import re
import uuid

import numpy as np
import spacy

from . import Chunk, HierarchicalChunk, make_chunk_id


nlp = spacy.load("en_core_web_sm")

SECTION_RE = re.compile(r"^\d+\.\d+\s+")

_para_counter = 0
_chunk_counter = 0


def _reset_counters():
    global _para_counter, _chunk_counter
    _para_counter = 0
    _chunk_counter = 0


def _next_para_id() -> str:
    global _para_counter
    _para_counter += 1
    return f"para_{_para_counter:04d}"


def _next_chunk_id() -> str:
    global _chunk_counter
    _chunk_counter += 1
    return f"chunk_{_chunk_counter:04d}"


def _make_id() -> str:
    return uuid.uuid4().hex[:12]


def _extract_sections(text: str) -> list[tuple[str, int]]:
    """Return list of (section_text, start_offset) preserving page numbers."""
    sections: list[tuple[str, int]] = []
    current: list[str] = []
    offset = 0
    for line in text.split("\n"):
        if SECTION_RE.match(line):
            if current:
                sections.append(("\n".join(current), offset))
                offset += len("\n".join(current)) + 1
            current = [line]
        elif current:
            current.append(line)
    if current:
        sections.append(("\n".join(current), offset))
    return sections


def document_aware_chunker(
    text: str,
    document_id: str,
    chunk_size: int = 512,
    overlap: int = 64,
    page_map: dict[int, int] | None = None,
) -> list[Chunk]:
    """Section → paragraph → sentence-aware chunker with full metadata.

    Preserves section hierarchy, paragraph boundaries, and sentence
    boundaries.  Only splits a paragraph when it exceeds *chunk_size*.
    When splitting, splits on spaCy sentence boundaries.

    *page_map* maps character offset → page_number (built during PDF load).
    """
    _reset_counters()
    sections = _extract_sections(text)
    if not sections:
        sections = [(text, 0)]

    all_chunks: list[Chunk] = []
    char_offset = 0

    for sec_idx, (section_text, sec_offset) in enumerate(sections):
        heading = section_text.split("\n")[0] if section_text else ""
        heading = heading.strip()[:200]

        paragraphs = re.split(r"\n\n+", section_text)
        for para_text in paragraphs:
            para_text = para_text.strip()
            if not para_text:
                continue

            para_id = _next_para_id()
            para_start = char_offset

            if len(para_text) <= chunk_size:
                chunk_id = _next_chunk_id()
                chunk_start = char_offset
                chunk_end = chunk_start + len(para_text)
                chunk = Chunk(
                    id=_make_id(),
                    document_id=document_id,
                    content=para_text,
                    metadata={
                        "indexing_version": 2,
                        "chunk_type": "paragraph",
                        "section_index": sec_idx,
                        "section_title": heading,
                        "page_number": _resolve_page(
                            chunk_start, page_map
                        ),
                        "parent_paragraph_id": para_id,
                        "chunk_sequence_id": chunk_id,
                        "previous_chunk_id": "",
                        "next_chunk_id": "",
                        "start_char": chunk_start,
                        "end_char": chunk_end,
                        "parent_context": para_text,
                    },
                )
                all_chunks.append(chunk)
                char_offset = chunk_end + 2  # account for paragraph break
                continue

            # Long paragraph: split on sentence boundaries
            doc = nlp(para_text)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            buffer = ""
            buffer_start = char_offset
            sent_start_offset = char_offset

            for sent_text in sentences:
                if not sent_text:
                    continue
                sent_len = len(sent_text) + (1 if buffer else 0)
                if buffer and len(buffer) + len(sent_text) > chunk_size:
                    chunk_id = _next_chunk_id()
                    chunk_end = sent_start_offset - 1
                    chunk = Chunk(
                        id=_make_id(),
                        document_id=document_id,
                        content=buffer,
                        metadata={
                            "indexing_version": 2,
                            "chunk_type": "sentence_group",
                            "section_index": sec_idx,
                            "section_title": heading,
                            "page_number": _resolve_page(
                                buffer_start, page_map
                            ),
                            "parent_paragraph_id": para_id,
                            "chunk_sequence_id": chunk_id,
                            "previous_chunk_id": "",
                            "next_chunk_id": "",
                            "start_char": buffer_start,
                            "end_char": chunk_end,
                            "parent_context": para_text,
                        },
                    )
                    all_chunks.append(chunk)
                    buffer = sent_text
                    buffer_start = sent_start_offset
                else:
                    buffer = (buffer + " " + sent_text) if buffer else sent_text
                sent_start_offset += len(sent_text) + 1

            if buffer:
                chunk_id = _next_chunk_id()
                chunk = Chunk(
                    id=_make_id(),
                    document_id=document_id,
                    content=buffer,
                    metadata={
                        "indexing_version": 2,
                        "chunk_type": "sentence_group",
                        "section_index": sec_idx,
                        "section_title": heading,
                        "page_number": _resolve_page(
                            buffer_start, page_map
                        ),
                        "parent_paragraph_id": para_id,
                        "chunk_sequence_id": chunk_id,
                        "previous_chunk_id": "",
                        "next_chunk_id": "",
                        "start_char": buffer_start,
                        "end_char": char_offset + len(buffer),
                        "parent_context": para_text,
                    },
                )
                all_chunks.append(chunk)

            char_offset += len(para_text) + 2

    # Link neighbouring chunks
    for i, chunk in enumerate(all_chunks):
        if i > 0:
            chunk.metadata["previous_chunk_id"] = all_chunks[i - 1].metadata[
                "chunk_sequence_id"
            ]
        if i < len(all_chunks) - 1:
            chunk.metadata["next_chunk_id"] = all_chunks[i + 1].metadata[
                "chunk_sequence_id"
            ]

    return all_chunks


def _resolve_page(char_offset: int, page_map: dict[int, int] | None) -> int | None:
    if not page_map:
        return None
    best = None
    for offset, page in sorted(page_map.items()):
        if offset <= char_offset:
            best = page
        else:
            break
    return best


# ── Existing strategies (unchanged) ──────────────────────────────


def recursive_chunker(
    text: str,
    document_id: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    words = text.split()
    chunks: list[Chunk] = []
    step = chunk_size - overlap
    if step < 1:
        step = 1
    for i in range(0, len(words), step):
        content = " ".join(words[i : i + chunk_size])
        chunks.append(
            Chunk(
                id=_make_id(),
                document_id=document_id,
                content=content,
                metadata={"chunk_type": "recursive", "index": i // step},
            )
        )
    return chunks


def compliance_chunker(
    text: str,
    document_id: str,
    max_section_chars: int = 1500,
    max_sentence_chars: int = 1000,
) -> list[Chunk]:
    sections = _extract_sections(text)
    if not sections:
        sections = [(text, 0)]
    chunks: list[Chunk] = []
    for sec_idx, (section, _) in enumerate(sections):
        if len(section) <= max_section_chars:
            chunks.append(
                Chunk(
                    id=_make_id(),
                    document_id=document_id,
                    content=section,
                    metadata={
                        "chunk_type": "compliance_section",
                        "section_index": sec_idx,
                    },
                )
            )
        else:
            doc = nlp(section)
            buffer = ""
            for sent in doc.sents:
                sent_text = sent.text.strip()
                if not sent_text:
                    continue
                if len(buffer) + len(sent_text) > max_sentence_chars:
                    if buffer:
                        chunks.append(
                            Chunk(
                                id=_make_id(),
                                document_id=document_id,
                                content=buffer,
                                metadata={
                                    "chunk_type": "compliance_sentence",
                                    "section_index": sec_idx,
                                },
                            )
                        )
                    buffer = sent_text
                else:
                    buffer += " " + sent_text if buffer else sent_text
            if buffer:
                chunks.append(
                    Chunk(
                        id=_make_id(),
                        document_id=document_id,
                        content=buffer,
                        metadata={
                            "chunk_type": "compliance_sentence",
                            "section_index": sec_idx,
                        },
                    )
                )
    return chunks


def sentence_chunker(
    text: str,
    document_id: str,
    max_chunk_chars: int = 512,
) -> list[Chunk]:
    doc = nlp(text)
    chunks: list[Chunk] = []
    buffer = ""
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if not sent_text:
            continue
        if len(buffer) + len(sent_text) > max_chunk_chars:
            if buffer:
                chunks.append(
                    Chunk(
                        id=_make_id(),
                        document_id=document_id,
                        content=buffer,
                        metadata={"chunk_type": "sentence"},
                    )
                )
            buffer = sent_text
        else:
            buffer += " " + sent_text if buffer else sent_text
    if buffer:
        chunks.append(
            Chunk(
                id=_make_id(),
                document_id=document_id,
                content=buffer,
                metadata={"chunk_type": "sentence"},
            )
        )
    return chunks


def semantic_chunker(
    text: str,
    document_id: str,
    embed_fn,
    threshold: float = 0.5,
    max_chunk_chars: int = 1024,
) -> list[Chunk]:
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    if not sentences:
        return []

    if len(sentences) == 1:
        return [
            Chunk(
                id=_make_id(),
                document_id=document_id,
                content=sentences[0],
                metadata={"chunk_type": "semantic"},
            )
        ]

    embeddings = embed_fn(sentences)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    similarities = np.sum(normalized[:-1] * normalized[1:], axis=1)

    chunks: list[Chunk] = []
    buffer = sentences[0]
    for i in range(1, len(sentences)):
        if similarities[i - 1] >= threshold and (
            len(buffer) + len(sentences[i]) <= max_chunk_chars
        ):
            buffer += " " + sentences[i]
        else:
            chunks.append(
                Chunk(
                    id=_make_id(),
                    document_id=document_id,
                    content=buffer,
                    metadata={"chunk_type": "semantic"},
                )
            )
            buffer = sentences[i]
    if buffer:
        chunks.append(
            Chunk(
                id=_make_id(),
                document_id=document_id,
                content=buffer,
                metadata={"chunk_type": "semantic"},
            )
        )
    return chunks


def hierarchical_chunker(
    text: str,
    document_id: str,
    big_chunk_size: int = 1024,
    small_chunk_size: int = 256,
    overlap: int = 32,
) -> list[HierarchicalChunk]:
    big_chunks = recursive_chunker(
        text, document_id, chunk_size=big_chunk_size, overlap=0
    )
    result: list[HierarchicalChunk] = []
    for big in big_chunks:
        small = recursive_chunker(
            big.content, document_id, chunk_size=small_chunk_size, overlap=overlap
        )
        parent = HierarchicalChunk(
            id=_make_id(),
            document_id=document_id,
            content=big.content,
            metadata={"chunk_type": "hierarchical_parent"},
        )
        children = [
            HierarchicalChunk(
                id=_make_id(),
                document_id=document_id,
                content=s.content,
                parent_id=parent.id,
                metadata={"chunk_type": "hierarchical_child"},
            )
            for s in small
        ]
        parent.children = children
        result.append(parent)
        result.extend(children)
    return result
