from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    id: str
    document_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HierarchicalChunk(Chunk):
    parent_id: str | None = None
    children: list["HierarchicalChunk"] = field(default_factory=list)


INDEXING_VERSION = 2
"""Bump when chunking strategy changes to invalidate old indexes."""


def make_chunk_id() -> str:
    import uuid
    return uuid.uuid4().hex[:12]

