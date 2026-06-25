import json
import re

from app.models.enums import ControlStatus


class ControlEvaluationResult:
    def __init__(
        self,
        status: str,
        confidence: float,
        explanation: str,
        recommendation: str,
    ):
        self.status = status
        self.confidence = confidence
        self.explanation = explanation
        self.recommendation = recommendation


class ComplianceEvaluationService:
    def evaluate(self, control_name: str, control_description: str, evidence_list: list) -> ControlEvaluationResult:
        from llm.factory import create_llm
        from app.config.settings import settings

        llm = create_llm(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.nvidia_api_key,
        )

        def _get_text(e: object) -> str:
            if hasattr(e, "text"):
                return str(e.text)
            if hasattr(e, "content"):
                return str(e.content)
            if isinstance(e, dict):
                return e.get("text", e.get("content", ""))
            return str(e)

        context = "\n\n".join(_get_text(c)[:1000] for c in evidence_list[:5]) if evidence_list else "No evidence found."

        prompt = f"""You are evaluating whether company evidence supports a compliance control.

Control: {control_name}
Control Description: {control_description}

Evidence:
{context}

Evaluate if the evidence supports this control. Respond with a JSON object:
{{
    "status": "implemented" or "partially_implemented" or "missing" or "insufficient_evidence",
    "confidence": <0.0-1.0>,
    "explanation": {{
        "summary": "<one-sentence summary of the finding>",
        "reasoning": "<detailed reasoning connecting evidence to control requirements>",
        "key_citations": "<specific quoted text from evidence that most directly supports or refutes the control>",
        "gaps": "<any gaps or missing evidence>"
    }},
    "recommendation": "<what evidence would improve this, or empty string if sufficient>"
}}

Rules:
- "implemented": clear evidence directly supports the control
- "partially_implemented": some evidence exists but gaps remain
- "missing": no relevant evidence found
- "insufficient_evidence": evidence exists but is too vague or indirect
- Confidence should reflect how certain you are (0.0-1.0)
- Be conservative: prefer slightly lower confidence when unsure
- The "key_citations" field MUST contain verbatim quoted text from the evidence above (use "..." notation with exact quotes from the evidence text)
- The "explanation" field MUST be a JSON object with the four keys shown above, NOT a plain string"""

        response = llm.invoke([
            {"role": "system", "content": "You are a SOC2 compliance auditor evaluating evidence. Return ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ])

        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                valid_statuses = {s.value for s in ControlStatus if s != ControlStatus.PENDING}
                if result.get("status") not in valid_statuses:
                    result["status"] = ControlStatus.INSUFFICIENT_EVIDENCE.value

                explanation_raw = result.get("explanation", "")
                if isinstance(explanation_raw, dict):
                    parts = []
                    if explanation_raw.get("summary"):
                        parts.append(f"**Summary:** {explanation_raw['summary']}")
                    if explanation_raw.get("reasoning"):
                        parts.append(f"**Reasoning:** {explanation_raw['reasoning']}")
                    if explanation_raw.get("key_citations"):
                        parts.append(f"**Key Citations:** {explanation_raw['key_citations']}")
                    if explanation_raw.get("gaps"):
                        parts.append(f"**Gaps:** {explanation_raw['gaps']}")
                    explanation = "\n\n".join(parts)
                else:
                    explanation = str(explanation_raw)

                return ControlEvaluationResult(
                    status=result.get("status", ControlStatus.INSUFFICIENT_EVIDENCE.value),
                    confidence=result.get("confidence", 0.0),
                    explanation=explanation,
                    recommendation=result.get("recommendation", ""),
                )
            except json.JSONDecodeError:
                pass

        if not evidence_list:
            return ControlEvaluationResult(
                status=ControlStatus.MISSING.value,
                confidence=0.0,
                explanation="No supporting evidence found for this control.",
                recommendation="Upload documentation addressing this control.",
            )

        return ControlEvaluationResult(
            status=ControlStatus.INSUFFICIENT_EVIDENCE.value,
            confidence=0.3,
            explanation="Could not determine compliance status from the available evidence.",
            recommendation="Review the control and upload additional documentation.",
        )
