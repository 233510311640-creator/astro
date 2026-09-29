from __future__ import annotations

import hmac
import secrets

from .protected_payload import PayloadProtectionError, default_payload_protector


def main() -> int:
    try:
        protector = default_payload_protector()
        probe = secrets.token_bytes(64)
        protected = protector.protect(probe)
        recovered = protector.unprotect(protected)
        if not hmac.compare_digest(probe, recovered):
            raise PayloadProtectionError("DPAPI round-trip did not recover the original probe")
    except PayloadProtectionError as exc:
        print(f"[FAIL] Windows current-user DPAPI preflight failed: {exc}")
        return 1
    print("[PASS] Windows current-user DPAPI protected-state preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
