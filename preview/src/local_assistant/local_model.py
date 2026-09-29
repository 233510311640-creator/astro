from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


SYSTEM_PROMPT = """Reasoning: high
You are the private reasoning component of a Windows agent.
You run locally and have no direct authority over the computer. Be concise and honest.
Never claim that an action was completed unless the host application supplies a tool result.
Never ask for passwords, recovery keys, one-time codes, or banking credentials.
Potential computer actions must be handled by the host permission engine, not invented by you.
"""


class LocalModelUnavailable(RuntimeError):
    pass


class LocalModel:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        base_url = base_url or os.environ.get("LOCAL_ASSISTANT_MODEL_URL", "http://127.0.0.1:11434")
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("The local model endpoint must be an HTTP loopback address")
        self.base_url = base_url.rstrip("/")
        self.model = model or os.environ.get("LOCAL_ASSISTANT_MODEL", "local-assistant-brain:latest")

    def chat(self, message: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            "temperature": 0.3,
            "max_tokens": 1200,
        }
        request = Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                data = json.load(response)
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise LocalModelUnavailable(str(error)) from error
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as error:
            raise LocalModelUnavailable("Unexpected response from local model") from error
