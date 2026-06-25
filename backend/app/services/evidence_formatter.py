import re

from app.config.settings import settings
from app.services.boilerplate_filter import is_boilerplate


_STRENGTH_TO_SCORE = {"Strong": 0.9, "Moderate": 0.6, "Weak": 0.3}
_SCORE_TO_STRENGTH = {0.9: "Strong", 0.6: "Moderate", 0.3: "Weak"}


class FormattedEvidence:
    def __init__(
        self,
        text: str,
        excerpt: str,
        strength: str,
        document_id: str,
        filename: str,
        page: int | None = None,
        section: str | None = None,
        chunk_id: str | None = None,
        similarity_score: float = 0.5,
    ):
        self.text = text
        self.excerpt = excerpt
        self.strength = strength
        self.document_id = document_id
        self.filename = filename
        self.page = page
        self.section = section
        self.chunk_id = chunk_id
        self.similarity_score = similarity_score

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "excerpt": self.excerpt,
            "strength": self.strength,
            "quoted_text": self.excerpt or self.text[:200],
            "similarity_score": round(self.similarity_score, 3),
            "document_id": self.document_id,
            "filename": self.filename,
            "page": self.page,
            "section": self.section,
            "chunk_id": self.chunk_id,
        }


_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_BREAK_RE = re.compile(r"\n\s*\n")

_BOILERPLATE_PREFIX_RE = re.compile(
    r"^(?:(?:PRODUCT\s+FRUITS|SOC\s+2\s+REPORT|TYPE\s+\d+|INDEPENDENT\s+SERVICE\s+AUDITOR)[\s\S]*?)\n\n+",
)


def _strip_boilerplate_prefix(text: str) -> str:
    """Remove any boilerplate prefix from evidence text before returning it."""
    while True:
        m = _BOILERPLATE_PREFIX_RE.match(text)
        if m:
            text = text[m.end():]
        else:
            break
    return text.strip()


def _classify_strength(text: str, reranker_score: float | None = None) -> str:
    if reranker_score is not None:
        if reranker_score >= 0.7:
            return "Strong"
        if reranker_score >= 0.4:
            return "Moderate"
        return "Weak"
    text = text.strip()
    if len(text) > 300:
        return "Strong"
    if len(text) > 100:
        return "Moderate"
    return "Weak"


def format_evidence(
    evidence_refs: list,
    max_context: int | None = None,
) -> list[FormattedEvidence]:
    """Convert raw retrieval results into formatted evidence blocks."""
    if not evidence_refs:
        return []

    max_context = max_context or settings.evidence_formatter_max_context
    formatted: list[FormattedEvidence] = []

    for ref in evidence_refs:
        parent_ctx = getattr(ref, "parent_context", "") or ""
        quoted = getattr(ref, "quoted_text", "") or ""
        similarity_score = getattr(ref, "similarity_score", 0.5)

        text = parent_ctx or quoted
        if not text or is_boilerplate(text):
            continue

        text = _strip_boilerplate_prefix(text)

        if settings.evidence_formatter_enabled:
            text = _merge_neighboring_context(text)
            text = _preserve_paragraph_boundaries(text)
            text = _restore_sentence_boundaries(text)

        if not text:
            continue

        display = text[:max_context] if len(text) > max_context else text
        excerpt = _make_excerpt(display)
        strength = _classify_strength(text, similarity_score)

        formatted.append(
            FormattedEvidence(
                text=display,
                excerpt=excerpt,
                strength=strength,
                document_id=getattr(ref, "document_id", ""),
                filename=getattr(ref, "filename", ""),
                page=getattr(ref, "page", None),
                section=getattr(ref, "section", None),
                chunk_id=getattr(ref, "chunk_id", None),
                similarity_score=similarity_score,
            )
        )

    return formatted


def _merge_neighboring_context(text: str) -> str:
    """Collapse redundant separator patterns from context expansion."""
    text = re.sub(r"\s*\.\.\.\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _restore_sentence_boundaries(text: str) -> str:
    """Ensure text ends on a sentence boundary."""
    text = text.strip()
    if not text:
        return text

    matches = list(_SENTENCE_END_RE.finditer(text))
    if not matches:
        return text

    last = matches[-1]
    return text[: last.end()].strip()


def _preserve_paragraph_boundaries(text: str) -> str:
    """Ensure text starts and ends at paragraph boundaries when possible."""
    text = text.strip()
    if not text:
        return text
    paragraphs = _PARAGRAPH_BREAK_RE.split(text)
    if len(paragraphs) <= 1:
        return text
    first = paragraphs[0].strip()
    last = paragraphs[-1].strip()
    if len(first) < 30 and len(paragraphs) > 1:
        paragraphs = paragraphs[1:]
    if len(last) < 30 and len(paragraphs) > 1:
        paragraphs = paragraphs[:-1]
    return "\n\n".join(p.strip() for p in paragraphs)


def _make_excerpt(text: str, max_chars: int = 150) -> str:
    """Generate a short display excerpt from the most relevant part."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."
