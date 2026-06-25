import re

from app.config.settings import settings

_BOILERPLATE_PATTERNS_SEARCH: list[re.Pattern] = [
    re.compile(r"(?i)(page\s+\d+(\s+of\s+\d+)?)"),
    re.compile(r"(?i)(confidential|proprietary|internal\s+use\s+only)"),
    re.compile(r"(?i)(disclaimer|copyright\s+©|all\s+rights?\s+reserved)"),
    re.compile(r"(?i)(table\s+of\s+contents)"),
    re.compile(r"(?i)(product\s+fruits|s\.r\.o\.)"),
    re.compile(r"(?i)(soc\s+2?\s*(\d*\s*)?report)"),
    re.compile(r"(?i)(independent\s+service\s+auditor)"),
    re.compile(r"(?i)(type\s+\d+\s+independent)"),
    re.compile(r"(?i)(report\s+on\s+controls)"),
    re.compile(r"^\s*rev\.?\s*[\d.]+\s*$", re.IGNORECASE),
    re.compile(r"^\s*ver\.?\s*[\d.]+\s*$", re.IGNORECASE),
    re.compile(r"^[A-Z][A-Z\s/]{30,}$"),
]

_BOILERPLATE_PATTERNS_MATCH: list[re.Pattern] = [
    re.compile(r"^\s*\d{1,2}\s*$"),
    re.compile(r"^\s*page\s+\d+", re.IGNORECASE),
]


def _boilerplate_ratio(text: str) -> float:
    """Fraction of lines that match boilerplate patterns."""
    lines = text.strip().split("\n")
    if not lines:
        return 1.0
    match_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for pat in _BOILERPLATE_PATTERNS_SEARCH:
            if pat.search(stripped):
                match_count += 1
                break
    return match_count / len(lines) if lines else 0.0


def is_boilerplate(text: str) -> bool:
    """Return True if the chunk appears to be boilerplate."""
    text = text.strip()
    if not text:
        return True
    if len(text) < settings.boilerplate_min_length:
        return True
    for pattern in _BOILERPLATE_PATTERNS_MATCH:
        if pattern.match(text):
            return True
    if _boilerplate_ratio(text) > 0.5:
        return True
    return False


def filter_boilerplate(chunks: list) -> list:
    """Remove boilerplate chunks, preserving order."""
    result = []
    removed = 0
    for c in chunks:
        content = c.content if hasattr(c, "content") else str(c)
        if is_boilerplate(content):
            removed += 1
            if removed <= 3:
                print(f"[boilerplate] removed: {content[:80]}...")
        else:
            result.append(c)
    if removed:
        print(f"[boilerplate] removed {removed} chunks total")
    return result


def deduplicate_chunks(chunks: list) -> list:
    """Remove chunks with identical or near-identical content, keep first occurrence."""
    seen: set[str] = set()
    result: list = []
    for c in chunks:
        content = c.content if hasattr(c, "content") else str(c)
        key = content[:300].strip().lower() if content else ""
        if key and key not in seen:
            seen.add(key)
            result.append(c)
    return result
