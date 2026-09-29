from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from local_assistant.cypher_core import (
    CYPHER_VERSION,
    DEEP_MODEL,
    FAST_MODEL,
    VISION_MODEL,
    DisplayEvent,
    HermesCapabilities,
    HermesRunClient,
    ModelRoles,
    RuntimeCapabilityContract,
    SseEvent,
    UnsupportedHermesError,
    build_core_instructions,
    is_capability_disclosure_request,
    parse_sse_lines,
    project_display_event,
    select_route,
    validate_loopback_endpoint,
)


class CoreIdentityTests(unittest.TestCase):
    def test_identity_disambiguates_cypher_and_states_only_bounded_facts(self):
        instructions = build_core_instructions()
        self.assertIn("private local Windows 11 resident assistant", instructions)
        self.assertIn("Neo4j query language", instructions)
        self.assertIn(CYPHER_VERSION, instructions)
        self.assertIn("Never claim an action succeeded", instructions)
        self.assertIn("Do not invent memories", instructions)
        self.assertIn("never bypass", instructions.lower())
        self.assertIn("this resident UI does not currently accept image attachments", instructions)
        self.assertIn("Never describe web browsing", instructions)
        self.assertIn("call that tool directly", instructions)
        self.assertIn("use tool_search once", instructions)
        self.assertIn("tool_describe", instructions)
        self.assertIn("tool name verbatim", instructions)
        self.assertIn("Do not claim the capability is absent", instructions)
        self.assertIn("Never substitute terminal, shell, built-in file tools", instructions)
        self.assertIn("fresh Hermes session", instructions)
        self.assertIn("explicit bounded successful-turn history", instructions)
        self.assertIn("hidden server-side session state", instructions)
        self.assertNotIn("you can freely access", instructions.lower())

    def test_identity_reports_configured_roles_without_granting_authority(self):
        roles = ModelRoles(fast="new-fast:7b", deep="new-deep:20b", vision="new-vision:8b")
        instructions = build_core_instructions(model_roles=roles)
        self.assertIn("new-fast:7b", instructions)
        self.assertIn("new-deep:20b", instructions)
        self.assertIn("new-vision:8b", instructions)
        self.assertIn("replaceable, benchmark-gated roles", instructions)


class RouterTests(unittest.TestCase):
    def test_model_roles_are_replaceable_and_validated(self):
        roles = ModelRoles.from_mapping(
            {
                "fast_model": "candidate-fast:8b",
                "deep_model": "candidate-deep:22b",
                "vision_model": "candidate-vision:9b",
                "model_provider": "custom",
            }
        )
        self.assertEqual(select_route("answer briefly", model_roles=roles).model, "candidate-fast:8b")
        self.assertEqual(select_route("/deep diagnose this failure", model_roles=roles).model, "candidate-deep:22b")
        self.assertEqual(select_route("inspect", has_image=True, model_roles=roles).model, "candidate-vision:9b")
        with self.assertRaises(ValueError):
            ModelRoles.from_mapping({"fast_model": "https://remote.example/model"})
        with self.assertRaises(ValueError):
            ModelRoles.from_mapping({"model_provider": "cloud"})

    def test_ordinary_request_uses_fast_model(self):
        decision = select_route("Make a simple schedule for this afternoon.")
        self.assertEqual(decision.model, FAST_MODEL)
        self.assertEqual(decision.profile, "fast")

    def test_explicit_commands_are_removed_before_submission(self):
        deep = select_route("/deep compare the evidence and identify uncertainty")
        fast = select_route("/fast answer briefly")
        self.assertEqual(deep.model, DEEP_MODEL)
        self.assertEqual(deep.input_text, "compare the evidence and identify uncertainty")
        self.assertEqual(deep.model_options, {"reasoning_effort": "medium"})
        self.assertEqual(fast.model, FAST_MODEL)
        self.assertEqual(fast.input_text, "answer briefly")

    def test_mode_commands_survive_common_markdown_copy_wrappers(self):
        inline = select_route("`/deep compare the evidence`")
        quote = select_route("> /deep compare the evidence")
        bullet = select_route("- /deep compare the evidence")
        invisible = select_route("\u200b/deep compare the evidence")
        self.assertEqual(inline.model, DEEP_MODEL)
        self.assertEqual(inline.input_text, "compare the evidence")
        self.assertEqual(quote.model, DEEP_MODEL)
        self.assertEqual(quote.input_text, "compare the evidence")
        self.assertEqual(bullet.model, DEEP_MODEL)
        self.assertEqual(invisible.model, DEEP_MODEL)

    def test_complex_request_escalates_with_bounded_local_rules(self):
        decision = select_route(
            "Create an evidence-based assessment with assumptions and uncertainty, "
            "then compare the evidence and explain the trade-offs."
        )
        self.assertEqual(decision.model, DEEP_MODEL)
        self.assertIn("bounded local routing", decision.reason)
        self.assertEqual(
            select_route("Create a concise 12-point risk register for Cypher").model,
            DEEP_MODEL,
        )

    def test_image_uses_vision_model(self):
        self.assertEqual(select_route("Explain this", has_image=True).model, VISION_MODEL)
        self.assertEqual(select_route("/vision inspect this screenshot").model, VISION_MODEL)

    def test_invalid_or_empty_input_is_rejected(self):
        for text in ("", "   ", "/deep"):
            with self.assertRaises(ValueError):
                select_route(text)
        with self.assertRaises(ValueError):
            select_route("hello", requested_mode="unrestricted")


class EventTests(unittest.TestCase):
    def test_sse_parser_handles_comments_json_and_multiline_data(self):
        lines = [
            b": keepalive\n",
            b"event: message.delta\n",
            b'data: {"delta":"Hello"}\n',
            b"\n",
            "event: note\n",
            "data: line one\n",
            "data: line two\n",
            "\n",
        ]
        events = list(parse_sse_lines(lines))
        self.assertEqual(events[0], SseEvent("message.delta", {"delta": "Hello"}))
        self.assertEqual(events[1], SseEvent("note", "line one\nline two"))

    def test_projection_exposes_text_and_status_but_not_reasoning(self):
        self.assertEqual(
            project_display_event(SseEvent("message.delta", {"delta": "Hi"})),
            DisplayEvent("text_delta", text="Hi"),
        )
        self.assertEqual(
            project_display_event(SseEvent("tool.start", {"name": "sandbox_list"})),
            DisplayEvent("tool_start", status="Running sandbox_list"),
        )
        self.assertIsNone(
            project_display_event(SseEvent("response.reasoning.delta", {"delta": "secret"}))
        )

    def test_approval_projection_does_not_expose_arguments(self):
        projected = project_display_event(
            SseEvent(
                "approval.request",
                {"request_id": "approve-1", "arguments": {"path": "private.txt"}},
            )
        )
        self.assertEqual(projected.request_id, "approve-1")
        self.assertEqual(projected.status, "Approval required")
        self.assertNotIn("private", repr(projected))


class CapabilityTests(unittest.TestCase):
    def test_runtime_contract_is_conservative_and_uses_verified_toolsets_only(self):
        contract = RuntimeCapabilityContract.from_payloads(
            {
                "features": {
                    "memory_write_api": False,
                    "audio_api": False,
                    "realtime_voice": False,
                }
            },
            {
                "toolsets": [
                    {"name": "web", "enabled": True, "configured": True},
                    {"name": "terminal", "enabled": True, "configured": False},
                    {"name": "file", "enabled": False, "configured": True},
                ]
            },
        )
        self.assertEqual(contract.enabled_toolsets, ("web",))
        self.assertTrue(contract.toolset_inventory_verified)
        prompt = contract.prompt_contract()
        self.assertIn("usable enabled toolsets: web", prompt)
        self.assertIn("Explicit Vision: commands may read one PNG", prompt)
        self.assertIn("MIC only drafts text for review; Send is required", prompt)
        self.assertIn("conditional tool abilities", prompt)
        self.assertIn("bounded discovery brokers", prompt)
        self.assertIn("Call a visible exact MCP tool directly", prompt)
        self.assertIn("preserve a returned tool name verbatim", prompt)
        disclosure = contract.disclosure()
        self.assertIn("Explicit Vision: ask or describe", disclosure)
        self.assertIn("Local Windows MIC drafts recognized speech", disclosure)
        self.assertIn("Image attachments, live camera", disclosure)
        self.assertIn("unrestricted computer control", disclosure)
        self.assertIn("Web, code, file, and system actions are conditional", disclosure)

    def test_missing_toolset_inventory_never_becomes_an_ambient_capability(self):
        contract = RuntimeCapabilityContract.from_payloads({"features": {}}, None)
        self.assertFalse(contract.toolset_inventory_verified)
        self.assertEqual(contract.enabled_toolsets, ())
        self.assertIn("usable enabled toolsets: none reported", contract.prompt_contract())

    def test_capability_question_detection_is_exact_and_bounded(self):
        self.assertTrue(is_capability_disclosure_request("What can you do?"))
        self.assertTrue(is_capability_disclosure_request("What tools do you have"))
        self.assertFalse(is_capability_disclosure_request("What can you do with this design file?"))

    def test_official_approval_response_capability_is_accepted(self):
        capabilities = HermesCapabilities.from_payload(
            {
                "features": {
                    "run_submission": True,
                    "run_status": True,
                    "run_events_sse": True,
                    "run_stop": True,
                    "run_approval_response": True,
                }
            }
        )
        capabilities.require_interactive_core()

    def test_missing_required_features_are_rejected(self):
        capabilities = HermesCapabilities.from_payload(
            {"features": {"run_submission": True, "run_status": True}}
        )
        with self.assertRaises(UnsupportedHermesError):
            capabilities.require_interactive_core()


class _HermesHandler(BaseHTTPRequestHandler):
    received_payload = None
    run_payload = None
    authorization = None
    approval_payload = None

    def log_message(self, format, *args):
        pass

    def _send_json(self, value, status=200):
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        type(self).authorization = self.headers.get("Authorization")
        if self.path == "/v1/capabilities":
            self._send_json(
                {
                    "features": {
                        "run_submission": True,
                        "run_status": True,
                        "run_events_sse": True,
                        "run_stop": True,
                        "run_approval_response": True,
                    }
                }
            )
        elif self.path == "/v1/runs/run_123/events":
            body = (
                'event: message.delta\ndata: {"delta":"Hello"}\n\n'
                'event: run.completed\ndata: {"status":"completed"}\n\n'
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/v1/runs/run_123":
            self._send_json({"run_id": "run_123", "status": "completed", "output": "Hello"})
        else:
            self._send_json({"error": "missing"}, 404)

    def do_POST(self):
        type(self).authorization = self.headers.get("Authorization")
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        type(self).received_payload = payload
        if self.path == "/v1/runs":
            type(self).run_payload = payload
            self._send_json({"run_id": "run_123", "status": "started"})
        elif self.path == "/v1/runs/run_123/stop":
            self._send_json({"status": "stopping"})
        elif self.path == "/v1/runs/run_123/approval":
            type(self).approval_payload = payload
            self._send_json({"status": "resolved", "choice": payload.get("choice")})
        else:
            self._send_json({"error": "missing"}, 404)


class ClientIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _HermesHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_full_run_stream_status_and_stop_flow(self):
        client = HermesRunClient(self.endpoint, "test-secret", timeout=2)
        capabilities = client.capabilities()
        capabilities.require_interactive_core()
        decision = select_route("Answer briefly", requested_mode="fast")
        run_id = client.start_run(decision, "cypher-session-1")
        events = list(client.stream_events(run_id))
        status = client.get_run(run_id)
        stopped = client.stop_run(run_id)
        approved = client.resolve_approval(run_id, "once")

        self.assertEqual(run_id, "run_123")
        self.assertEqual(project_display_event(events[0]).text, "Hello")
        self.assertEqual(status["output"], "Hello")
        self.assertEqual(stopped["status"], "stopping")
        self.assertEqual(approved["choice"], "once")
        self.assertEqual(_HermesHandler.approval_payload, {"choice": "once"})
        self.assertEqual(_HermesHandler.authorization, "Bearer test-secret")
        self.assertEqual(_HermesHandler.run_payload["model"], FAST_MODEL)
        self.assertEqual(_HermesHandler.run_payload["provider"], "custom")
        self.assertIn(
            "private local Windows 11 resident assistant",
            _HermesHandler.run_payload["instructions"],
        )
        self.assertIn(CYPHER_VERSION, _HermesHandler.run_payload["instructions"])

    def test_secret_is_not_exposed_and_ids_cannot_change_paths(self):
        client = HermesRunClient(self.endpoint, "test-secret", timeout=2)
        self.assertNotIn("test-secret", repr(client))
        for invalid_id in ("../health", "run/other", "", "?secret"):
            with self.assertRaises(ValueError):
                client.get_run(invalid_id)

    def test_only_loopback_http_endpoints_are_allowed(self):
        self.assertEqual(validate_loopback_endpoint(self.endpoint), self.endpoint)
        for endpoint in (
            "https://127.0.0.1:8642",
            "http://192.168.1.10:8642",
            "http://example.com",
            "http://user:password@127.0.0.1:8642",
            "http://127.0.0.1:8642/v1",
        ):
            with self.assertRaises(ValueError):
                validate_loopback_endpoint(endpoint)

    def test_native_approval_is_limited_to_once_or_deny(self):
        client = HermesRunClient(self.endpoint, "test-secret", timeout=2)
        self.assertEqual(client.resolve_approval("run_123", "deny")["choice"], "deny")
        for choice in ("always", "session", "allow_all"):
            with self.assertRaises(ValueError):
                client.resolve_approval("run_123", choice)


if __name__ == "__main__":
    unittest.main()
