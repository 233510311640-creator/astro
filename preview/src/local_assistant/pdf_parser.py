"""Bounded PDF-to-text parser process with no file path, model, or action context."""
from __future__ import annotations

import io
import json
import logging
import sys
import warnings

from pypdf import PdfReader


MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_PAGES = 100
MAX_TEXT_BYTES = 1024 * 1024
MAX_PAGE_TEXT_BYTES = 64 * 1024


class PdfFault(Exception):
    pass


def _bounded_utf8(text: str, limit: int) -> tuple[str, bool]:
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    return encoded[:limit].decode("utf-8", "ignore"), True


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(
        char if char in "\n\t" or (
            ord(char) >= 32
            and not 127 <= ord(char) <= 159
            and char not in "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
        ) else "\\u%04x" % ord(char)
        for char in text
    )


def extract(payload: bytes) -> dict:
    if not isinstance(payload, bytes) or not payload.startswith(b"%PDF-"):
        raise PdfFault("PDF_SIGNATURE_INVALID")
    try:
        reader = PdfReader(io.BytesIO(payload), strict=True)
        if reader.is_encrypted:
            raise PdfFault("PDF_ENCRYPTED")
        page_count = len(reader.pages)
    except PdfFault:
        raise
    except Exception as exc:
        raise PdfFault("PDF_PARSE_FAILED") from exc
    if page_count < 1:
        raise PdfFault("PDF_HAS_NO_PAGES")
    if page_count > MAX_PAGES:
        raise PdfFault("PDF_PAGE_LIMIT")

    pages = []
    used = 0
    truncated = False
    for number, page in enumerate(reader.pages, 1):
        try:
            value = page.extract_text(extraction_mode="plain") or ""
        except Exception as exc:
            raise PdfFault("PDF_TEXT_EXTRACTION_FAILED") from exc
        if not isinstance(value, str):
            raise PdfFault("PDF_TEXT_EXTRACTION_FAILED")
        value = _clean(value)
        value, page_truncated = _bounded_utf8(value, MAX_PAGE_TEXT_BYTES)
        remaining = MAX_TEXT_BYTES - used
        value, total_truncated = _bounded_utf8(value, max(0, remaining))
        encoded = value.encode("utf-8")
        used += len(encoded)
        pages.append({"number": number, "text": value})
        if page_truncated or total_truncated:
            truncated = True
        if used >= MAX_TEXT_BYTES and number < page_count:
            truncated = True
            break
    return {
        "ok": True,
        "version": 1,
        "page_count": page_count,
        "pages": pages,
        "text_bytes": used,
        "truncated": truncated,
    }


def main() -> int:
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore")
    try:
        payload = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(payload) > MAX_INPUT_BYTES:
            raise PdfFault("PDF_SIZE_LIMIT")
        value = extract(payload)
    except PdfFault as exc:
        value = {"ok": False, "code": str(exc)}
    except Exception:
        value = {"ok": False, "code": "PDF_PARSE_FAILED"}
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
