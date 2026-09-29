from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


FAST_MODEL = "qwen3.5:9b-q4_K_M"
DEEP_MODEL = "gpt-oss:20b"
VISION_MODEL = "qwen3.5:9b-q4_K_M"
MODEL_PROVIDER = "custom"
MAX_INPUT_CHARS = 32_000
CYPHER_VERSION = "0.7.0-core-preview10.13.2"

_SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_MODEL_NAME = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}(?::[A-Za-z0-9][A-Za-z0-9._-]{0,63})?$"
)


class CypherCoreError(RuntimeError):
    pass


class HermesUnavailableError(CypherCoreError):
    pass


class UnsupportedHermesError(CypherCoreError):
    pass


@dataclass(frozen=True)
class ModelRoles:
    """Validated, replaceable model assignments; roles never grant authority."""

    fast: str = FAST_MODEL
    deep: str = DEEP_MODEL
    vision: str = VISION_MODEL
    provider: str = MODEL_PROVIDER

    @staticmethod
    def _validated_name(value: object, fallback: str) -> str:
        candidate = str(value or fallback).strip()
        if not _MODEL_NAME.fullmatch(candidate):
            raise ValueError(f"Invalid local model name: {candidate!r}")
        return candidate

    @classmethod
    def from_mapping(cls, values: Mapping[str, object] | None) -> ModelRoles:
        settings = values or {}
        provider = str(settings.get("model_provider") or MODEL_PROVIDER).strip()
        if provider != MODEL_PROVIDER:
            raise ValueError("Cypher's local model provider must remain 'custom'")
        return cls(
            fast=cls._validated_name(settings.get("fast_model"), FAST_MODEL),
            deep=cls._validated_name(settings.get("deep_model"), DEEP_MODEL),
            vision=cls._validated_name(settings.get("vision_model"), VISION_MODEL),
            provider=provider,
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "fast_model": self.fast,
            "deep_model": self.deep,
            "vision_model": self.vision,
            "model_provider": self.provider,
        }


def build_core_instructions(
    assistant_name: str = "Cypher",
    model_roles: ModelRoles | None = None,
) -> str:
    name = assistant_name.strip() or "Cypher"
    roles = model_roles or ModelRoles()
    return (
        f"You are {name}, the user's private local Windows 11 resident assistant—not "
        "the Neo4j query language or another product. When the user says Cypher, this "
        "assistant, this version, our project, or we, interpret it as this local-assistant "
        f"project unless clearly specified otherwise. Current core version: {CYPHER_VERSION}. "
        "Chat uses the local Hermes orchestration gateway. Explicit Research: requests use bounded Wikipedia discovery or supplied public HTTPS pages; explicit Research papers: requests use bounded OpenAlex scholarly-abstract discovery. Both run in a separate worker with no action tools; "
        f"Ollama runs the local models. The configured fast role is {roles.fast}; the deep "
        f"role is {roles.deep}; and the multimodal/fallback role is {roles.vision}. These "
        "are replaceable, benchmark-gated roles rather than permanent product dependencies; "
        "this resident UI does not currently accept image attachments. Hermes and the "
        "capability broker enforce tools, approved roots, and human approvals; never bypass "
        "them or imply unrestricted computer access. Be practical, direct, and context-aware. "
        "Distinguish advice or a proposed plan from an executed action. Never claim an action "
        "succeeded without a confirming tool result. The current run input is authoritative. "
        "When it contains a clear task, answer that task; do not mistake transport, continuation, "
        "or output-length markers for the user's request. Every submitted chat task uses a fresh Hermes "
        "session; conversation continuity comes only from explicit bounded successful-turn history. "
        "Research runs separately and is not added to that history. Never infer an unfinished task from hidden server-side session state. Ask one focused clarification only when "
        "missing information materially changes the result. Do not invent memories, "
        "capabilities, files, or system state beyond these facts and tool results. Do not "
        "expose hidden reasoning. Never describe web browsing, code execution, file access, "
        "vision input, memory, voice, or computer control as available unless the current "
        "runtime capability contract or an actually supplied tool explicitly confirms it."
        " When an exact permissioned MCP tool schema is already visible, call that tool directly; "
        "never wrap an eager tool in tool_search, tool_describe, or tool_call. Only when the exact "
        "schema is absent and Hermes supplies the progressive-disclosure bridge, use tool_search "
        "once, copy the returned tool name verbatim, use tool_describe only if its exact schema is "
        "still needed, and invoke it through tool_call. Never reconstruct an MCP wire name from a "
        "display or server name; punctuation in a display name may be sanitized in the wire name. "
        "Do not claim the capability is absent before that bounded discovery "
        "attempt. If Hermes supplies neither the discovery brokers nor the exact tool, state that "
        "limitation. Never substitute terminal, shell, built-in file tools, or invented commands for "
        "a requested permissioned MCP workflow."
    )


@dataclass(frozen=True)
class RuntimeCapabilityContract:
    """Authoritative, conservative capability facts supplied by Hermes at runtime."""

    enabled_toolsets: tuple[str, ...] = ()
    toolset_inventory_verified: bool = False
    memory_write_api: bool = False
    audio_api: bool = False
    realtime_voice: bool = False

    @classmethod
    def from_payloads(
        cls,
        capabilities_payload: dict[str, Any],
        toolsets_payload: dict[str, Any] | None,
    ) -> RuntimeCapabilityContract:
        features = capabilities_payload.get("features")
        if not isinstance(features, dict):
            features = {}
        usable: list[str] = []
        verified = isinstance(toolsets_payload, dict)
        entries = toolsets_payload.get("toolsets", []) if verified else []
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                if (
                    isinstance(name, str)
                    and name.strip()
                    and entry.get("enabled") is True
                    and entry.get("configured", True) is True
                ):
                    usable.append(name.strip())
        return cls(
            enabled_toolsets=tuple(sorted(set(usable))),
            toolset_inventory_verified=verified,
            memory_write_api=features.get("memory_write_api") is True,
            audio_api=features.get("audio_api") is True,
            realtime_voice=features.get("realtime_voice") is True,
        )

    def prompt_contract(self) -> str:
        toolsets = ", ".join(self.enabled_toolsets) or "none reported"
        inventory = "verified" if self.toolset_inventory_verified else "unverified"
        return (
            "AUTHORITATIVE RUNTIME CAPABILITY CONTRACT (this overrides general model "
            "knowledge and marketing-style descriptions): The resident interface supports "
            "local text chat, bounded model routing, streaming, status, stop, and one-time "
            "approval responses. Explicit Vision: commands may read one PNG from an approved folder through the isolated local worker; image attachments and live vision are unavailable. "
            "The visible desktop app has local Windows MIC and READ ALOUD controls. MIC only drafts text for review; Send is required. These are not Hermes audio tools or realtime voice. "
            f"Hermes built-in toolset inventory is {inventory}; usable enabled toolsets: "
            f"{toolsets}. Durable memory writes: {str(self.memory_write_api).lower()}. "
            f"Audio API: {str(self.audio_api).lower()}. Realtime voice: "
            f"{str(self.realtime_voice).lower()}. Additional MCP tools may appear for an "
            "individual run. Call a visible exact MCP tool directly. When Hermes instead supplies "
            "tool_search, tool_describe, and tool_call, use those bounded discovery brokers only "
            "for an explicitly requested capability, preserve a returned tool name verbatim, and "
            "call only a discovered exact schema. "
            "Claim or use a substantive capability only when its exact schema is actually present. "
            "Never infer a capability from the selected model. Web browsing, code execution, "
            "file/system actions, and computer control are conditional tool abilities—not "
            "general abilities—and must not be claimed without an available matching tool."
        )

    def disclosure(self) -> str:
        toolsets = ", ".join(self.enabled_toolsets) or "none reported"
        toolset_line = (
            f"- Enabled built-in toolsets from verified inventory: {toolsets}."
            if self.toolset_inventory_verified
            else "- Built-in toolset inventory could not be verified, so none are claimed."
        )
        return (
            "Available now:\n"
            "- Local text chat and planning with Qwen for fast work and GPT-OSS for deeper reasoning.\n"
            "- Hermes streaming, run status, verified Stop, and one-time approval or denial.\n"
            "- Explicit Vision: ask or describe reads one named PNG in an approved folder with one installed local vision model; interpretations are not verified OCR.\n"
            "- Local Windows MIC drafts recognized speech in the input box for review; Send is required. READ ALOUD speaks a bounded part of the response. No wake word or saved raw audio.\n"
            f"{toolset_line}\n\n"
            "Not built into this interface yet:\n"
            "- Image attachments, live camera, screenshots, or unrestricted vision input.\n"
            "- Always-on voice, durable personal memory, or unrestricted computer control.\n\n"
            "Web, code, file, and system actions are conditional. I may use them only when "
            "the exact tool is supplied for the current run and its permissions and approvals allow it."
        )


def is_capability_disclosure_request(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", text.casefold())
    normalized = " ".join(normalized.split())
    if len(normalized) > 160:
        return False
    exact = {
        "what can you do",
        "what can cypher do",
        "what are your capabilities",
        "what tools do you have",
        "describe your capabilities",
        "what can this assistant do",
        "which features are available",
    }
    return normalized in exact


@dataclass(frozen=True)
class RoutingDecision:
    profile: str
    model: str
    provider: str
    display_label: str
    reason: str
    input_text: str
    model_options: dict[str, Any]


@dataclass(frozen=True)
class SseEvent:
    name: str
    data: Any


@dataclass(frozen=True)
class DisplayEvent:
    kind: str
    text: str = ""
    status: str = ""
    request_id: str | None = None


@dataclass(frozen=True)
class HermesCapabilities:
    run_submission: bool
    run_status: bool
    run_events_sse: bool
    run_stop: bool
    run_approval_response: bool

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> HermesCapabilities:
        features = payload.get("features")
        if not isinstance(features, dict):
            features = {}
        return cls(
            run_submission=features.get("run_submission") is True,
            run_status=features.get("run_status") is True,
            run_events_sse=features.get("run_events_sse") is True,
            run_stop=features.get("run_stop") is True,
            run_approval_response=features.get("run_approval_response") is True,
        )

    def require_interactive_core(self) -> None:
        required = {
            "run_submission": self.run_submission,
            "run_status": self.run_status,
            "run_events_sse": self.run_events_sse,
            "run_stop": self.run_stop,
            "run_approval_response": self.run_approval_response,
        }
        missing = [name for name, available in required.items() if not available]
        if missing:
            raise UnsupportedHermesError(
                "Hermes does not expose the required Cypher Core features: "
                + ", ".join(missing)
            )


def validate_loopback_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Hermes endpoint must be an HTTP loopback address")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Hermes endpoint must not contain credentials, a query, or a fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("Hermes endpoint must not contain an API path")
    return endpoint.rstrip("/")


def _validated_input(text: str) -> str:
    normalized = text.strip().lstrip("\ufeff\u200b")
    if not normalized:
        raise ValueError("Cypher input cannot be empty")
    if len(normalized) > MAX_INPUT_CHARS:
        raise ValueError(f"Cypher input cannot exceed {MAX_INPUT_CHARS} characters")
    return normalized


def _strip_mode_command(text: str) -> tuple[str | None, str]:
    match = re.match(
        r"^(?:(?:>\s*)|(?:[-*+]\s+))?(?:`{1,3}\s*)?/(fast|deep|vision)(?:\s+|$)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, text
    remainder = re.sub(r"\s*`{1,3}$", "", text[match.end() :]).strip()
    if not remainder:
        raise ValueError("A mode command must be followed by a request")
    return match.group(1).lower(), remainder


def _deep_score(text: str) -> int:
    lower = text.casefold()
    score = 0
    if len(text) >= 1_800:
        score += 2
    elif len(text) >= 800:
        score += 1
    if text.count("\n") >= 6:
        score += 1

    strong_markers = (
        "analyze deeply",
        "deep analysis",
        "root cause",
        "threat model",
        "risk register",
        "system architecture",
        "research plan",
        "evidence-based assessment",
        "debug this failure",
        "diagnose this failure",
        "compare the evidence",
    )
    if any(marker in lower for marker in strong_markers):
        score += 2

    reasoning_markers = (
        "trade-off",
        "tradeoff",
        "risks and benefits",
        "multiple constraints",
        "step-by-step",
        "assumptions and uncertainty",
        "counterargument",
        "long-term strategy",
    )
    score += min(sum(marker in lower for marker in reasoning_markers), 2)
    return score


def select_route(
    text: str,
    requested_mode: str = "auto",
    *,
    has_image: bool = False,
    model_roles: ModelRoles | None = None,
) -> RoutingDecision:
    roles = model_roles or ModelRoles()
    input_text = _validated_input(text)
    command_mode, input_text = _strip_mode_command(input_text)
    mode = command_mode or requested_mode.strip().lower()
    if mode not in {"auto", "fast", "deep", "vision"}:
        raise ValueError("requested_mode must be auto, fast, deep, or vision")

    if has_image or mode == "vision":
        return RoutingDecision(
            profile="vision",
            model=roles.vision,
            provider=roles.provider,
            display_label=f"Vision · {roles.vision}",
            reason="image input requires the on-demand multimodal profile",
            input_text=input_text,
            model_options={},
        )
    if mode == "deep":
        return RoutingDecision(
            profile="deep",
            model=roles.deep,
            provider=roles.provider,
            display_label=f"Deep · {roles.deep}",
            reason="deep mode was explicitly requested",
            input_text=input_text,
            model_options={"reasoning_effort": "medium"},
        )
    if mode == "auto" and _deep_score(input_text) >= 2:
        return RoutingDecision(
            profile="deep",
            model=roles.deep,
            provider=roles.provider,
            display_label=f"Deep · {roles.deep}",
            reason="bounded local routing detected a complex reasoning request",
            input_text=input_text,
            model_options={"reasoning_effort": "medium"},
        )
    return RoutingDecision(
        profile="fast",
        model=roles.fast,
        provider=roles.provider,
        display_label=f"Fast · {roles.fast}",
        reason=(
            "fast mode was explicitly requested"
            if mode == "fast"
            else "ordinary requests use the measured reflex profile"
        ),
        input_text=input_text,
        model_options={},
    )


def parse_sse_lines(lines: Iterable[bytes | str]) -> Iterator[SseEvent]:
    event_name = "message"
    data_parts: list[str] = []

    def dispatch() -> SseEvent | None:
        nonlocal event_name, data_parts
        if not data_parts:
            event_name = "message"
            return None
        raw_data = "\n".join(data_parts)
        try:
            data: Any = json.loads(raw_data)
        except json.JSONDecodeError:
            data = raw_data
        event = SseEvent(event_name, data)
        event_name = "message"
        data_parts = []
        return event

    for raw_line in lines:
        line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else raw_line
        line = line.rstrip("\r\n")
        if not line:
            event = dispatch()
            if event is not None:
                yield event
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if field == "event":
            event_name = value or "message"
        elif field == "data":
            data_parts.append(value)
    event = dispatch()
    if event is not None:
        yield event


def _event_name(event: SseEvent) -> str:
    if event.name != "message":
        return event.name
    if isinstance(event.data, dict):
        for key in ("type", "event"):
            value = event.data.get(key)
            if isinstance(value, str) and value:
                return value
    return event.name


def _text_delta(data: Any) -> str:
    if not isinstance(data, dict):
        return data if isinstance(data, str) else ""
    for key in ("delta", "text", "content"):
        value = data.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            nested = value.get("text") or value.get("content")
            if isinstance(nested, str):
                return nested
    return ""


def project_display_event(event: SseEvent) -> DisplayEvent | None:
    name = _event_name(event).lower()
    data = event.data if isinstance(event.data, dict) else {}

    # Raw chain-of-thought is neither displayed nor retained by Cypher Core.
    if "reasoning" in name or "thinking" in name:
        return None
    if name in {
        "message.delta",
        "assistant.delta",
        "response.output_text.delta",
        "text.delta",
        "run.output.delta",
    }:
        text = _text_delta(event.data)
        return DisplayEvent("text_delta", text=text) if text else None
    if name in {"tool.start", "tool.started", "hermes.tool.progress"}:
        tool_name = data.get("name") or data.get("tool") or "approved tool"
        return DisplayEvent("tool_start", status=f"Running {tool_name}")
    if name in {"tool.complete", "tool.completed"}:
        tool_name = data.get("name") or data.get("tool") or "tool"
        return DisplayEvent("tool_complete", status=f"Completed {tool_name}")
    if name in {"approval.request", "approval_requested"}:
        request_id = data.get("request_id")
        description = data.get("description")
        if not isinstance(description, str):
            description = "Hermes needs permission for one bounded action."
        return DisplayEvent(
            "approval_request",
            text=description[:240],
            status="Approval required",
            request_id=request_id if isinstance(request_id, str) else None,
        )
    if name in {"clarify.request", "clarification.request"}:
        request_id = data.get("request_id")
        return DisplayEvent(
            "clarification_request",
            status="Cypher needs clarification",
            request_id=request_id if isinstance(request_id, str) else None,
        )
    if name in {"run.completed", "response.completed", "message.complete"}:
        return DisplayEvent("completed", status="Completed")
    if name in {"run.cancelled", "response.cancelled"}:
        return DisplayEvent("cancelled", status="Cancelled")
    if "error" in name or name in {"run.failed", "response.failed"}:
        return DisplayEvent("error", status="Hermes reported a run failure")
    if name in {"subagent.start", "delegation.start"}:
        return DisplayEvent("status", status="Specialist started")
    if name in {"subagent.complete", "delegation.complete"}:
        return DisplayEvent("status", status="Specialist completed")
    return None


class HermesRunClient:
    def __init__(self, endpoint: str, api_key: str, timeout: int = 300):
        self.endpoint = validate_loopback_endpoint(endpoint)
        if not api_key or any(character in api_key for character in "\r\n"):
            raise ValueError("A valid Hermes API key is required")
        self._api_key = api_key
        self.timeout = timeout

    def __repr__(self) -> str:
        return f"HermesRunClient(endpoint={self.endpoint!r}, timeout={self.timeout!r})"

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        accept: str = "application/json",
        timeout: int | None = None,
    ):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.endpoint}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Accept": accept,
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            return urlopen(request, timeout=timeout or self.timeout)
        except HTTPError as error:
            # Do not include response bodies: providers may echo request content in errors.
            raise HermesUnavailableError(
                f"Hermes returned HTTP {error.code} for {method} {path}"
            ) from error
        except (OSError, URLError, TimeoutError) as error:
            raise HermesUnavailableError(f"Hermes did not respond to {method} {path}") from error

    def _request_json(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        with self._request(method, path, payload) as response:
            try:
                value = json.load(response)
            except json.JSONDecodeError as error:
                raise HermesUnavailableError(
                    f"Hermes returned invalid JSON for {method} {path}"
                ) from error
        if not isinstance(value, dict):
            raise HermesUnavailableError(f"Hermes returned an unexpected value for {method} {path}")
        return value

    def capabilities(self) -> HermesCapabilities:
        payload = self._request_json("GET", "/v1/capabilities")
        return HermesCapabilities.from_payload(payload)

    def start_run(
        self,
        decision: RoutingDecision,
        session_id: str,
        *,
        instructions: str | None = None,
    ) -> str:
        if not _SESSION_ID.fullmatch(session_id):
            raise ValueError("Invalid Cypher session id")
        payload: dict[str, Any] = {
            "input": decision.input_text,
            "session_id": session_id,
            "model": decision.model,
            "provider": decision.provider,
        }
        if decision.model_options:
            payload["model_options"] = decision.model_options
        payload["instructions"] = instructions or build_core_instructions()
        response = self._request_json("POST", "/v1/runs", payload)
        run_id = response.get("run_id")
        if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
            raise HermesUnavailableError("Hermes returned an invalid run id")
        return run_id

    def stream_events(self, run_id: str) -> Iterator[SseEvent]:
        if not _RUN_ID.fullmatch(run_id):
            raise ValueError("Invalid Hermes run id")
        with self._request(
            "GET",
            f"/v1/runs/{run_id}/events",
            accept="text/event-stream",
        ) as response:
            yield from parse_sse_lines(response)

    def get_run(self, run_id: str) -> dict[str, Any]:
        if not _RUN_ID.fullmatch(run_id):
            raise ValueError("Invalid Hermes run id")
        return self._request_json("GET", f"/v1/runs/{run_id}")

    def stop_run(self, run_id: str) -> dict[str, Any]:
        if not _RUN_ID.fullmatch(run_id):
            raise ValueError("Invalid Hermes run id")
        return self._request_json("POST", f"/v1/runs/{run_id}/stop", {})

    def resolve_approval(self, run_id: str, choice: str) -> dict[str, Any]:
        if not _RUN_ID.fullmatch(run_id):
            raise ValueError("Invalid Hermes run id")
        normalized = choice.strip().lower()
        if normalized not in {"once", "deny"}:
            raise ValueError("Cypher exposes only one-time approval or denial")
        return self._request_json(
            "POST",
            f"/v1/runs/{run_id}/approval",
            {"choice": normalized},
        )
