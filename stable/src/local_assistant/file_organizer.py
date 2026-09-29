from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import shutil
import uuid

from .audit import AuditStore
from .config import Settings
from .models import Candidate, MoveItem, MovePlan
from .policy import PolicyEngine, PolicyViolation


PROJECT_EXTENSIONS = {".psd", ".psb", ".ai", ".ait", ".indd", ".idml", ".xd", ".fig", ".afdesign", ".xcf", ".kra"}
VECTOR_EXTENSIONS = {".svg", ".eps"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".gif", ".bmp", ".heic", ".avif"}
FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}
MOCKUP_WORDS = {"mockup", "template", "scene", "device", "packaging"}
EXPORT_WORDS = {"export", "final", "render", "output", "thumbnail", "banner", "poster", "logo"}


class GraphicOrganizer:
    def __init__(self, settings: Settings, policy: PolicyEngine, audit: AuditStore):
        self.settings = settings
        self.policy = policy
        self.audit = audit

    @staticmethod
    def _hidden(path: Path) -> bool:
        return any(part.startswith(".") for part in path.parts)

    @staticmethod
    def _project_directory(path: Path) -> bool:
        try:
            return any(child.suffix.lower() in PROJECT_EXTENSIONS for child in path.parent.iterdir() if child.is_file())
        except OSError:
            return True

    def classify(self, path: Path) -> Candidate | None:
        suffix = path.suffix.lower()
        words = {part.lower() for part in path.stem.replace("-", "_").split("_")}
        if suffix in PROJECT_EXTENSIONS:
            return Candidate(path, "Projects", f"Design project format {suffix}", 1.0)
        if suffix in FONT_EXTENSIONS:
            return Candidate(path, "Fonts", f"Font format {suffix}", 0.99)
        if suffix in VECTOR_EXTENSIONS:
            return Candidate(path, "Vectors", f"Vector/document asset format {suffix}", 0.9)
        if suffix in IMAGE_EXTENSIONS:
            if words & MOCKUP_WORDS:
                return Candidate(path, "Mockups", "Filename suggests a mockup/template asset", 0.86)
            if words & EXPORT_WORDS:
                return Candidate(path, "Exports", "Filename suggests a rendered/exported design", 0.82)
            return Candidate(path, "Images", f"Image format {suffix}; requires human preview", 0.55)
        return None

    def scan(self) -> list[Candidate]:
        candidates: list[Candidate] = []
        seen: set[Path] = set()
        for root in self.settings.scan_roots:
            for current, directories, filenames in os.walk(root, followlinks=False):
                current_path = Path(current)
                directories[:] = [
                    name
                    for name in directories
                    if not self._hidden(current_path / name)
                    and not (current_path / name).is_symlink()
                    and not self.policy._within(current_path / name, self.settings.destination)
                ]
                for filename in filenames:
                    path = current_path / filename
                    try:
                        self.policy.assert_scannable(path)
                    except PolicyViolation:
                        continue
                    if path in seen or path.is_symlink() or self._hidden(path):
                        continue
                    candidate = self.classify(path)
                    if candidate is None:
                        continue
                    # Loose files are safe to propose. Assets already in a project directory stay put.
                    if candidate.category != "Projects" and self._project_directory(path):
                        continue
                    candidates.append(candidate)
                    seen.add(path)
        return sorted(candidates, key=lambda item: (-item.confidence, str(item.source).lower()))

    def _unique_destination(self, category: str, source: Path, reserved: set[Path]) -> Path:
        directory = self.settings.destination / category
        candidate = directory / source.name
        index = 2
        while candidate.exists() or candidate in reserved:
            candidate = directory / f"{source.stem} ({index}){source.suffix}"
            index += 1
        reserved.add(candidate)
        return candidate

    def make_plan(self, candidates: Iterable[Candidate]) -> MovePlan:
        reserved: set[Path] = set()
        items = tuple(
            MoveItem(
                source=item.source,
                destination=self._unique_destination(item.category, item.source, reserved),
                category=item.category,
                reason=item.reason,
            )
            for item in candidates
        )
        payload = [
            {"source": str(item.source), "destination": str(item.destination), "category": item.category}
            for item in items
        ]
        fingerprint = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return MovePlan(
            plan_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            items=items,
            fingerprint=fingerprint,
        )

    def execute(self, plan: MovePlan, approval_fingerprint: str, stop_file: Path) -> str:
        if approval_fingerprint != plan.fingerprint:
            raise PolicyViolation("Approval does not match the displayed plan")
        if stop_file.exists():
            raise PolicyViolation("Emergency stop is active")
        self.audit.begin(plan.plan_id, plan.fingerprint)
        try:
            for ordinal, item in enumerate(plan.items):
                if stop_file.exists():
                    raise PolicyViolation("Emergency stop activated during operation")
                self.policy.assert_move(item.source, item.destination)
                item.destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(item.source), str(item.destination))
                self.audit.record_move(plan.plan_id, ordinal, item.source, item.destination)
        except Exception:
            self.audit.finish(plan.plan_id, "interrupted")
            raise
        self.audit.finish(plan.plan_id)
        return plan.plan_id

    def undo(self, operation_id: str) -> int:
        restored = 0
        for source_text, destination_text, status in self.audit.moves_for(operation_id):
            if status != "moved":
                continue
            source, destination = Path(source_text), Path(destination_text)
            if not destination.exists() or source.exists():
                continue
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), str(source))
            restored += 1
        self.audit.mark_undone(operation_id)
        return restored
