import re
import uuid

import numpy as np
import spacy

from . import Chunk, HierarchicalChunk


nlp = spacy.load("en_core_web_sm")

SECTION_RE = re.compile(r"^\d+\.\d+\s+")


def _make_id() -> str:
    return uuid.uuid4().hex[:12]


def _extract_sections(text: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in text.split("\n"):
        if SECTION_RE.match(line):
            if current:
                sections.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        sections.append("\n".join(current))
    return sections


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
        sections = [text]
    chunks: list[Chunk] = []
    for sec_idx, section in enumerate(sections):
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
