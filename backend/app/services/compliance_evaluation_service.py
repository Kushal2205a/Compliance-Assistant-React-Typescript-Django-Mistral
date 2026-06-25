import json
import re

from app.models.enums import ControlStatus
from app.services.control_grouper import ControlGroup


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
    def _get_llm(self):
        from llm.factory import create_llm
        from app.config.settings import settings
        return create_llm(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.nvidia_api_key,
        )

    @staticmethod
    def _get_text(e: object) -> str:
        if hasattr(e, "text"):
            return str(e.text)
        if hasattr(e, "content"):
            return str(e.content)
        if isinstance(e, dict):
            return e.get("text", e.get("content", ""))
        return str(e)

    @staticmethod
    def _format_explanation(explanation_raw) -> str:
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
            return "\n\n".join(parts)
        return str(explanation_raw)

    def _parse_single_result(self, result: dict) -> ControlEvaluationResult:
        valid_statuses = {s.value for s in ControlStatus if s != ControlStatus.PENDING}
        status = result.get("status", ControlStatus.INSUFFICIENT_EVIDENCE.value)
        if status not in valid_statuses:
            status = ControlStatus.INSUFFICIENT_EVIDENCE.value
        return ControlEvaluationResult(
            status=status,
            confidence=result.get("confidence", 0.0),
            explanation=self._format_explanation(result.get("explanation", "")),
            recommendation=result.get("recommendation", ""),
        )

    def _extract_json_array(self, response: str) -> list | None:
        """Multi-pass JSON array extraction."""
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        try:
            result = json.loads(response.strip())
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return [result]
        except json.JSONDecodeError:
            pass

        objects = re.findall(r'\{[^{}]*"control_id"[^{}]*\}', response)
        if objects:
            parsed = []
            for obj_str in objects:
                try:
                    parsed.append(json.loads(obj_str))
                except json.JSONDecodeError:
                    continue
            if parsed:
                return parsed

        return None

    def batch_evaluate(self, group: ControlGroup, evidence_list: list) -> list[ControlEvaluationResult]:
        """Evaluate multiple controls in a single LLM call using shared evidence."""
        llm = self._get_llm()

        context = "\n\n".join(self._get_text(c)[:1000] for c in evidence_list[:8]) if evidence_list else "No evidence found."

        controls_text = ""
        for i, ctrl in enumerate(group.controls, 1):
            desc = f" — {ctrl.description}" if ctrl.description else ""
            controls_text += f"{i}. [{ctrl.control_id}] {ctrl.name}{desc}\n"

        prompt = f"""Evaluate these controls against the evidence. Return a JSON array.
Each element: {{"control_id":"...","status":"implemented|partially_implemented|missing|insufficient_evidence","confidence":0.0-1.0,"explanation":{{"summary":"...","reasoning":"...","key_citations":"...","gaps":"..."}},"recommendation":"..."}}

Evidence:
{context}

Controls:
{controls_text}

Return ONLY a JSON array. No markdown, no other text."""

        response = llm.invoke([
            {"role": "system", "content": "Return ONLY a valid JSON array of compliance evaluation results."},
            {"role": "user", "content": prompt},
        ])

        results_array = self._extract_json_array(response)
        if results_array and isinstance(results_array, list):
            return self._map_batch_results(group, results_array, evidence_list)

        print(f"[eval] batch parse failed, falling back to individual evaluation for {len(group.controls)} controls")
        return [self.evaluate(c.name, c.description, evidence_list) for c in group.controls]

    def _map_batch_results(
        self,
        group: ControlGroup,
        results_array: list,
        evidence_list: list,
    ) -> list[ControlEvaluationResult]:
        """Map LLM batch results to controls, with per-control fallback."""
        results_by_id: dict[str, dict] = {}
        for r in results_array:
            if isinstance(r, dict) and "control_id" in r:
                cid = r["control_id"].strip()
                results_by_id[cid] = r

        output = []
        for ctrl in group.controls:
            matched = results_by_id.get(ctrl.control_id)
            if matched:
                try:
                    output.append(self._parse_single_result(matched))
                except Exception as e:
                    print(f"[eval] parse failed for {ctrl.control_id}: {e}, falling back")
                    output.append(self.evaluate(ctrl.name, ctrl.description, evidence_list))
            else:
                print(f"[eval] {ctrl.control_id} not found in batch response, evaluating individually")
                output.append(self.evaluate(ctrl.name, ctrl.description, evidence_list))

        return output

    def evaluate(self, control_name: str, control_description: str, evidence_list: list) -> ControlEvaluationResult:
        llm = self._get_llm()
        context = "\n\n".join(self._get_text(c)[:1000] for c in evidence_list[:5]) if evidence_list else "No evidence found."

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
                return self._parse_single_result(result)
            except (json.JSONDecodeError, KeyError):
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
