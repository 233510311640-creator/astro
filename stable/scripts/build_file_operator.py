"""Build the deterministic, standard-library-only native file worker; no downloads."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODULES = ('__init__.py', 'file_tasks.py', 'file_browser.py', 'file_tasks_selftest.py', 'operator_engine.py',
           'permission_center.py', 'protected_payload.py', 'capability_broker.py', 'inventory_broker.py')


def build(destination=None):
    destination = Path(destination) if destination else ROOT / 'windows/Cypher.CorePreview/file_operator.pyz'
    files = {'__main__.py': b'import os\nfrom local_assistant.file_tasks import main\nos._exit(main())\n'}
    for name in MODULES:
        files['local_assistant/' + name] = (ROOT / 'src/local_assistant' / name).read_bytes()
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            entry = zipfile.ZipInfo(name, (2026, 9, 10, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, files[name], compresslevel=9)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


if __name__ == '__main__': print(build())
