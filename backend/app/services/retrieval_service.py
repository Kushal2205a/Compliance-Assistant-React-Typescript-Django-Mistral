import re
import time
import uuid

from app.config.settings import settings
from app.services.bm25_index import get_bm25_index
from app.services.boilerplate_filter import deduplicate_chunks, filter_boilerplate
from app.services.reranker_service import get_reranker
from app.vectorstore.factory import get_vectorstore


class RetrievalDiagnostics:
    def __init__(self):
        self.dense_results = 0
        self.bm25_results = 0
        self.rrf_results = 0
        self.reranked_results = 0
        self.expanded_contexts = 0
        self.boilerplate_removed = 0
        self.deduplicated = 0
        self.final_chunks_sent = 0
        self.chunks_discarded_validation = 0
        self.dense_search_ms = 0.0
        self.bm25_search_ms = 0.0
        self.reranker_ms = 0.0
        self.expansion_ms = 0.0
        self.boilerplate_ms = 0.0
        self.llm_ms = 0.0
        self.format_ms = 0.0
        self.total_ms = 0.0
        self.embedding_model = ""
        self.retrieval_strategy = ""
        self.reranker_model = ""

    def to_dict(self) -> dict:
        return {
            "dense_results": self.dense_results,
            "bm25_results": self.bm25_results,
            "rrf_results": self.rrf_results,
            "reranked_results": self.reranked_results,
            "expanded_contexts": self.expanded_contexts,
            "boilerplate_removed": self.boilerplate_removed,
            "deduplicated": self.deduplicated,
            "final_chunks_sent": self.final_chunks_sent,
            "chunks_discarded_validation": self.chunks_discarded_validation,
            "dense_search_ms": round(self.dense_search_ms, 1),
            "bm25_search_ms": round(self.bm25_search_ms, 1),
            "reranker_ms": round(self.reranker_ms, 1),
            "expansion_ms": round(self.expansion_ms, 1),
            "boilerplate_ms": round(self.boilerplate_ms, 1),
            "llm_ms": round(self.llm_ms, 1),
            "format_ms": round(self.format_ms, 1),
            "total_ms": round(self.total_ms, 1),
            "embedding_model": self.embedding_model,
            "retrieval_strategy": self.retrieval_strategy,
            "reranker_model": self.reranker_model,
        }


class EvidenceRef:
    def __init__(
        self,
        document_id: str,
        filename: str,
        page: int | None = None,
        section: str | None = None,
        chunk_id: str | None = None,
        similarity_score: float = 0.0,
        quoted_text: str = "",
        parent_context: str = "",
    ):
        self.document_id = document_id
        self.filename = filename
        self.page = page
        self.section = section
        self.chunk_id = chunk_id
        self.similarity_score = similarity_score
        self.quoted_text = quoted_text
        self.parent_context = parent_context

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "page": self.page,
            "section": self.section,
            "chunk_id": self.chunk_id,
            "similarity_score": round(self.similarity_score, 3),
            "quoted_text": self.quoted_text,
            "parent_context": self.parent_context,
        }


class RetrievalResult:
    def __init__(self, chunks: list, evidence_refs: list[EvidenceRef], diagnostics: RetrievalDiagnostics | None = None):
        self.chunks = chunks
        self.evidence_refs = evidence_refs
        self.diagnostics = diagnostics or RetrievalDiagnostics()


_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from rag.pipeline.embeddings.models import SentenceTransformerModel
        _embedder = SentenceTransformerModel(
            settings.embedding_model_name,
            settings.embedding_device,
        )
    return _embedder


_CONTENT_KEYWORDS = re.compile(
    r"(?i)(policy|procedure|control|implement|security|access|encrypt|monitor|"
    r"audit|review|approve|manage|protect|backup|recovery|incident|risk|"
    r"compliance|governance|password|authentication|authorization|data\s+protection|"
    r"confidentiality|integrity|availability|vendor|asset|network|endpoint|"
    r"vulnerability|remediation|patching|notification|training|awareness)"
)

_MIN_CONTENT_WORDS = 15


def _is_meaningful_content(chunk_text: str) -> bool:
    """Check if chunk contains meaningful evidence content vs metadata/headers."""
    if not chunk_text:
        return False
    words = chunk_text.split()
    if len(words) < _MIN_CONTENT_WORDS:
        return False
    content_matches = _CONTENT_KEYWORDS.findall(chunk_text)
    return len(content_matches) >= 2


def _validate_evidence(chunks: list) -> list:
    """Discard chunks that don't contain meaningful evidence content."""
    return [c for c in chunks if _is_meaningful_content(c.content if hasattr(c, "content") else str(c))]


def _clean_sentence_boundaries(text: str, max_chars: int = 600) -> str:
    if not text:
        return text
    text = text.strip()
    if len(text) <= max_chars:
        return text
    text = text[:max_chars]
    sentence_end = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    positions = [m.end() for m in sentence_end.finditer(text)]
    if positions:
        return text[:positions[-1]]
    return text


def _reciprocal_rank_fusion(
    dense_results: list[tuple[str, float]],
    bm25_results: list[tuple[str, float]],
    k: int | None = None,
    top_k: int | None = None,
) -> list[str]:
    """Fuse dense and BM25 results using Reciprocal Rank Fusion."""
    k = k or settings.retrieval_rrf_k
    top_k = top_k or settings.retrieval_rrf_top_k

    scores: dict[str, float] = {}
    for rank, (doc_id, _) in enumerate(dense_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    for rank, (doc_id, _) in enumerate(bm25_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_id for doc_id, _ in ranked[:top_k]]


class RetrievalService:
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResult:
        t_start = time.time()
        diag = RetrievalDiagnostics()
        vs = get_vectorstore()
        embedder = _get_embedder()
        print(f"[retrieval] query={query[:60]}...")

        # --- 1. Dense retrieval ---
        t0 = time.time()
        query_emb = embedder.embed_query(query)
        dense_results = vs.search(query_emb, k=settings.retrieval_dense_top_k)
        diag.dense_search_ms = (time.time() - t0) * 1000
        diag.dense_results = len(dense_results)
        print(f"[retrieval]  1. dense: {len(dense_results)} results ({diag.dense_search_ms:.0f}ms)")

        # --- 2. BM25 retrieval ---
        bm25_results_raw: list[tuple[str, float]] = []
        if settings.bm25_enabled:
            t0 = time.time()
            bm25 = get_bm25_index()
            bm25_results_raw = bm25.search(query, top_k=settings.retrieval_bm25_top_k)
            diag.bm25_search_ms = (time.time() - t0) * 1000
            diag.bm25_results = len(bm25_results_raw)
            print(f"[retrieval]  2. bm25: {len(bm25_results_raw)} results ({diag.bm25_search_ms:.0f}ms)")
        else:
            print(f"[retrieval]  2. bm25: disabled")

        # --- 3. RRF fusion ---
        dense_ids = [(r.chunk.id, r.score) for r in dense_results]
        fused_ids = _reciprocal_rank_fusion(dense_ids, bm25_results_raw)
        diag.rrf_results = len(fused_ids)
        print(f"[retrieval]  3. rrf: {len(fused_ids)} fused")

        # Build a lookup from fused IDs to search results
        result_by_id = {r.chunk.id: r for r in dense_results}
        for doc_id, score in bm25_results_raw:
            if doc_id not in result_by_id:
                result_by_id[doc_id] = None

        fused_results = [result_by_id[doc_id] for doc_id in fused_ids if doc_id in result_by_id and result_by_id[doc_id] is not None]

        # --- 4. Reranker ---
        reranker_enabled = settings.reranker_enabled
        top_k_rerank = top_k or settings.retrieval_top_k
        if reranker_enabled and len(fused_results) > 1:
            t0 = time.time()
            reranker = get_reranker()
            texts = [r.chunk.content for r in fused_results]
            reranked = reranker.rerank(query, texts, top_k=top_k_rerank)
            diag.reranker_ms = (time.time() - t0) * 1000
            diag.reranked_results = len(reranked)
            print(f"[retrieval]  4. reranker: {len(reranked)} results ({diag.reranker_ms:.0f}ms)")

            reranked_texts = {t for t, _ in reranked}
            reranked_results = [r for r in fused_results if r.chunk.content in reranked_texts]
            fused_results = reranked_results
        else:
            fused_results = fused_results[:top_k_rerank]
            diag.reranked_results = len(fused_results)
            print(f"[retrieval]  4. reranker: disabled (taking top {len(fused_results)})")

        # --- 5. Boilerplate filtering ---
        t0 = time.time()
        before_filter = len(fused_results)
        filtered = filter_boilerplate([r.chunk for r in fused_results])
        diag.boilerplate_removed = before_filter - len(filtered)
        diag.boilerplate_ms = (time.time() - t0) * 1000
        print(f"[retrieval]  5. boilerplate: removed {diag.boilerplate_removed}, kept {len(filtered)} ({diag.boilerplate_ms:.1f}ms)")

        # --- 6. Deduplication ---
        before_dedup = len(filtered)
        deduped = deduplicate_chunks(filtered)
        diag.deduplicated = before_dedup - len(deduped)

        # Rebuild result list from filtered+deduped chunks
        filtered_ids = {c.id for c in deduped}
        final_results_before_val = [r for r in fused_results if r.chunk.id in filtered_ids]

        # --- 7. Evidence validation ---
        before_val = len(final_results_before_val)
        validated = _validate_evidence([r.chunk for r in final_results_before_val])
        diag.chunks_discarded_validation = before_val - len(validated)
        validated_ids = {c.id for c in validated}
        final_results = [r for r in final_results_before_val if r.chunk.id in validated_ids]
        if diag.chunks_discarded_validation:
            print(f"[retrieval]  7. validation: discarded {diag.chunks_discarded_validation}, kept {len(final_results)}")

        # --- 8. Context expansion ---
        if settings.context_expansion_enabled:
            t0 = time.time()
            final_results = self._expand_context(vs, final_results)
            diag.expansion_ms = (time.time() - t0) * 1000
            print(f"[retrieval]  8. context expansion: {len(final_results)} contexts ({diag.expansion_ms:.0f}ms)")

        diag.expanded_contexts = len(final_results)
        diag.final_chunks_sent = len(final_results)
        diag.embedding_model = settings.embedding_model_name
        diag.retrieval_strategy = "hybrid" if settings.bm25_enabled else "dense_only"
        if settings.reranker_enabled:
            diag.retrieval_strategy += "+reranker"
        diag.reranker_model = settings.reranker_model if settings.reranker_enabled else ""

        # --- Build evidence refs ---
        chunks = []
        evidence_refs = []
        for r in final_results:
            chunks.append(r.chunk)
            chunk = r.chunk
            metadata = chunk.metadata or {}
            quoted = chunk.content[:600] if chunk.content else ""
            quoted = _clean_sentence_boundaries(quoted)
            parent_context = metadata.get("parent_context", "")
            evidence_refs.append(
                EvidenceRef(
                    document_id=metadata.get("document_id", chunk.document_id or ""),
                    filename=metadata.get("filename", "Unknown"),
                    page=metadata.get("page_number"),
                    section=metadata.get("section_title"),
                    chunk_id=chunk.id,
                    similarity_score=r.score,
                    quoted_text=parent_context or quoted,
                    parent_context=parent_context,
                )
            )

        diag.total_ms = (time.time() - t_start) * 1000
        print(f"[retrieval]  done: {len(evidence_refs)} refs, {diag.total_ms:.0f}ms total")

        return RetrievalResult(chunks=chunks, evidence_refs=evidence_refs, diagnostics=diag)

    def _expand_context(self, vs, results: list) -> list:
        """Expand each result by merging neighbouring chunks."""
        expanded = []
        for r in results:
            chunk = r.chunk
            metadata = chunk.metadata or {}
            prev_id = metadata.get("previous_chunk_id")
            next_id = metadata.get("next_chunk_id")

            neighbor_ids = []
            for i in range(1, settings.context_expansion_window + 1):
                if prev_id:
                    neighbor_ids.append(prev_id)
                if next_id:
                    neighbor_ids.append(next_id)

            if not neighbor_ids:
                expanded.append(r)
                continue

            neighbors = vs.get_chunks_by_ids(neighbor_ids)
            if not neighbors:
                expanded.append(r)
                continue

            context_parts = [n.content for n in neighbors]
            context_parts.append(chunk.content)
            merged = " ... ".join(context_parts)
            merged = _clean_sentence_boundaries(merged, max_chars=1200)

            metadata["parent_context"] = merged
            expanded.append(r)

        return expanded
