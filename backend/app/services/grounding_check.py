import re

_CONTROL_KEYWORDS: dict[str, list[re.Pattern]] = {}


def _extract_claims(explanation: str) -> list[str]:
    """Extract factual claims from the LLM's explanation."""
    claims = []
    lines = explanation.split("\n")
    for line in lines:
        stripped = re.sub(r"^\*\*[^*]+\*\*:?\s*", "", line).strip()
        if not stripped:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", stripped):
            sentence = sentence.strip().strip('"')
            if 15 < len(sentence) < 300 and not sentence.startswith("http"):
                claims.append(sentence)
    return claims[:6]


def _find_claim_in_evidence(claim: str, evidence_texts: list[str]) -> tuple[bool, str]:
    """Check if a claim is directly supported by at least one piece of evidence."""
    claim_lower = claim.lower()

    stopwords = {"a", "an", "the", "is", "are", "was", "were", "has", "have", "had", "been",
                 "being", "be", "will", "shall", "may", "might", "can", "could", "would", "should",
                 "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through",
                 "during", "before", "after", "above", "below", "between", "out", "off", "over",
                 "under", "again", "further", "then", "once"}

    words = [w for w in re.findall(r"\w+", claim_lower) if w not in stopwords and len(w) > 3]
    if len(words) < 2:
        return True, ""

    for ev_text in evidence_texts:
        ev_lower = ev_text.lower()
        matches = sum(1 for w in words if w in ev_lower)
        ratio = matches / len(words)
        if ratio >= 0.6:
            return True, ""

        if len(words) >= 3:
            bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
            bigram_matches = sum(1 for bg in bigrams if bg in ev_lower)
            if bigram_matches >= 1:
                return True, ""

    return False, f"Claim not found in any evidence: \"{claim[:100]}...\""


def check_grounding(
    explanation: str,
    evidence_texts: list[str],
    status: str,
    confidence: float,
) -> tuple[str, float, str]:
    """Validate that the LLM's evaluation is grounded in the provided evidence.

    Returns (adjusted_status, adjusted_confidence, grounding_warnings).
    """
    if status == "pending" or status == "missing":
        return status, confidence, ""

    claims = _extract_claims(explanation)
    if not claims:
        return status, confidence, ""

    warnings: list[str] = []
    for claim in claims:
        supported, warning = _find_claim_in_evidence(claim, evidence_texts)
        if not supported:
            warnings.append(warning)

    if warnings:
        warning_text = " | ".join(warnings)
        new_confidence = max(0.1, confidence - 0.2 * len(warnings))
        new_status = status
        if status == "implemented" and new_confidence < 0.4:
            new_status = "insufficient_evidence"
        return new_status, round(new_confidence, 2), warning_text

    return status, confidence, ""
