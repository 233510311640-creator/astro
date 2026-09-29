from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


Category = Literal["Projects", "Images", "Vectors", "Fonts", "Mockups", "Exports", "Unsorted"]


@dataclass(frozen=True)
class Candidate:
    source: Path
    category: Category
    reason: str
    confidence: float


@dataclass(frozen=True)
class MoveItem:
    source: Path
    destination: Path
    category: Category
    reason: str


@dataclass(frozen=True)
class MovePlan:
    plan_id: str
    created_at: str
    items: tuple[MoveItem, ...]
    fingerprint: str

