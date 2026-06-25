import re

import pdfplumber

from . import Document

_HEADER_LINE_CACHE: dict[str, int] = {}


def _is_running_header(line: str, min_count: int = 3) -> bool:
    """Detect running headers by checking if the same line appears on multiple pages."""
    key = line.strip().lower()
    if len(key) < 10:
        return False
    _HEADER_LINE_CACHE[key] = _HEADER_LINE_CACHE.get(key, 0) + 1
    return _HEADER_LINE_CACHE[key] >= min_count


def _strip_running_headers(page_text: str) -> str:
    """Remove running headers/footers from a single page's text."""
    lines = page_text.split("\n")
    cleaned = [l for l in lines if not _is_running_header(l)]
    return "\n".join(cleaned).strip()


def load_pdf(file, return_page_map: bool = False) -> Document | tuple[Document, dict[int, int]]:
    with pdfplumber.open(file) as pdf:
        raw_pages: list[str] = [page.extract_text() or "" for page in pdf.pages]

    line_freq: dict[str, int] = {}
    for extracted in raw_pages:
        for line in extracted.split("\n"):
            key = line.strip().lower()
            if len(key) >= 10:
                line_freq[key] = line_freq.get(key, 0) + 1

    threshold = max(3, len(raw_pages) // 3)
    running_headers: set[str] = {k for k, v in line_freq.items() if v >= threshold}

    def _clean(text: str) -> str:
        if not text:
            return ""
        lines = text.split("\n")
        kept = [l for l in lines if l.strip().lower() not in running_headers]
        return "\n".join(kept).strip()

    page_map: dict[int, int] = {}
    offset = 0
    text_parts: list[str] = []
    for page_num, extracted in enumerate(raw_pages):
        cleaned = _clean(extracted)
        if cleaned:
            page_map[offset] = page_num
            text_parts.append(cleaned)
            offset += len(cleaned) + 1
        else:
            text_parts.append("")
            offset += 1

    content = "\n".join(text_parts)
    filename = getattr(file, "name", "unknown")
    print(f"[loader] {filename}: {len(raw_pages)} pages, {sum(len(t) for t in text_parts if t)} chars extracted, {len(running_headers)} running header patterns detected")
    doc = Document(
        id=filename,
        content=content,
        metadata={"source": filename, "pages": len(raw_pages)},
        source=filename,
    )
    if return_page_map:
        return doc, page_map
    return doc
