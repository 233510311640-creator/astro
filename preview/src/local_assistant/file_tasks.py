"""Native, human-approved file tasks. Not an MCP/model tool; no network or model calls."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time
from typing import Callable

from .capability_broker import BrokerPolicyViolation, ReadOnlyCapabilityBroker
from .operator_engine import OperatorCancelled, OperatorStateStore, PermissionedOperator, canonical_json
from .permission_center import PermissionCenter, PermissionRootStore, SUPPORTED_CAPABILITIES
from .protected_payload import default_payload_protector
from . import file_browser

VERSION = "0.10.13.2"
MAX_SCAN = 200
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TASK_BYTES = 128 * 1024 * 1024
REVIEW_SECONDS = 120
BUCKETS = {
    "Images": frozenset(".png .jpg .jpeg .webp .gif .svg .bmp .tif .tiff".split()),
    "Documents": frozenset(".pdf .txt .md .docx .doc .odt .rtf".split()),
    "Spreadsheets": frozenset(".csv .xlsx .xls .ods".split()),
    "Presentations": frozenset(".pptx .ppt .odp".split()),
    "Audio": frozenset(".mp3 .wav .flac .aac .m4a .ogg".split()),
    "Video": frozenset(".mp4 .mkv .mov .webm .avi".split()),
}
HELP = ('File tasks\nFiles: add folder\nFiles: folders\nFiles: remove ROOT\nFiles: list ROOT ["relative/folder"]\nFiles: find ROOT "filename fragment" [in "relative/folder"]\nFiles: read ROOT "relative/file.txt"\nFiles: organize ROOT\n'
        'Files: mkdir ROOT "Folder"\nFiles: move ROOT "file.png" to ROOT "Folder/file.png"\n'
        'Files: copy ROOT "file.png" to ROOT "Folder/file.png"\n'
        'Files: create ROOT "note.txt" : text\nFiles: replace ROOT "note.txt" : text\n'
        'Files: review PLAN-ID\nFiles: status\nFiles: undo last\nFiles: recover\n\n'
        'List/find use metadata only; read shows UTF-8 text up to 32 KiB and 200 lines. No model call. '
        'Find searches accessible names within four subfolder levels, 1,000 entries and three seconds; limits are disclosed. '
        'Organize groups recognized file types in the selected root only. It does not recurse. '
        'Every change has an exact review. Stop ends forward work between file steps; rollback completes before a new task.')


def tokens(text: str) -> list[str]:
    pattern = r'"[^"\r\n]*"|[^\s"]+'
    matches = list(re.finditer(pattern, text))
    offset = 0
    out = []
    for match in matches:
        if text[offset:match.start()].strip():
            raise BrokerPolicyViolation("Use complete double quotes around paths containing spaces")
        value = match[0]
        out.append(value[1:-1] if value.startswith('"') else value)
        offset = match.end()
    if text[offset:].strip():
        raise BrokerPolicyViolation("Unclosed path quote")
    return out


def frame(state: str, text: str, **extra: object) -> dict:
    return {"type": "result", "state": state, "text": text, **extra}


class FileTasks:
    def __init__(self, store: PermissionRootStore, state: OperatorStateStore, quarantine: Path):
        self.store, self.state, self.quarantine = store, state, quarantine

    def operator(self) -> PermissionedOperator:
        # Reload the human-managed allowlist for every preparation and execution.
        return PermissionedOperator(PermissionCenter(self.store.load(), None), self.state, self.quarantine)

    def _ready(self) -> None:
        if self.state.incomplete_operations():
            raise BrokerPolicyViolation("An interrupted file operation needs review. Use Files: recover before new file changes")

    @staticmethod
    def _bounded(plan: dict) -> None:
        sizes = [int(a.get("size_bytes", a.get("content_bytes", 0))) for a in plan["actions"]]
        if any(n > MAX_FILE_BYTES for n in sizes) or sum(sizes) > MAX_TASK_BYTES:
            raise BrokerPolicyViolation("Desktop file tasks allow 16 MiB per file and 128 MiB per batch")

    @staticmethod
    def _preview(plan: dict, heading: str = "Proposed file task") -> str:
        lines = [heading + ' (' + str(len(plan['actions'])) + ' actions)', ""]
        for i, action in enumerate(plan["actions"], 1):
            kind = action['kind']
            label = {'mkdir': 'Create folder', 'create_text': 'Create text file', 'replace_text': 'Replace text file',
                     'quarantine': 'Move file to protected quarantine'}.get(kind, kind.capitalize())
            lines.append(str(i) + '. ' + label)
            if kind in {'move', 'copy', 'rename'}:
                source = Path(action.get('source_root_path', action.get('root_path', ''))) / action['source_relative_path']
                target = Path(action.get('destination_root_path', action.get('root_path', ''))) / action['destination_relative_path']
                lines += ['   From: ' + str(source), '   To: ' + str(target)]
            else:
                lines.append('   Path: ' + str(Path(action['root_path']) / action['relative_path']))
            if 'content' in action:
                lines += ['   Full new content (quoted; \\n means a new line):', json.dumps(action['content'], ensure_ascii=False)]
            if 'size_bytes' in action: lines.append('   File size: ' + str(action['size_bytes']) + ' bytes')
            lines.append('')
        reversing = heading != 'Proposed file task'
        lines += ["", "Approve once reverses the reviewed changes." if reversing else "Approve once applies this exact plan. No overwrite except an explicit Replace action.",
                  "Stop pauses reversal between steps; use Files: recover to review the remainder." if reversing else "Stop ends forward work between file steps, then verified changes are rolled back.",
                  "Review expires after two minutes. Undo data stays encrypted on this PC."]
        return "\n".join(lines)

    def _review(self, plan_id: str) -> dict:
        self._ready()
        op = self.operator()
        plan = op.human_review_plan(plan_id)
        if plan["status"] != "proposed":
            raise BrokerPolicyViolation("This plan is not awaiting approval")
        self._bounded(plan)
        return {"type": "review", "kind": "apply", "id": plan_id,
                "fingerprint": plan["fingerprint"], "text": self._preview(plan)}

    def _organize(self, op: PermissionedOperator, root_id: str) -> list[dict]:
        record, view = op.permissions.require(root_id, "move")
        op.permissions.require(root_id, "mkdir")
        entries = []
        with os.scandir(record.path) as iterator:
            for entry in iterator:
                entries.append(entry.name)
                if len(entries) > MAX_SCAN:
                    raise BrokerPolicyViolation("Folder has over 200 direct entries; choose a smaller folder")
        moves, directories, total = [], set(), 0
        for name in sorted(entries, key=lambda s: (s.casefold(), s)):
            candidate = record.path / name
            if candidate.is_symlink() or ReadOnlyCapabilityBroker._is_reparse_point(candidate):
                raise BrokerPolicyViolation("Links or junctions were found; no organization plan was created")
            if not candidate.is_file():
                continue
            bucket = next((b for b, extensions in BUCKETS.items() if candidate.suffix.casefold() in extensions), None)
            if bucket is None:
                continue
            source = view.resolve(name, require_file=True)
            size = source.stat().st_size
            total += size
            if size > MAX_FILE_BYTES or total > MAX_TASK_BYTES:
                raise BrokerPolicyViolation("Organization exceeds the 16 MiB file or 128 MiB batch limit")
            target_dir = record.path / bucket
            if target_dir.exists() or target_dir.is_symlink():
                view.resolve(bucket, require_dir=True)
            else:
                directories.add(bucket)
            moves.append({"kind": "move", "source_root_id": root_id, "source_relative_path": name,
                          "destination_root_id": root_id, "destination_relative_path": bucket + "/" + name})
            if len(moves) + len(directories) > 50:
                raise BrokerPolicyViolation("Organization exceeds 50 actions; choose a smaller folder")
        return [{"kind": "mkdir", "root_id": root_id, "relative_path": name} for name in sorted(directories)] + moves

    def prepare(self, text: str, folder: str | None = None, stopped: Callable[[], bool] = lambda: False) -> dict:
        if not isinstance(text, str) or len(text) > 16384 or not re.match(r'^\s*Files\s*:', text, re.I):
            raise BrokerPolicyViolation("Invalid file-task request")
        body = text.split(":", 1)[1].strip()
        if body.casefold() in {"", "help"}:
            return frame("COMPLETED", HELP)
        if body.casefold() == "add folder":
            if not isinstance(folder, str) or not Path(folder).is_absolute():
                raise BrokerPolicyViolation("Use Files: add folder and choose one existing folder")
            path = self.store._validator.validate_root_path(Path(folder))
            existing = self.store.load()
            # Validate the exact same overlap constraints before displaying approval.
            for record in existing:
                if self.store._validator._is_within(path, record.path) or self.store._validator._is_within(record.path, path):
                    raise BrokerPolicyViolation("This folder overlaps an existing approved folder")
            name = re.sub(r'[^a-z0-9_-]', '-', path.name.casefold()).strip('-_')[:24]
            if not name or not name[0].isalpha():
                name = 'files-' + name
            original, suffix = name, 2
            while any(r.root_id == name for r in existing):
                name = original[:24] + '-' + str(suffix); suffix += 1
            payload = {"root_id": name, "folder": str(path), "capabilities": sorted(SUPPORTED_CAPABILITIES)}
            return {"type": "review", "kind": "grant", "id": name, "payload": payload,
                    "fingerprint": hashlib.sha256(canonical_json(payload).encode()).hexdigest(),
                    "text": "Allow this folder for file tasks?\n\n" + str(path) + "\nFolder name in commands: " + name
                    + "\nAllows listing, text reads, create, replace, copy, move, rename, folders and recoverable quarantine."
                    + "\n\nThis adds lasting folder permission. Each file change still requires its own plan approval."
                    + "\nNo administrator, shell, permanent-delete or network permission is included."}
        if folder is not None:
            raise BrokerPolicyViolation("Unexpected folder selection")
        content_match = re.fullmatch(r'(create|replace)\s+([a-z][a-z0-9_-]*)\s+"([^"\r\n]+)"\s*:\s?([\s\S]*)', body, re.I)
        args = [content_match[1].casefold()] if content_match else tokens(body)
        command = args[0].casefold()
        if command == 'remove' and len(args) == 2:
            self._ready()
            record = next((r for r in self.store.load() if r.root_id == args[1]), None)
            if record is None: raise BrokerPolicyViolation('Unknown approved folder')
            payload = {'root_id': record.root_id, 'path': str(record.path), 'capabilities': sorted(record.capabilities), 'added_at': record.added_at}
            return {'type': 'review', 'kind': 'revoke', 'id': record.root_id, 'payload': payload,
                    'fingerprint': hashlib.sha256(canonical_json(payload).encode()).hexdigest(),
                    'text': 'Remove permission for this folder?\n\n' + str(record.path)
                    + '\nFiles remain in place. Undo of earlier changes may require adding this same folder again.'}
        if command == "folders" and len(args) == 1:
            roots = self.store.load()
            return frame("COMPLETED", "Approved file folders\n\n" + ("\n".join(
                r.root_id + " — " + str(r.path) + "\n  " + ", ".join(sorted(r.capabilities)) for r in roots)
                or "None yet. Send Files: add folder to choose one."))
        if command == "status" and len(args) == 1:
            labels = {'proposed': 'Awaiting approval', 'approved': 'Approved', 'executed': 'Completed',
                      'undone': 'Undone', 'undone_after_restart': 'Undone after restart', 'restart_recovered': 'Recovered',
                      'cancelled_rolled_back': 'Stopped; changes reversed', 'failed_rolled_back': 'Failed; changes reversed',
                      'denied': 'Cancelled or denied before execution', 'expired': 'Expired', 'applying': 'Running',
                      'undoing': 'Undo in progress', 'recovery_required': 'Recovery required'}
            plans = self.state.list_plans()
            lines = ['Recent file tasks', 'Latest ' + str(len(plans)) + ' plans; metadata only.']
            if not plans: lines.append('No file plans yet. Use Files: help to get started.')
            for number, p in enumerate(plans, 1):
                counts = {}
                for action in p.actions:
                    label = {'mkdir': 'create folder', 'create_text': 'create text', 'replace_text': 'replace text'}.get(action['kind'], action['kind'])
                    counts[label] = counts.get(label, 0) + 1
                lines += ['', str(number) + '. ' + labels.get(p.status, p.status),
                          '   ' + ', '.join(str(n) + ' ' + k for k, n in counts.items()),
                          '   Created (UTC): ' + p.created_at, '   Plan: ' + p.plan_id]
                if p.operation_id:
                    status = self.operator().operation_status(p.operation_id)
                    verified = sum(s['verified'] for s in status['steps'])
                    reversed_steps = sum(s['status'] == 'rolled_back' for s in status['steps'])
                    lines += ['   Forward verification receipts: ' + str(verified) + ' / ' + str(len(p.actions)),
                              '   Reversed steps: ' + str(reversed_steps), '   Operation: ' + p.operation_id,
                              '   undo: ' + ('available — Files: undo ' + p.operation_id if p.status == 'executed' else 'unavailable')]
                elif p.status == 'proposed': lines.append('   Review: Files: review ' + p.plan_id)
                else: lines.append('   No operation was started.')
            if self.state.incomplete_operations(): lines.append("Recovery required. Send Files: recover.")
            return frame("COMPLETED", "\n".join(lines))
        if command == "list" and len(args) in {2, 3}:
            return file_browser.browse(lambda: self.operator().permissions, args[1], args[2] if len(args) == 3 else ".", stopped=stopped)
        if command == "find" and (len(args) == 3 or len(args) == 5 and args[3].casefold() == "in"):
            return file_browser.browse(lambda: self.operator().permissions, args[1], args[4] if len(args) == 5 else ".", args[2], stopped)
        if command == "read" and len(args) == 3:
            return file_browser.read(lambda: self.operator().permissions, args[1], args[2], stopped)
        if command == "review" and len(args) == 2:
            return self._review(args[1])
        if command == "recover" and len(args) == 1:
            records = self.state.incomplete_operations()
            if not records: return frame("COMPLETED", "No interrupted file operations need recovery.")
            plans = [self.operator().human_review_plan(r["plan_id"]) for r in records]
            if len(plans) > 20: raise BrokerPolicyViolation("Too many interrupted operations for one desktop review")
            details = self._recovery_details()
            return {"type": "review", "kind": "recover", "id": "recovery", "payload": details,
                    "fingerprint": hashlib.sha256(canonical_json(details).encode()).hexdigest(),
                    "text": "Review rollback of interrupted file tasks. No original action will be replayed.\n\n"
                    + "\n\n".join(self._preview(p, "Reverse remaining changes") for p in plans)}
        self._ready()
        op = self.operator()
        if command == "undo" and len(args) == 2:
            operation_id = args[1]
            if operation_id.casefold() == "last":
                plan = next((p for p in self.state.list_plans(100) if p.status == "executed"), None)
                if plan is None: return frame("COMPLETED", "No completed file task is available to undo.")
                operation_id = plan.operation_id
            operation = self.state.operation(operation_id)
            if operation["status"] != "executed": raise BrokerPolicyViolation("This operation is not available for undo")
            plan = op.human_review_plan(operation["plan_id"])
            return {"type": "review", "kind": "undo", "id": operation_id, "fingerprint": plan["fingerprint"],
                    "text": self._preview(plan, "Undo this completed file task (reverse the actions below)")}
        actions = []
        if command == "organize" and len(args) == 2:
            actions = self._organize(op, args[1])
            if not actions: return frame("COMPLETED", "No supported loose files need organizing. Existing subfolders and unrecognized types are left in place.")
        elif command == "mkdir" and len(args) == 3:
            actions = [{"kind": "mkdir", "root_id": args[1], "relative_path": args[2]}]
        elif command in {"move", "copy"} and len(args) == 6 and args[3].casefold() == "to":
            actions = [{"kind": command, "source_root_id": args[1], "source_relative_path": args[2],
                        "destination_root_id": args[4], "destination_relative_path": args[5]}]
        elif command in {"create", "replace"}:
            match = re.fullmatch(r'(create|replace)\s+([a-z][a-z0-9_-]*)\s+"([^"\r\n]+)"\s*:\s?([\s\S]*)', body, re.I)
            if match:
                actions = [{"kind": command + "_text", "root_id": match[2], "relative_path": match[3], "content": match[4]}]
        if not actions: return frame("REJECTED", "Unrecognized file command.\n\n" + HELP)
        plan = op.propose(actions)
        return self._review(plan["plan_id"])

    def reject(self, review: dict) -> None:
        if review["kind"] == "apply": self.state.reject(review["id"], review["fingerprint"])

    def _recovery_details(self) -> list[dict]:
        return [{'id': r['operation_id'], 'plan': r['plan_id'], 'state': r['status'],
                 'fingerprint': self.state.get_plan(r['plan_id']).fingerprint,
                 'steps': [(s['step_index'], s['status']) for s in self.state.operation_steps(r['operation_id'])]}
                for r in self.state.incomplete_operations()]

    def execute(self, review: dict, fingerprint: str, stopped: Callable[[], bool], progress: Callable[[int, int], None]) -> dict:
        if not hmac.compare_digest(review["fingerprint"], fingerprint):
            raise BrokerPolicyViolation("Approval fingerprint does not match the reviewed task")
        if stopped():
            self.reject(review)
            return frame("CANCELLED", "Cancelled before execution. No file action ran.")
        op = self.operator()
        kind = review["kind"]
        if kind == 'revoke':
            self._ready()
            record = next((r for r in self.store.load() if r.root_id == review['id']), None)
            now = None if record is None else {'root_id': record.root_id, 'path': str(record.path),
                   'capabilities': sorted(record.capabilities), 'added_at': record.added_at}
            if now != review['payload']: raise BrokerPolicyViolation('Folder permission changed; review again')
            self.store.remove(review['id'])
            return frame('COMPLETED', 'Folder permission removed. No file was moved or deleted.')
        if kind == "grant":
            payload = review["payload"]
            record = self.store.add(payload["root_id"], Path(payload["folder"]), payload["capabilities"])
            return frame("COMPLETED", "Folder added: " + record.root_id + "\n" + str(record.path)
                         + "\n\nTry Files: organize " + record.root_id + ". Every file change still needs plan approval.")
        if kind == "recover":
            now = self._recovery_details()
            if now != review["payload"]: raise BrokerPolicyViolation("Recovery state changed; create a fresh review")
            result = op.reconcile_incomplete(cancelled=stopped)
            return frame("COMPLETED" if result["safe_to_start"] else "RECOVERY REQUIRED",
                         "Recovery result (no action replay)\n" + json.dumps(result, indent=2))
        self._ready()
        if kind == "undo":
            operation = self.state.operation(review["id"])
            plan = self.state.get_plan(operation["plan_id"])
            if plan.fingerprint != fingerprint: raise BrokerPolicyViolation("Undo plan changed")
            result = op.undo_operation(review["id"], cancelled=stopped)
            return frame("COMPLETED", "File task undone and reverse changes verified.\nOperation: " + result["operation_id"])
        if kind != "apply": raise BrokerPolicyViolation("Invalid review kind")
        self.state.approve(review["id"], fingerprint)
        try:
            result = op.apply(review["id"], cancelled=stopped, progress=progress)
        except OperatorCancelled:
            plan = self.state.get_plan(review["id"])
            if plan.operation_id is None:
                return frame("CANCELLED", "Stopped before the file operation started. No file action ran.")
            return frame("CANCELLED", "Stopped. Verified file changes were rolled back; no later action ran.\nOperation: " + str(plan.operation_id))
        return frame("COMPLETED", str(result["verified_items"]) + " file actions verified.\nOperation: "
                     + result["operation_id"] + "\nUndo available: send Files: undo last.")


def build_service() -> FileTasks:
    base = Path(os.environ["LOCALAPPDATA"]) / "LocalAssistantBroker"
    return FileTasks(PermissionRootStore(base / "operator_permissions.json"),
                     OperatorStateStore(base / "operator_state.db", default_payload_protector()), base / "Quarantine")


def serve(reader, writer, factory=build_service) -> int:
    line = reader.readline(65537)
    if len(line) > 65536 or not line.endswith('\n'): raise ValueError('Invalid request framing')
    request = json.loads(line)
    if not isinstance(request, dict) or set(request) not in ({"input", "nonce"}, {"input", "nonce", "folder"}):
        raise ValueError("Invalid request envelope")
    nonce = request['nonce']
    if not isinstance(nonce, str) or not re.fullmatch(r'[a-f0-9]{32}', nonce): raise ValueError("Invalid request nonce")
    def emit(value):
        encoded = json.dumps(dict(value, nonce=nonce), ensure_ascii=True, separators=(',', ':'))
        if len(encoded) > 262144: raise BrokerPolicyViolation("File-task response is too large")
        writer.write(encoded + '\n'); writer.flush()
    if request['input'] == 'Files: self-test' and 'folder' not in request:
        from .file_tasks_selftest import run
        run(default_payload_protector())
        emit(frame('COMPLETED', 'FILE_TASK_SELF_TEST_OK'))
        return 0
    stopped = threading.Event()
    controls: queue.Queue = queue.Queue(maxsize=2)
    def control_reader():
        decided = False
        try:
            while True:
                line = reader.readline(4097)
                if not line or len(line) > 4096: break
                value = json.loads(line)
                if not isinstance(value, dict) or value.get('nonce') != nonce: break
                command = value.get('command')
                keys = {'nonce', 'command', 'fingerprint'} if command == 'approve' else {'nonce', 'command'}
                if set(value) != keys or command not in {'approve', 'deny', 'stop'}: break
                if command in {'approve', 'deny'}:
                    if decided: break
                    decided = True
                if command == 'approve' and (not isinstance(value['fingerprint'], str) or not re.fullmatch(r'[a-f0-9]{64}', value['fingerprint'])): break
                if command != 'approve': stopped.set()
                try: controls.put_nowait(value)
                except queue.Full: break
        except Exception:
            pass
        stopped.set()
        try: controls.put_nowait({'command': 'stop'})
        except queue.Full: pass
    threading.Thread(target=control_reader, daemon=True).start()
    review = None
    try:
        service = factory()
        review = service.prepare(request['input'], request.get('folder'), stopped=stopped.is_set)
        if stopped.is_set():
            if review['type'] == 'review': service.reject(review)
            emit(frame('CANCELLED', 'Stopped before execution. No file action ran.')); return 0
        if review['type'] == 'result': emit(review); return 0
        emit({k: review[k] for k in ('type', 'text', 'fingerprint')})
        try: control = controls.get(timeout=REVIEW_SECONDS)
        except queue.Empty: control = {'command': 'stop'}
        if control['command'] != 'approve' or stopped.is_set():
            service.reject(review)
            emit(frame('CANCELLED', 'Approval declined, expired or cancelled. No file action ran.')); return 0
        emit({'type': 'progress', 'verified': 0, 'total': 0})
        result = service.execute(review, control.get('fingerprint', ''), stopped.is_set,
                                 lambda verified, total: emit({'type': 'progress', 'verified': verified, 'total': total}))
        emit(result)
    except Exception as exc:
        incomplete = False
        try: incomplete = bool(service.state.incomplete_operations())
        except Exception: pass
        # No tracebacks or file content in stdout/stderr. Bounded policy messages stay in the UI.
        detail = str(exc)[:350] if isinstance(exc, (BrokerPolicyViolation, OperatorCancelled)) else type(exc).__name__
        emit(frame('RECOVERY REQUIRED' if incomplete else 'FAILED', 'File task could not finish: ' + detail
                   + ('\nSend Files: recover to review rollback. No action is replayed.' if incomplete else '\nNo success is claimed. Use Files: status to inspect receipts.')))
    return 0


def main() -> int:
    try:
        return serve(sys.stdin, sys.stdout)
    except Exception:
        return 1


if __name__ == '__main__':
    # All transactions and terminal frames are committed/flushed before returning.
    # The stdin listener can still be blocked; do not race CPython buffered-reader finalization.
    os._exit(main())
