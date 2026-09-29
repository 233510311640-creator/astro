"""Deterministic document worker package; excludes file action engines and research clients."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODULES = ('__init__.py', 'document_worker.py', 'file_browser.py', 'permission_center.py',
           'capability_broker.py', 'inventory_broker.py', 'runtime_worker.py')


def build():
    target = ROOT / 'windows/Cypher.CorePreview/document_worker.pyz'
    files = {'__main__.py': b'import os\nfrom local_assistant.document_worker import main\nos._exit(main())\n'}
    for name in MODULES: files['local_assistant/' + name] = (ROOT / 'src/local_assistant' / name).read_bytes()
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            entry = zipfile.ZipInfo(name, (2026, 9, 15, 0, 0, 0))
            entry.create_system = 3; entry.external_attr = 0o100644 << 16; entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, files[name], compresslevel=9)
    return hashlib.sha256(target.read_bytes()).hexdigest()


if __name__ == '__main__': print(build())
