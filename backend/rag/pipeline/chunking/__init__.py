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
