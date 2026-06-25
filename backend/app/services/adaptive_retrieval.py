import json
import re

from app.config.settings import settings
from rag.pipeline.prompts.evaluate import EVALUATE_PROMPT
from rag.pipeline.prompts.rewrite import REWRITE_PROMPT


class SufficiencyResult:
    def __init__(
        self,
        sufficient: bool,
        missing_info: list[str] | None = None,
        reformulated_query: str | None = None,
        reasoning: str = "",
    ):
        self.sufficient = sufficient
        self.missing_info = missing_info or []
        self.reformulated_query = reformulated_query
        self.reasoning = reasoning


class AdaptiveResult:
    def __init__(
        self,
        evidence_refs: list,
        chunks: list,
        diagnostics=None,
        attempts: int = 1,
        rewritten_queries: list[str] | None = None,
        original_query: str = "",
    ):
        self.evidence_refs = evidence_refs
        self.chunks = chunks
        self.diagnostics = diagnostics
        self.attempts = attempts
        self.rewritten_queries = rewritten_queries or []
        self.original_query = original_query


class AdaptiveRetrievalService:
    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            from llm.factory import create_llm
            self._llm = create_llm(
                model=settings.llm_model,
                base_url=settings.llm_base_url,
                api_key=settings.nvidia_api_key,
            )
        return self._llm

    def check_sufficiency(self, query: str, context: str) -> SufficiencyResult:
        """Ask LLM whether retrieved context is sufficient."""
        if not settings.adaptive_retrieval_enabled:
            return SufficiencyResult(sufficient=True)

        llm = self._get_llm()
        prompt = EVALUATE_PROMPT.format(query=query, context=context)

        response = llm.invoke([
            {"role": "system", "content": "You are evaluating retrieval sufficiency. Return ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ])

        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return SufficiencyResult(
                    sufficient=data.get("sufficient", True),
                    missing_info=data.get("missing_info", []),
                    reformulated_query=data.get("reformulated_query"),
                    reasoning=data.get("reasoning", ""),
                )
            except json.JSONDecodeError:
                pass

        return SufficiencyResult(sufficient=True)

    def rewrite_query(self, original_query: str) -> str:
        """Rewrite query for improved retrieval."""
        llm = self._get_llm()
        prompt = REWRITE_PROMPT.format(query=original_query)

        response = llm.invoke([
            {"role": "system", "content": "You rewrite queries for better retrieval. Return ONLY the rewritten query."},
            {"role": "user", "content": prompt},
        ])

        rewritten = response.strip().strip('"\'')
        return rewritten if rewritten else original_query

    def retrieve_with_adaptive(
        self,
        query: str,
        retrieval_fn,
        top_k: int | None = None,
        max_retries: int | None = None,
    ) -> AdaptiveResult:
        """Retrieve, check sufficiency, retry with rewritten query if needed."""
        max_retries = max_retries or settings.adaptive_max_retries
        k = top_k or settings.retrieval_top_k

        current_query = query
        all_refs: list = []
        all_chunks: list = []
        rewritten: list[str] = []
        diagnostics = None

        for attempt in range(max_retries + 1):
            result = retrieval_fn(current_query, top_k=k)
            all_refs.extend(result.evidence_refs)
            all_chunks.extend(result.chunks)
            if result.diagnostics:
                diagnostics = result.diagnostics

            if attempt == max_retries:
                break

            context = "\n\n".join(
                ref.quoted_text or ref.parent_context or ""
                for ref in result.evidence_refs
            )
            if not context:
                break

            sufficiency = self.check_sufficiency(current_query, context)
            if sufficiency.sufficient:
                break

            if sufficiency.reformulated_query:
                current_query = sufficiency.reformulated_query
            else:
                current_query = self.rewrite_query(current_query)
            rewritten.append(current_query)

        return AdaptiveResult(
            evidence_refs=all_refs,
            chunks=all_chunks,
            diagnostics=diagnostics,
            attempts=len(rewritten) + 1,
            rewritten_queries=rewritten,
            original_query=query,
        )


_adaptive_service: AdaptiveRetrievalService | None = None


def get_adaptive_retrieval_service() -> AdaptiveRetrievalService:
    global _adaptive_service
    if _adaptive_service is None:
        _adaptive_service = AdaptiveRetrievalService()
    return _adaptive_service
