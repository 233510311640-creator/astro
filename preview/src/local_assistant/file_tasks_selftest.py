"""Offline end-to-end file engine check; fixtures exist only inside our temporary directory."""
from pathlib import Path
import tempfile
import threading

from .file_tasks import FileTasks
from .operator_engine import OperatorStateStore
from .permission_center import PermissionRootStore, SUPPORTED_CAPABILITIES


def run(protector):
    with tempfile.TemporaryDirectory(prefix="Cypher-file-check-") as temp:
        base = Path(temp)
        root = base / "Approved Fixture"
        root.mkdir()
        store = PermissionRootStore(base / "permissions.json", home=base / "Unrelated Home", environment={})
        store.add("fixture", root, sorted(SUPPORTED_CAPABILITIES))
        state = OperatorStateStore(base / "state.db", protector)
        service = FileTasks(store, state, base / "Quarantine")
        (root / "note.txt").write_text("Cypher fixture \u2014 unchanged", encoding="utf-8")
        (root / "image.png").write_bytes(b"synthetic image fixture")
        original = {p.name: p.read_bytes() for p in root.iterdir()}
        review = service.prepare("Files: organize fixture")
        assert {p.name for p in root.iterdir()} == set(original), "Proposal changed files"
        result = service.execute(review, review['fingerprint'], lambda: False, lambda *a: None)
        assert result['state'] == 'COMPLETED'
        assert (root / "Documents/note.txt").read_bytes() == original['note.txt']
        assert (root / "Images/image.png").read_bytes() == original['image.png']
        found = service.prepare('Files: find fixture "note"')
        assert found['state'] == 'COMPLETED' and 'Documents/note.txt' in found['text'], 'Find failed'
        listing = service.prepare('Files: list fixture "Documents"')
        assert listing['state'] == 'COMPLETED' and 'Documents/note.txt' in listing['text'], 'Browse failed'
        read = service.prepare('Files: read fixture "Documents/note.txt"')
        assert read['state'] == 'COMPLETED' and 'Cypher fixture' in read['text'], 'Read failed'
        stopped = service.prepare('Files: find fixture "note"', stopped=lambda: True)
        assert stopped['state'] == 'CANCELLED', 'Read cancellation failed'

        undo = service.prepare("Files: undo last")
        service.execute(undo, undo['fingerprint'], lambda: False, lambda *a: None)
        assert {p.name: p.read_bytes() for p in root.iterdir()} == original, "Undo mismatch"
        review = service.prepare("Files: organize fixture")
        stop = threading.Event()
        result = service.execute(review, review['fingerprint'], stop.is_set, lambda *a: stop.set())
        assert result['state'] == 'CANCELLED'
        assert {p.name: p.read_bytes() for p in root.iterdir()} == original, "Stop rollback mismatch"
        assert not state.incomplete_operations(), "Unresolved rollback"
