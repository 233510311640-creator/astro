from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def user_home() -> Path:
    return Path(os.environ.get("USERPROFILE", Path.home())).resolve()


@dataclass(frozen=True)
class Settings:
    home: Path
    data_dir: Path
    destination: Path
    scan_roots: tuple[Path, ...]

    @classmethod
    def default(cls) -> "Settings":
        home = user_home()
        data_dir = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")) / "LocalAssistant"
        destination = home / "Desktop" / "graphic"
        roots = tuple(
            path
            for path in (
                home / "Desktop",
                home / "Downloads",
                home / "Documents",
                home / "Pictures",
            )
            if path.exists()
        )
        return cls(home=home, data_dir=data_dir, destination=destination, scan_roots=roots)

