from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import hashlib
import hmac
import os
from pathlib import Path
import secrets
from typing import Protocol


class PayloadProtectionError(RuntimeError):
    """Raised when protected local operator state cannot be sealed or opened."""


class PayloadProtector(Protocol):
    def protect(self, payload: bytes) -> str: ...

    def unprotect(self, protected: str) -> bytes: ...


class WindowsDpapiProtector:
    """Protect operator payloads for the current Windows user with DPAPI."""

    _CRYPTPROTECT_UI_FORBIDDEN = 0x1

    class _DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    def __init__(self, description: str = "Cypher permissioned operator state"):
        if os.name != "nt":
            raise PayloadProtectionError("Windows DPAPI is only available on Windows")
        self.description = description
        self._crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(self._DataBlob),
            wintypes.LPCWSTR,
            ctypes.POINTER(self._DataBlob),
            wintypes.LPVOID,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(self._DataBlob),
        ]
        self._crypt32.CryptProtectData.restype = wintypes.BOOL
        self._crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(self._DataBlob),
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(self._DataBlob),
            wintypes.LPVOID,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(self._DataBlob),
        ]
        self._crypt32.CryptUnprotectData.restype = wintypes.BOOL
        self._kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        self._kernel32.LocalFree.restype = ctypes.c_void_p

    @classmethod
    def _input_blob(cls, payload: bytes) -> tuple[ctypes.Array[ctypes.c_char], _DataBlob]:
        buffer = ctypes.create_string_buffer(payload, max(1, len(payload)))
        blob = cls._DataBlob(
            len(payload), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        )
        return buffer, blob

    def protect(self, payload: bytes) -> str:
        if not isinstance(payload, bytes):
            raise PayloadProtectionError("DPAPI payload must be bytes")
        _buffer, source = self._input_blob(payload)
        output = self._DataBlob()
        if not self._crypt32.CryptProtectData(
            ctypes.byref(source),
            self.description,
            None,
            None,
            None,
            self._CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output),
        ):
            raise PayloadProtectionError(
                f"DPAPI protection failed with Windows error {ctypes.get_last_error()}"
            )
        try:
            protected = ctypes.string_at(output.pbData, output.cbData)
            return "dpapi:" + base64.b64encode(protected).decode("ascii")
        finally:
            if output.pbData:
                self._kernel32.LocalFree(ctypes.cast(output.pbData, ctypes.c_void_p))

    def unprotect(self, protected: str) -> bytes:
        if not isinstance(protected, str) or not protected.startswith("dpapi:"):
            raise PayloadProtectionError("Protected payload is not a DPAPI envelope")
        try:
            ciphertext = base64.b64decode(protected[6:], validate=True)
        except (ValueError, TypeError) as exc:
            raise PayloadProtectionError("Protected DPAPI payload is invalid") from exc
        _buffer, source = self._input_blob(ciphertext)
        output = self._DataBlob()
        if not self._crypt32.CryptUnprotectData(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            self._CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output),
        ):
            raise PayloadProtectionError(
                f"DPAPI unprotect failed with Windows error {ctypes.get_last_error()}"
            )
        try:
            return ctypes.string_at(output.pbData, output.cbData)
        finally:
            if output.pbData:
                self._kernel32.LocalFree(ctypes.cast(output.pbData, ctypes.c_void_p))


class TestKeyProtector:
    """Portable authenticated test envelope; production Windows code uses DPAPI."""

    def __init__(self, key_path: Path):
        self.key_path = key_path
        key_path.parent.mkdir(parents=True, exist_ok=True)
        if key_path.exists():
            self._key = key_path.read_bytes()
        else:
            self._key = secrets.token_bytes(32)
            with key_path.open("xb") as stream:
                stream.write(self._key)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                key_path.chmod(0o600)
            except OSError:
                pass
        if len(self._key) != 32:
            raise PayloadProtectionError("Test protection key is invalid")

    def _keystream(self, nonce: bytes, length: int) -> bytes:
        blocks: list[bytes] = []
        generated = 0
        counter = 0
        while generated < length:
            block = hmac.new(
                self._key,
                b"stream\0" + nonce + counter.to_bytes(8, "big"),
                hashlib.sha256,
            ).digest()
            blocks.append(block)
            generated += len(block)
            counter += 1
        return b"".join(blocks)[:length]

    def protect(self, payload: bytes) -> str:
        nonce = secrets.token_bytes(16)
        stream = self._keystream(nonce, len(payload))
        ciphertext = bytes(left ^ right for left, right in zip(payload, stream))
        tag = hmac.new(self._key, b"tag\0" + nonce + ciphertext, hashlib.sha256).digest()
        return "test-v1:" + base64.b64encode(nonce + tag + ciphertext).decode("ascii")

    def unprotect(self, protected: str) -> bytes:
        if not isinstance(protected, str) or not protected.startswith("test-v1:"):
            raise PayloadProtectionError("Protected test payload has an invalid envelope")
        try:
            packed = base64.b64decode(protected[8:], validate=True)
        except (ValueError, TypeError) as exc:
            raise PayloadProtectionError("Protected test payload is invalid") from exc
        if len(packed) < 48:
            raise PayloadProtectionError("Protected test payload is truncated")
        nonce, tag, ciphertext = packed[:16], packed[16:48], packed[48:]
        expected = hmac.new(
            self._key, b"tag\0" + nonce + ciphertext, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(tag, expected):
            raise PayloadProtectionError("Protected test payload authentication failed")
        stream = self._keystream(nonce, len(ciphertext))
        return bytes(left ^ right for left, right in zip(ciphertext, stream))


def default_payload_protector() -> PayloadProtector:
    if os.name != "nt":
        raise PayloadProtectionError(
            "The permissioned operator requires Windows DPAPI outside the test suite"
        )
    return WindowsDpapiProtector()
