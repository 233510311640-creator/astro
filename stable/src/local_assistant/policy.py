from __future__ import annotations

from pathlib import Path

from .config import Settings


class PolicyViolation(RuntimeError):
    pass


class PolicyEngine:
    """Default-deny boundary for filesystem actions."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.blocked_names = {
            "$recycle.bin",
            "appdata",
            "program files",
            "program files (x86)",
            "programdata",
            "windows",
        }

    @staticmethod
    def _within(path: Path, root: Path) -> bool:
        try:
            path.resolve(strict=False).relative_to(root.resolve(strict=False))
            return True
        except ValueError:
            return False

    def assert_scannable(self, path: Path) -> None:
        resolved = path.resolve(strict=False)
        approved_root = next(
            (root.resolve(strict=False) for root in self.settings.scan_roots if self._within(resolved, root)),
            None,
        )
        if approved_root is None:
            raise PolicyViolation(f"Scan outside approved roots: {resolved}")
        if self._within(resolved, self.settings.destination):
            raise PolicyViolation(f"Destination cannot be scanned: {resolved}")
        # Inspect only the user-controlled path beneath the approved root. An
        # approved test or redirected-profile root may itself live below a
        # directory named AppData; treating ancestors outside the capability
        # root as content incorrectly rejects every file below that root.
        relative_parts = resolved.relative_to(approved_root).parts
        if any(part.lower() in self.blocked_names for part in relative_parts):
            raise PolicyViolation(f"Protected path: {resolved}")

    def assert_move(self, source: Path, destination: Path) -> None:
        self.assert_scannable(source)
        if not source.exists() or not source.is_file() or source.is_symlink():
            raise PolicyViolation(f"Invalid move source: {source}")
        if not self._within(destination, self.settings.destination):
            raise PolicyViolation(f"Move outside destination: {destination}")
        if destination.exists():
            raise PolicyViolation(f"Refusing to overwrite: {destination}")
