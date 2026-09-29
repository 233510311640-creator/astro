"""Build the deterministic, standard-library-only OOXML parser archive."""
from pathlib import Path
import hashlib
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP = (2026, 9, 19, 0, 0, 0)


def build():
    target = ROOT / "windows/Cypher.CorePreview/office_parser.pyz"
    files = {
        "__main__.py": b"from local_assistant.office_parser import main\nraise SystemExit(main())\n",
        "local_assistant/__init__.py": b"",
        "local_assistant/office_parser.py": (ROOT / "src/local_assistant/office_parser.py").read_bytes(),
    }
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            entry = zipfile.ZipInfo(name, TIMESTAMP)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, files[name], compresslevel=9)
    return hashlib.sha256(target.read_bytes()).hexdigest()


if __name__ == "__main__":
    print(build())
