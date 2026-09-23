"""Real loopback HTTP and DOCX analysis integration, with offline chat jobs."""
import base64
from copy import deepcopy
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ayqyn.api import server
from ayqyn.chat.agent import run_turn as real_run_turn
from ayqyn.chat.service import ACTIVE
from test_analyzer import docx, para
from test_chat_service import ANSWER, question, result_fixture


class ChatHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.start_patch("ayqyn.api.server.ANALYSIS_ROOT", self.root / "analyses")
        self.start_patch("ayqyn.api.server.RESEARCH_ROOT", self.root / "research")
        env = patch.dict(os.environ, {"OPENAI_API_KEY": "", "OPENAI_MODEL": "", "OPENAI_BASE_URL": ""})
        env.start()
        self.addCleanup(env.stop)
        self.transport = self.start_patch("ayqyn.providers.llm.request_json_api",
                                         side_effect=AssertionError("Live API forbidden"))
        self.runner = self.start_patch("ayqyn.chat.agent.run_turn", return_value=deepcopy(ANSWER))
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=lambda: self.http.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.http.server_port}"
        self.addCleanup(self.close_server)

    def close_server(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=5)
        if hasattr(self.http, "chat_service"):
            self.http.chat_service.close()
        self.transport.assert_not_called()

    def start_patch(self, target, *args, **kwargs):
        patcher = patch(target, *args, **kwargs)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def request(self, path, payload=None, *, headers=None, raw=None, method=None):
        data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
        request = Request(self.base + path, data=data, method=method,
                          headers={"Content-Type": "application/json", **(headers or {})})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            return response.status, json.load(response)

    def analyze(self):
        texts = [["3.4. Структура", "Отдел планирования",
                  "Отдел осуществляет мониторинг исполнения государственных программ."],
                 ["3.4. Структура", "Отдел планирования", "Отдел учета", "4.1. Функции",
                  "Отдел А обеспечивает подготовку ежегодных отчетов о выполнении программ.",
                  "Отдел Б обеспечивает подготовку ежегодных отчетов о выполнении программ."]]
        payload = {side: {"name": side + ".docx", "data": base64.b64encode(
            docx("".join(para(text) for text in rows))).decode()} for side, rows in zip(("before", "after"), texts)}
        code, result = self.request("/api/analyze", payload)
        self.assertEqual(code, 200, result)
        self.assertRegex(result["analysis_id"], r"^a-[a-f0-9]{32}$")
        return result

    def poll(self, identifier, turn_id):
        for _ in range(200):
            code, result = self.request(f"/api/analyses/{identifier}/chat/turns/{turn_id}")
            self.assertEqual(code, 200, result)
            if result["status"] not in ACTIVE:
                return result
            time.sleep(0.005)
        self.fail("HTTP turn did not complete")

    def test_real_analyze_exposes_persistent_snapshot_sources_and_empty_history(self):
        result = self.analyze()
        identifier = result["analysis_id"]
        self.assertEqual(result["mode"], "rules")
        self.assertEqual(result["chat"]["state"], "requires_model")
        self.assertTrue(result["findings"])
        code, snapshot = self.request(f"/api/analyses/{identifier}")
        self.assertEqual(code, 200)
        self.assertEqual(snapshot["result"]["findings"], result["findings"])
        code, history = self.request(f"/api/analyses/{identifier}/chat")
        self.assertEqual((code, history["conversation_version"], history["messages"]), (200, 0, []))
        fragment = result["before"]["paragraphs"][0]
        code, source = self.request(f"/api/analyses/{identifier}/source?fragment_id=before:{fragment['id']}")
        self.assertEqual(code, 200, source)
        self.assertEqual(source["fragment"]["text"], fragment["text"])
        self.assertEqual(source["document"]["name"], result["before"]["name"])
        self.assertTrue((self.root / "analyses" / identifier / "snapshot.json").exists())
        self.runner.assert_not_called()

    def test_submit_poll_and_duplicate_client_id_round_trip(self):
        identifier = self.analyze()["analysis_id"]
        entered, release = threading.Event(), threading.Event()
        def run(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Test gate timeout")
            return deepcopy(ANSWER)
        self.runner.side_effect = run
        self.addCleanup(release.set)
        path = f"/api/analyses/{identifier}/chat/messages"
        code, turn = self.request(path, question())
        self.assertEqual(code, 202)
        self.assertTrue(entered.wait(2))
        code, duplicate = self.request(path, question())
        self.assertEqual(code, 202)
        self.assertEqual(duplicate["turn_id"], turn["turn_id"])
        code, conflict = self.request(path, question("new-question", 1))
        self.assertEqual((code, conflict["error"]["code"]), (409, "turn_in_progress"))
        release.set()
        final = self.poll(identifier, turn["turn_id"])
        self.assertEqual((final["status"], final["conversation_version"]), ("completed", 2))
        self.assertEqual(self.runner.call_count, 1)
        code, duplicate = self.request(path, question())
        self.assertEqual((code, duplicate["turn_id"]), (200, turn["turn_id"]))
        code, conflict = self.request(path, question("new-question", 0))
        self.assertEqual((code, conflict["error"]["code"]), (409, "version_conflict"))

    def test_actual_agent_reads_context_validates_citation_and_persists_http_answer(self):
        result = self.analyze()
        identifier = result["analysis_id"]
        fragment = result["before"]["paragraphs"][-1]
        canonical_id = "before:" + fragment["id"]
        answer = {
            "outcome": "answered",
            "blocks": [{"kind": "claim", "basis": "source", "text": fragment["text"],
                        "citation_ids": ["citation-one"], "finding_ids": []}],
            "citations": [{"id": "citation-one", "fragment_id": canonical_id, "quote": fragment["text"]}],
            "analysis_relation": "not_determined", "claims_absence": False,
            "limitations": ["Этот ответ подтверждает формулировку до реорганизации; новая редакция не проверена."],
        }
        def call(name, arguments, number):
            return ({"role": "assistant", "content": None, "tool_calls": [
                {"id": "call-" + str(number), "type": "function",
                 "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}}]},
                {"total_tokens": 5})
        driver = self.start_patch("ayqyn.providers.llm.agent_turn", side_effect=[
            call("read_context", {"fragment_id": canonical_id, "scope": "section", "offset": 0}, 1),
            call("finish_answer", answer, 2),
        ])
        self.runner.side_effect = real_run_turn
        payload = question(text="Как была сформулирована обязанность до реорганизации?")
        code, turn = self.request(f"/api/analyses/{identifier}/chat/messages", payload)
        self.assertEqual(code, 202)
        final = self.poll(identifier, turn["turn_id"])
        self.assertEqual(final["status"], "completed", final)
        message = final["assistant_message"]
        self.assertEqual(message["outcome"], "answered")
        self.assertEqual(message["human_review"], "unreviewed")
        self.assertEqual(message["metrics"]["model_calls"], 2)
        self.assertEqual(message["metrics"]["search_method"], "not_used")
        self.assertEqual(driver.call_count, 2)
        citation = message["citations"][0]
        self.assertEqual(citation["fragment_id"], canonical_id)
        self.assertEqual(citation["document_name"], result["before"]["name"])
        self.assertEqual(citation["sha256"], result["before"]["sha256"])
        self.assertIsNone(citation["page"])
        code, source = self.request(f"/api/analyses/{identifier}/source?fragment_id={citation['fragment_id']}")
        self.assertEqual(code, 200)
        self.assertIn(citation["quote"], source["fragment"]["text"])
        self.assertEqual(citation["source_locator"]["original_fragment_id"], fragment["id"])
        code, history = self.request(f"/api/analyses/{identifier}/chat")
        self.assertEqual(code, 200)
        self.assertEqual(history["conversation_version"], 2)
        self.assertEqual(history["messages"][1], message)
        code, snapshot = self.request(f"/api/analyses/{identifier}")
        self.assertEqual(code, 200)
        self.assertEqual(snapshot["result"]["findings"], result["findings"])
        trace = self.root / "analyses" / identifier / "turns" / turn["turn_id"] / "trace.json"
        self.assertEqual([event["tool"] for event in json.loads(trace.read_text(encoding="utf-8"))["events"]],
                         ["read_context", "finish_answer"])

    def test_bad_origin_and_host_cannot_read_or_submit_chat(self):
        identifier = self.analyze()["analysis_id"]
        for headers in ({"Origin": "https://attacker.example"}, {"Origin": "null"},
                        {"Host": "attacker.example"}):
            for suffix, payload in (("", None), ("/chat/messages", question())):
                with self.subTest(headers=headers, suffix=suffix):
                    code, result = self.request(f"/api/analyses/{identifier}{suffix}", payload, headers=headers)
                    self.assertEqual((code, result["error"]["code"]), (403, "invalid_origin"))
        code, _ = self.request(f"/api/analyses/{identifier}/chat", headers={"Origin": self.base})
        self.assertEqual(code, 200)
        self.runner.assert_not_called()

    def test_unknown_ids_and_foreign_sources_return_structured_errors(self):
        identifier = self.analyze()["analysis_id"]
        other = self.http.chat_service.store.save(result_fixture("foreign", "foreign"))["analysis_id"]
        code, turn = self.request(f"/api/analyses/{other}/chat/messages", question())
        self.assertEqual(code, 202)
        self.poll(other, turn["turn_id"])
        cases = [(f"/api/analyses/a-{'0' * 32}", "analysis_not_found"),
                 (f"/api/analyses/{identifier}/source?fragment_id=before:foreign1", "source_not_found"),
                 (f"/api/analyses/{identifier}/chat/turns/{turn['turn_id']}", "turn_not_found")]
        for path, error in cases:
            with self.subTest(path=path):
                code, result = self.request(path)
                self.assertEqual((code, result["error"]["code"]), (404, error))
        code, result = self.request(f"/api/analyses/{identifier}/chat/messages", question(finding_ids=["foreign"]))
        self.assertEqual((code, result["error"]["code"]), (400, "invalid_request"))

    def test_invalid_payloads_and_source_offset_are_rejected(self):
        identifier = self.analyze()["analysis_id"]
        path = f"/api/analyses/{identifier}/chat/messages"
        for raw in (b"{bad", b"[]", b"null", b"x" * 32769):
            with self.subTest(raw=raw[:20]):
                code, result = self.request(path, raw=raw)
                self.assertEqual((code, result["error"]["code"]), (400, "invalid_request"))
        code, result = self.request(path, question(), headers={"Content-Type": "text/plain"})
        self.assertEqual((code, result["error"]["code"]), (400, "invalid_request"))
        code, result = self.request(f"/api/analyses/{identifier}/source?fragment_id=before:p1&offset=wrong")
        self.assertEqual((code, result["error"]["code"]), (400, "invalid_request"))
        self.runner.assert_not_called()

    def test_rules_analysis_can_be_read_but_chat_requires_model(self):
        identifier = self.analyze()["analysis_id"]
        code, result = self.request(f"/api/analyses/{identifier}/chat/messages", question(config={}))
        self.assertEqual((code, result["error"]["code"]), (422, "model_required"))
        self.assertEqual(self.request(f"/api/analyses/{identifier}/chat")[1]["messages"], [])

    def test_snapshot_write_error_preserves_analysis_and_reports_chat_unavailable(self):
        with patch("ayqyn.chat.snapshots.atomic_json", side_effect=OSError("Disk full")):
            payload = {side: {"name": side + ".docx", "data": base64.b64encode(
                docx(para("Отдел осуществляет мониторинг исполнения программ."))).decode()}
                for side in ("before", "after")}
            code, result = self.request("/api/analyze", payload)
        self.assertEqual(code, 200, result)
        self.assertIsNone(result["analysis_id"])
        self.assertEqual(result["chat"]["reason_code"], "snapshot_failed")
        self.assertEqual(result["mode"], "rules")
        self.assertIn("не сохранён", " ".join(result["warnings"]))


if __name__ == "__main__":
    unittest.main()
