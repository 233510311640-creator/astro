"""Bounded, path-free OOXML text extraction for DOCX, PPTX and XLSX bytes."""
from __future__ import annotations

from io import BytesIO
import json
import posixpath
import re
import sys
import zipfile
from xml.etree import ElementTree as ET


MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 2000
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_PART_BYTES = 4 * 1024 * 1024
MAX_RATIO = 200
MAX_ELEMENTS = 100000
MAX_UNITS = 1000
MAX_UNIT_BYTES = 64 * 1024
MAX_TEXT_BYTES = 1024 * 1024

CONTENT_TYPES = "[Content_Types].xml"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DRAW_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PRESENTATION_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

MAIN_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml": "pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml": "xlsx",
}


class OfficeFault(Exception):
    pass


def _fault(code):
    raise OfficeFault(code)


def _safe_name(name):
    if (not isinstance(name, str) or not name or "\x00" in name or "\\" in name
            or name.startswith("/") or re.match(r"^[A-Za-z]:", name)):
        _fault("OFFICE_PACKAGE_INVALID")
    normalized = posixpath.normpath(name)
    if normalized in {".", ".."} or normalized.startswith("../") or normalized != name.rstrip("/"):
        _fault("OFFICE_PACKAGE_INVALID")
    return normalized


class Package:
    def __init__(self, payload):
        if not payload.startswith(b"PK"):
            _fault("OFFICE_SIGNATURE_INVALID")
        try:
            self.archive = zipfile.ZipFile(BytesIO(payload), "r")
            infos = self.archive.infolist()
        except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile):
            _fault("OFFICE_PACKAGE_INVALID")
        if not infos or len(infos) > MAX_ENTRIES:
            _fault("OFFICE_ARCHIVE_LIMIT")
        self.names = {}
        total = 0
        for info in infos:
            name = _safe_name(info.filename)
            folded = name.casefold()
            if folded in self.names:
                _fault("OFFICE_PACKAGE_INVALID")
            self.names[folded] = name
            if info.is_dir():
                continue
            if info.flag_bits & 1:
                _fault("OFFICE_ENCRYPTED")
            if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                _fault("OFFICE_PACKAGE_INVALID")
            if info.file_size < 0 or info.file_size > MAX_PART_BYTES:
                _fault("OFFICE_ARCHIVE_LIMIT")
            if info.file_size and (info.compress_size <= 0 or info.file_size > info.compress_size * MAX_RATIO):
                _fault("OFFICE_ARCHIVE_LIMIT")
            total += info.file_size
            if total > MAX_ARCHIVE_BYTES:
                _fault("OFFICE_ARCHIVE_LIMIT")

    def canonical(self, name):
        safe = _safe_name(name.lstrip("/"))
        actual = self.names.get(safe.casefold())
        if actual is None:
            _fault("OFFICE_PACKAGE_INVALID")
        return actual

    def read(self, name, *, required=True):
        try:
            actual = self.canonical(name)
        except OfficeFault:
            if not required:
                return None
            raise
        try:
            value = self.archive.read(actual)
        except (OSError, RuntimeError, zipfile.BadZipFile):
            _fault("OFFICE_PACKAGE_INVALID")
        if len(value) > MAX_PART_BYTES:
            _fault("OFFICE_ARCHIVE_LIMIT")
        return value

    def xml(self, name, *, required=True):
        data = self.read(name, required=required)
        if data is None:
            return None
        upper = data.upper()
        if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
            _fault("OFFICE_XML_INVALID")
        try:
            root = ET.fromstring(data)
        except (ET.ParseError, ValueError, RecursionError):
            _fault("OFFICE_XML_INVALID")
        if sum(1 for _ in root.iter()) > MAX_ELEMENTS:
            _fault("OFFICE_ARCHIVE_LIMIT")
        return root


def _relationships_path(part):
    folder, leaf = posixpath.split(part)
    return posixpath.join(folder, "_rels", leaf + ".rels")


def _target(part, value):
    if (not isinstance(value, str) or not value or "\\" in value or value.startswith("/")
            or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value)):
        _fault("OFFICE_PACKAGE_INVALID")
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(part), value))
    if joined in {".", ".."} or joined.startswith("../"):
        _fault("OFFICE_PACKAGE_INVALID")
    return joined


def _relationships(package, part):
    root = package.xml(_relationships_path(part), required=False)
    result = {}
    if root is None:
        return result
    for rel in root.findall("{" + PKG_REL_NS + "}Relationship"):
        rid, target = rel.get("Id"), rel.get("Target")
        if not rid or rid in result:
            _fault("OFFICE_PACKAGE_INVALID")
        result[rid] = {
            "type": rel.get("Type", ""),
            "target": None if rel.get("TargetMode") == "External" else _target(part, target),
        }
    return result


def _content_type(package):
    root = package.xml(CONTENT_TYPES)
    matches = []
    for node in root:
        if not node.tag.endswith("}Override"):
            continue
        kind = MAIN_TYPES.get(node.get("ContentType"))
        if kind:
            matches.append((kind, node.get("PartName", "").lstrip("/")))
    if len(matches) != 1:
        _fault("OFFICE_FORMAT_UNSUPPORTED")
    kind, main = matches[0]
    return kind, package.canonical(main)


def _clean(value, limit=160):
    value = "".join(
        char if ord(char) >= 32 and not 127 <= ord(char) <= 159
        and char not in "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069" else " "
        for char in (value or "")
    )
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _prefix_utf8(value, maximum):
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum:
        return value, False
    return encoded[:maximum].decode("utf-8", "ignore"), True


class Output:
    def __init__(self):
        self.units = []
        self.text_bytes = 0
        self.truncated = False

    def add(self, label, text):
        text = "\n".join(_clean(line, MAX_UNIT_BYTES) for line in text.splitlines() if _clean(line, MAX_UNIT_BYTES))
        if not text:
            return True
        if len(self.units) >= MAX_UNITS or self.text_bytes >= MAX_TEXT_BYTES:
            self.truncated = True
            return False
        budget = min(MAX_UNIT_BYTES, MAX_TEXT_BYTES - self.text_bytes)
        text, cut = _prefix_utf8(text, budget)
        text = text.rstrip()
        if not text:
            self.truncated = True
            return False
        self.units.append({"number": len(self.units) + 1, "label": _clean(label), "text": text})
        self.text_bytes += len(text.encode("utf-8"))
        self.truncated |= cut
        return not cut


def _word(package, main, output):
    root = package.xml(main)
    paragraph = "{" + WORD_NS + "}p"
    text = "{" + WORD_NS + "}t"
    tab = "{" + WORD_NS + "}tab"
    br = "{" + WORD_NS + "}br"
    number = 0
    for node in root.iter(paragraph):
        chunks = []
        for child in node.iter():
            if child.tag == text and child.text:
                chunks.append(child.text)
            elif child.tag == tab:
                chunks.append("\t")
            elif child.tag == br:
                chunks.append("\n")
        value = "".join(chunks)
        if value.strip():
            number += 1
            if not output.add("paragraph " + str(number), value):
                break


def _presentation(package, main, output):
    root = package.xml(main)
    rels = _relationships(package, main)
    ids = root.findall(".//{" + PRESENTATION_NS + "}sldId")
    if len(ids) > 500:
        _fault("OFFICE_ARCHIVE_LIMIT")
    for number, node in enumerate(ids, 1):
        relationship = rels.get(node.get("{" + REL_NS + "}id"))
        if not relationship or relationship["target"] is None or not relationship["type"].endswith("/slide"):
            _fault("OFFICE_PACKAGE_INVALID")
        slide = package.xml(relationship["target"])
        lines = []
        for paragraph in slide.iter("{" + DRAW_NS + "}p"):
            value = "".join(item.text or "" for item in paragraph.iter("{" + DRAW_NS + "}t"))
            if value.strip():
                lines.append(value)
        if lines and not output.add("slide " + str(number), "\n".join(lines)):
            break


def _shared_strings(package, rels):
    relationship = next((value for value in rels.values() if value["type"].endswith("/sharedStrings")), None)
    if relationship is None:
        return []
    if relationship["target"] is None:
        _fault("OFFICE_PACKAGE_INVALID")
    root = package.xml(relationship["target"])
    values = []
    for item in root.findall("{" + SHEET_NS + "}si"):
        values.append("".join(node.text or "" for node in item.iter("{" + SHEET_NS + "}t")))
        if len(values) > 100000:
            _fault("OFFICE_ARCHIVE_LIMIT")
    return values


def _cell_value(cell, shared):
    kind = cell.get("t", "n")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.iter("{" + SHEET_NS + "}t"))
    node = cell.find("{" + SHEET_NS + "}v")
    value = node.text if node is not None and node.text is not None else ""
    if kind == "s":
        try:
            index = int(value)
        except ValueError:
            _fault("OFFICE_PACKAGE_INVALID")
        if not 0 <= index < len(shared):
            _fault("OFFICE_PACKAGE_INVALID")
        return shared[index]
    if kind == "b":
        return "TRUE" if value == "1" else "FALSE" if value == "0" else ""
    return value


def _spreadsheet(package, main, output):
    root = package.xml(main)
    rels = _relationships(package, main)
    shared = _shared_strings(package, rels)
    sheets = root.findall(".//{" + SHEET_NS + "}sheet")
    if len(sheets) > 256:
        _fault("OFFICE_ARCHIVE_LIMIT")
    for sheet_index, sheet in enumerate(sheets, 1):
        relationship = rels.get(sheet.get("{" + REL_NS + "}id"))
        if not relationship or relationship["target"] is None or not relationship["type"].endswith("/worksheet"):
            _fault("OFFICE_PACKAGE_INVALID")
        name = _clean(sheet.get("name", "Sheet " + str(sheet_index)), 80) or "Sheet " + str(sheet_index)
        worksheet = package.xml(relationship["target"])
        fallback_row = 0
        for row in worksheet.iter("{" + SHEET_NS + "}row"):
            fallback_row += 1
            number = row.get("r") or str(fallback_row)
            if not re.fullmatch(r"[1-9][0-9]{0,6}", number):
                _fault("OFFICE_PACKAGE_INVALID")
            cells = []
            for cell in row.findall("{" + SHEET_NS + "}c"):
                reference = cell.get("r", "?")
                if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]{0,6}", reference):
                    reference = "?"
                value = _cell_value(cell, shared)
                if value.strip():
                    cells.append(reference + ": " + value)
            if cells and not output.add('sheet "' + name + '" · row ' + number, " | ".join(cells)):
                return


def parse(payload):
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_INPUT_BYTES:
        _fault("OFFICE_SIZE_LIMIT")
    package = Package(payload)
    kind, main = _content_type(package)
    output = Output()
    if kind == "docx":
        _word(package, main, output)
    elif kind == "pptx":
        _presentation(package, main, output)
    else:
        _spreadsheet(package, main, output)
    return {
        "ok": True,
        "version": 1,
        "kind": kind,
        "unit_count": len(output.units),
        "units": output.units,
        "text_bytes": output.text_bytes,
        "truncated": output.truncated,
    }


def main():
    try:
        payload = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        result = parse(payload)
    except OfficeFault as exc:
        result = {"ok": False, "code": str(exc)}
    except Exception:
        result = {"ok": False, "code": "OFFICE_PARSE_FAILED"}
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
