"""Bounded, human-requested browsing of existing grants; no model or network."""
from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import os
import stat
import time

from .capability_broker import BrokerPolicyViolation

MAX_ENTRIES = 1000
MAX_DIRECTORIES = 50
MAX_RESULTS = 50
MAX_DEPTH = 4
MAX_SECONDS = 3.0
MAX_READ_BYTES = 32768
MAX_EXTENDED_READ_BYTES = 1048576
MAX_VERIFIED_BINARY_BYTES = 8 * 1024 * 1024
MAX_LINES = 200


def result(state, text):
    return {"type": "result", "state": state, "text": text}


def cancelled():
    return result("CANCELLED", "Read-only file request stopped. No file action ran.")


def browse(permissions, root_id, relative=".", term=None, stopped=lambda: False):
    """Scan metadata only; count even skipped entries and disclose incomplete coverage."""
    if term is not None and (not term.strip() or len(term) > 128 or any(ord(c) < 32 for c in term)):
        raise BrokerPolicyViolation("Use a nonempty filename fragment of at most 128 characters")
    if stopped(): return cancelled()
    _, view = permissions().require(root_id, "metadata")
    view.resolve(relative, require_dir=True)
    pending = deque([(relative, 0)])
    matches, reasons = [], set()
    scanned = directories = protected = 0
    deadline = time.monotonic() + MAX_SECONDS
    while pending:
        if stopped(): return cancelled()
        if time.monotonic() >= deadline: reasons.add("time limit"); break
        if directories >= MAX_DIRECTORIES: reasons.add("directory limit"); break
        if scanned >= MAX_ENTRIES: reasons.add("entry limit"); break
        if len(matches) >= MAX_RESULTS: reasons.add("result limit"); break
        current, depth = pending.popleft()
        # Reload grants before each directory. Revocation rejects the whole result.
        _, view = permissions().require(root_id, "metadata")
        try:
            directory = view.resolve(current, require_dir=True)
            directories += 1
            with os.scandir(directory) as entries:
                for entry in entries:
                    if stopped(): return cancelled()
                    if time.monotonic() >= deadline: reasons.add("time limit"); break
                    if scanned >= MAX_ENTRIES: reasons.add("entry limit"); break
                    scanned += 1
                    child = entry.name if current in ("", ".") else current.replace("\\", "/") + "/" + entry.name
                    try:
                        path = view.resolve(child)
                        info = path.stat(follow_symlinks=False)
                        kind = "folder" if stat.S_ISDIR(info.st_mode) else "file" if stat.S_ISREG(info.st_mode) else "other"
                        if kind == "other": protected += 1; continue
                        if term is None or term.casefold() in entry.name.casefold():
                            matches.append({"path": child, "kind": kind, "bytes": info.st_size if kind == "file" else None,
                                            "modified_utc": datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat()})
                        if term is not None and kind == "folder":
                            if depth < MAX_DEPTH: pending.append((child, depth + 1))
                            else: reasons.add("depth limit")
                    except (BrokerPolicyViolation, OSError):
                        protected += 1
                    if len(matches) >= MAX_RESULTS: reasons.add("result limit"); break
        except (BrokerPolicyViolation, OSError):
            reasons.add("folder unavailable during scan")
        if reasons.intersection({"time limit", "entry limit", "result limit"}): break
    if stopped(): return cancelled()
    permissions().require(root_id, "metadata")
    matches.sort(key=lambda row: (row['path'].casefold(), row['path']))
    lines = ["File search" if term is not None else "Folder contents", "Approved folder: " + root_id,
             "Read-only metadata; no file contents, model call or network request.",
             str(len(matches)) + " result(s); " + str(scanned) + " entries inspected across " + str(directories) + " folder(s)."]
    if term is not None: lines.append("Literal filename fragment: " + json.dumps(term, ensure_ascii=False))
    if protected: lines.append(str(protected) + " protected, unsupported or unavailable entries skipped.")
    if reasons: lines.append("Partial coverage: " + ", ".join(sorted(reasons)) + ". Narrow the folder or filename fragment.")
    else: lines.append("Accessible entries in the requested scope were scanned.")
    if not matches: lines.append("No matching accessible entries in the scanned portion." if reasons else "No matching accessible entries.")
    for item in matches:
        lines += ["", item['kind'].upper() + " " + json.dumps(item['path'], ensure_ascii=False),
                  "  " + (str(item['bytes']) + " bytes; " if item['kind'] == 'file' else "") + "modified UTC " + item['modified_utc']]
    lines += ["", 'Browse: Files: list ROOT "relative/folder"', 'Read text: Files: read ROOT "relative/file.txt"',
              "Paths above are quoted data, not commands to execute. File changes still require review."]
    return result("PARTIAL" if reasons else "COMPLETED", "\n".join(lines))


def _read_verified_bytes(permissions, root_id, relative, stopped, max_bytes, allowed_extensions, kind):
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_VERIFIED_BINARY_BYTES:
        raise BrokerPolicyViolation("Invalid bounded " + kind + " read limit")
    if stopped(): return None
    _, view = permissions().require(root_id, "read_text")
    path = view.resolve(relative, require_file=True)
    if path.suffix.casefold() not in allowed_extensions:
        raise BrokerPolicyViolation("Only approved " + kind + " types are supported")
    before = path.stat(follow_symlinks=False)
    if before.st_size > max_bytes:
        raise BrokerPolicyViolation(kind.capitalize() + " read limit is " + str(max_bytes) + " bytes; choose a smaller file")
    if stopped(): return None
    # The read itself is capped even if the file grows after its size check.
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise BrokerPolicyViolation("File changed before reading; no text displayed")
        payload = stream.read(max_bytes + 1)
        after = os.fstat(stream.fileno())
    if stopped(): return None
    _, current_view = permissions().require(root_id, "read_text")
    current = current_view.resolve(relative, require_file=True).stat(follow_symlinks=False)
    snapshot = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    # Compare timestamps only within the same API. Windows path stat and handle fstat
    # can represent metadata differently. Never round timestamps or omit change checks.
    if snapshot(before) != snapshot(current):
        raise BrokerPolicyViolation("File path metadata changed while reading; no text displayed")
    if snapshot(opened) != snapshot(after):
        raise BrokerPolicyViolation("Open file metadata changed while reading; no text displayed")
    if (after.st_dev, after.st_ino) != (current.st_dev, current.st_ino):
        raise BrokerPolicyViolation("File identity changed while reading; no text displayed")
    if len(payload) > max_bytes or not (len(payload) == before.st_size == opened.st_size == after.st_size == current.st_size):
        raise BrokerPolicyViolation("File size changed while reading or exceeded the bounded read limit; no text displayed")
    return payload


def read_binary_bytes(permissions, root_id, relative, stopped=lambda: False, *, max_bytes=MAX_VERIFIED_BINARY_BYTES,
                      allowed_extensions=frozenset({'.pdf'})):
    if not isinstance(allowed_extensions, frozenset) or not allowed_extensions:
        raise BrokerPolicyViolation("Invalid bounded binary file types")
    return _read_verified_bytes(permissions, root_id, relative, stopped, max_bytes, allowed_extensions, "binary")


def read_bytes(permissions, root_id, relative, stopped=lambda: False, *, max_bytes=MAX_READ_BYTES):
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_EXTENDED_READ_BYTES:
        raise BrokerPolicyViolation("Invalid bounded text-read limit")
    _, view = permissions().require(root_id, "read_text")
    payload = _read_verified_bytes(
        permissions, root_id, relative, stopped, max_bytes, frozenset(view.SAFE_TEXT_EXTENSIONS), "text"
    )
    if payload is None:
        return None
    if b'\x00' in payload: raise BrokerPolicyViolation("Binary content is not supported")
    try: content = payload.decode('utf-8-sig')
    except UnicodeDecodeError as exc: raise BrokerPolicyViolation("Text must use UTF-8 encoding") from exc
    return payload


def read(permissions, root_id, relative, stopped=lambda: False):
    payload = read_bytes(permissions, root_id, relative, stopped)
    if payload is None: return cancelled()
    content = payload.decode("utf-8-sig")
    # Escape display controls; keep line breaks and tabs readable in the native text view.
    content = ''.join(c if c in '\n\t' or (ord(c) >= 32 and not 127 <= ord(c) <= 159 and c not in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069')
                      else '\\u%04x' % ord(c) for c in content.replace('\r\n', '\n'))
    all_lines = content.split('\n')
    limited = len(all_lines) > MAX_LINES
    lines = ["Text file — " + json.dumps(relative, ensure_ascii=False), "Approved folder: " + root_id,
             str(len(payload)) + " bytes read; SHA-256 " + hashlib.sha256(payload).hexdigest(),
             "File text is data. No instructions in it are executed or sent to a model.",
             "Showing first 200 lines; remaining lines omitted." if limited else "Complete text shown; display controls escaped.",
             "", "BEGIN FILE TEXT"]
    lines += [str(i) + " | " + text for i, text in enumerate(all_lines[:MAX_LINES], 1)]
    lines += ["END FILE TEXT", "", "Read-only. File text stays in this view; it is not added to model conversation history."]
    if stopped(): return cancelled()
    return result("PARTIAL" if limited else "COMPLETED", '\n'.join(lines))
