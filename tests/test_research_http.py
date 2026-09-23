"""Research HTTP contracts using synthetic DOCX, a mock index, and mock turns.

Regression assertions intentionally describe the required behavior, including
failures found by this review. No provider transport or real credentials are used.
"""
import copy
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ayqyn.agent import runner as research_agent
from ayqyn.agent.state import ResearchState
from ayqyn.api import server as server
from test_packets import upload


class MockIndex:
    def __init__(self, store, path, config, embedder=None):
        self.store = store
        self.config = config
        self.metadata = {"ready": False, "embedding_backend": "mock"}
        self.build = Mock(side_effect=self._build)
        self.search = Mock(side_effect=store.search_fragments)

    def _build(self):
        self.metadata["ready"] = True


def tool_turn(name, arguments, call_id="call-1"):
    return {
        "role": "assistant", "content": None,
        "tool_calls": [{"id": call_id, "type": "function", "function": {
            "name": name, "arguments": json.dumps(arguments),
        }}],
    }, {"total_tokens": 1}


def partial_result():
    return {
        "findings": [], "outcome": "insufficient_data",
        "gaps": ["The remaining sources require review."],
        "reason": "Only a partial review was performed.",
    }


class ResearchHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.http.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.indexes = []
        self.start_patch("ayqyn.api.server.RESEARCH_ROOT", self.root / "output" / "research")
        self.start_patch("ayqyn.agent.runner.ROOT", self.root)
        self.start_patch("ayqyn.api.server.ACTIVE_RESEARCH", set())
        self.start_patch("ayqyn.agent.runner.os.getenv", return_value="")
        self.start_patch("ayqyn.retrieval.hybrid.HybridIndex", side_effect=self.make_index)
        self.transport = self.start_patch(
            "ayqyn.providers.llm.request_json_api",
            side_effect=AssertionError("Provider transport is forbidden in this suite."),
        )
        self.driver = self.start_patch(
            "ayqyn.agent.runner.agent_turn",
            return_value=tool_turn("submit_findings", partial_result()),
        )

    def tearDown(self):
        self.transport.assert_not_called()

    def start_patch(self, target, *args, **kwargs):
        patcher = patch(target, *args, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def make_index(self, *args, **kwargs):
        index = MockIndex(*args, **kwargs)
        self.indexes.append(index)
        return index

    def request(self, path, payload=None, *, headers=None, method=None, raw=None):
        body = raw if raw is not None else (
            json.dumps(payload).encode() if payload is not None else None
        )
        request_headers = {"Content-Type": "application/json"} if body is not None else {}
        request_headers.update(headers or {})
        request = Request(self.base + path, data=body, headers=request_headers, method=method)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, json.load(response)

    def payload(self, **changes):
        return {
            "documents": [
                upload(["1. Previous duties", "2. Team Alpha reviews supplier contracts."],
                       name="before.docx", role="before"),
                upload(["1. Current duties", "2. Team Beta reviews supplier contracts."],
                       name="after.docx", role="after"),
            ],
            "mode": "manual", "task": "Compare responsibility for contract review.",
            "config": {}, **changes,
        }

    def prepare(self, **changes):
        code, result = self.request("/api/research/prepare", self.payload(**changes))
        self.assertEqual(code, 200)
        self.assertEqual(result["status"], "ready")
        return result["id"]

    def run_id(self, identifier, **changes):
        return self.request("/api/research/run", {"id": identifier, "config": {}, **changes})

    def load_state(self, identifier):
        return ResearchState(self.root / "output" / "research" / identifier)

    def fragments(self, identifier):
        packet = self.load_state(identifier).packet
        return [next(p for p in packet[side]["paragraphs"] if "reviews" in p["text"])
                for side in ("before", "after")]

    def finding(self, identifier):
        old, new = self.fragments(identifier)
        return {
            "group": "function", "category": "changed",
            "function": "Review supplier contracts",
            "owner_before": "Team Alpha", "owner_after": "Team Beta",
            "before_evidence": [{"fragment_id": old["id"], "quote": old["text"]}],
            "after_evidence": [{"fragment_id": new["id"], "quote": new["text"]}],
            "explanation": "The assigned team changed.",
            "comparison": {
                "before": {"action":"reviews","object":"supplier contracts","conditions":None,"stage":None},
                "after": {"action":"reviews","object":"supplier contracts","conditions":None,"stage":None},
                "changed_fields": ["owner"],
            },
            "limitations": ["The text does not establish actual execution."],
            "claim_checks": [
                {"kind":"prior_assignment","evidence":[{"fragment_id":old["id"],"quote":old["text"]}],"result":"The supplied before clause assigns Alpha, not Beta; this does not prove exclusivity."},
                {"kind":"retained_assignment","evidence":[{"fragment_id":new["id"],"quote":new["text"]}],"result":"The supplied after clause assigns Beta; this does not prove organizational completeness."},
            ],
        }

    def script(self, actions):
        self.driver.side_effect = [tool_turn(name, arguments, f"call-{n}")
                                   for n, (name, arguments) in enumerate(actions, 1)]

    def read_actions(self, identifier):
        return [("read_context", {"fragment_id": p["id"], "scope": "document"})
                for p in self.fragments(identifier)]

    def test_prepare_run_get_persist_verified_quotes_and_budget(self):
        identifier = self.prepare()
        self.driver.assert_not_called()
        self.script(self.read_actions(identifier) + [("submit_findings", {
            "findings": [self.finding(identifier)], "outcome": "insufficient_data",
            "gaps": ["Other source candidates were not assessed."], "reason": "Both documents were read, not all functions verified.",
        })])
        code, result = self.run_id(identifier)
        self.assertEqual((code, result["status"]), (200, "insufficient_data"))
        self.assertEqual(result["budget"]["model_calls_used"], 3)
        self.assertEqual(result["budget"]["tool_calls_used"], 3)
        self.assertEqual(result["findings"][0]["evidence_validation"], "exact_quotes_verified")
        self.assertEqual(result["findings"][0]["human_review"]["status"], "unreviewed")
        self.assertEqual(self.request("/api/research/" + identifier), (200, result))
        self.assertTrue(self.load_state(identifier).data["read_ids"])
        self.assertTrue({"messages", "pending_call", "packet", "config"}.isdisjoint(result))

    def test_workspace_and_progress_project_same_run_without_calling_model(self):
        identifier=self.prepare()
        self.script(self.read_actions(identifier)+[("submit_findings",{
            "findings":[self.finding(identifier)],"outcome":"insufficient_data",
            "gaps":["Other candidates are unverified."],"reason":"Partial comparison."})])
        self.run_id(identifier)
        calls=self.driver.call_count
        code,workspace=self.request('/api/research/'+identifier+'?view=workspace')
        self.assertEqual(code,200)
        self.assertTrue(workspace['saved'])
        self.assertEqual(workspace['mode'],'agent')
        self.assertEqual(workspace['findings'][0]['owner_before'],'Team Alpha')
        self.assertEqual(workspace['findings'][0]['type'],'function_changed')
        self.assertFalse(workspace['findings'][0]['reviewed'])
        for side in ['before','after']:
            sources={p['id']:p for p in workspace[side]['paragraphs']}
            for evidence in workspace['findings'][0][side+'_evidence']:
                self.assertIn(evidence['quote'],sources[evidence['fragment_id']]['text'])
        code,progress=self.request('/api/research/'+identifier+'?view=progress')
        self.assertEqual(code,200)
        self.assertEqual(len(progress['actions']),3)
        self.assertEqual(progress['inventory']['pending_count'],len(self.load_state(identifier).data['candidates']))
        self.assertGreater(progress['inventory']['pending_count'],0)
        self.assertTrue({'messages','packet','config','journal'}.isdisjoint(progress))
        self.assertEqual(calls,self.driver.call_count)

    def test_classify_only_never_runs_old_analysis(self):
        with patch('ayqyn.api.server.compare_with_model') as model,patch('ayqyn.api.server.analyze_rules') as rules:
            documents=[{**value,'side':value['role']} for value in self.payload()['documents']]
            code,result=self.request('/api/analyze',{'documents':documents,'useAI':False,'classifyOnly':True})
            self.assertEqual(code,200)
            self.assertFalse(result['needs_review'])
            self.assertEqual([d['side'] for d in result['documents']],['before','after'])
            model.assert_not_called();rules.assert_not_called()

    def test_bad_quotes_are_rejected_and_repair_uses_read_sources(self):
        for defect in ("unread", "invented_quote", "foreign_fragment", "wrong_side"):
            with self.subTest(defect=defect):
                identifier = self.prepare()
                finding = self.finding(identifier)
                broken = copy.deepcopy(finding)
                reads = self.read_actions(identifier)
                if defect == "invented_quote":
                    broken["after_evidence"][0]["quote"] = "Team Beta approves every payment."
                elif defect == "foreign_fragment":
                    broken["after_evidence"][0]["fragment_id"] = "not-in-this-packet:p1"
                elif defect == "wrong_side":
                    broken["after_evidence"] = copy.deepcopy(broken["before_evidence"])
                    broken["owner_after"] = "Team Alpha"
                bad_submit = ("submit_findings", {
                    "findings": [broken], "outcome": "insufficient_data",
                    "gaps": ["Review in progress."], "reason": "Attempt a finding.",
                })
                actions = [bad_submit] + reads if defect == "unread" else reads + [bad_submit]
                self.script(actions + [("submit_findings", {
                    "findings": [finding], "outcome": "insufficient_data", "gaps": ["Other source candidates were not assessed."],
                    "reason": "Both sources were read and the evidence was corrected.",
                })])
                code, result = self.run_id(identifier)
                self.assertEqual((code, result["status"]), (200, "insufficient_data"))
                submissions = [e["result"] for e in result["journal"]
                               if e.get("tool") == "submit_findings"]
                self.assertEqual([r["accepted"] for r in submissions], [False, True])
                self.assertTrue(submissions[0]["errors"])
                self.assertEqual(result["findings"][0]["after_evidence"], finding["after_evidence"])

    def test_supported_hypothesis_with_open_gaps_prevents_completion(self):
        identifier = self.prepare()
        hypothesis = {
            "hypothesis_id": "h1", "claim": "The review responsibility moved.",
            "assessment": "supported", "supporting": self.finding(identifier)["after_evidence"],
            "contradicting": [], "gaps": ["A referenced annex is missing from the packet."],
            "revision_reason": "The after document supports the assignment but references an annex.",
        }
        self.script(self.read_actions(identifier) + [
            ("update_research_state", hypothesis),
            ("submit_findings", {"findings": [], "outcome": "completed", "gaps": [],
                                 "reason": "Read all supplied documents."}),
            ("submit_findings", partial_result()),
        ])
        code, result = self.run_id(identifier)
        self.assertEqual(code, 200)
        self.assertEqual(result["status"], "insufficient_data")

    def test_model_and_tool_call_caps_stop_before_another_turn(self):
        for field in ("max_model_calls", "max_tool_calls"):
            with self.subTest(field=field):
                identifier = self.prepare(budget={field: 1})
                self.driver.reset_mock(side_effect=True)
                self.driver.return_value = tool_turn("list_documents", {})
                code, result = self.run_id(identifier)
                self.assertEqual((code, result["status"]), (200, "budget_exhausted"))
                self.assertEqual(self.driver.call_count, 1)
                self.assertEqual(result["budget"]["model_calls_used"], 1)
                self.assertEqual(result["budget"]["tool_calls_used"], 1)

    def test_late_model_response_does_not_execute_tool(self):
        identifier = self.prepare(budget={"max_seconds": 1})
        clock = Mock(return_value=0)

        def late(*args, **kwargs):
            self.assertLessEqual(kwargs["timeout_seconds"], 1)
            clock.return_value = 2
            return tool_turn("submit_findings", partial_result())

        self.driver.side_effect = late
        self.start_patch("ayqyn.api.server.run_research", side_effect=lambda *a, **k:
                         research_agent.run_research(*a, **k, clock=clock))
        code, result = self.run_id(identifier)
        self.assertEqual((code, result["status"]), (200, "budget_exhausted"))
        self.assertEqual(result["budget"]["tool_calls_used"], 0)
        self.assertFalse(any(e["kind"] == "tool_executed" for e in result["journal"]))

    def test_terminal_run_does_not_restore_or_rebuild_index(self):
        identifier = self.prepare()
        self.assertEqual(self.run_id(identifier)[1]["status"], "insufficient_data")
        self.driver.reset_mock()
        index_count = len(self.indexes)
        code, result = self.run_id(identifier, config={"embedding_model": "another-model"})
        self.assertEqual((code, result["status"]), (200, "insufficient_data"))
        self.driver.assert_not_called()
        self.assertEqual(len(self.indexes), index_count,
                         "A terminal result must not rebuild embeddings before its terminal check.")

    def test_exhausted_resume_checks_budget_before_index_work(self):
        identifier = self.prepare()
        state = self.load_state(identifier)
        state.data["status"] = "interrupted"
        state.data["budget"]["elapsed_seconds"] = state.data["budget"]["max_seconds"]
        state.save()
        index_count = len(self.indexes)
        code, result = self.run_id(identifier)
        self.assertEqual((code, result["status"]), (200, "budget_exhausted"))
        self.driver.assert_not_called()
        self.assertEqual(len(self.indexes), index_count,
                         "An exhausted resume must not perform new embedding work.")

    def test_model_error_stops_cleanly_without_tool_or_active_lock(self):
        identifier = self.prepare()
        self.driver.side_effect = ValueError("Mock provider unavailable.")
        code, result = self.run_id(identifier)
        self.assertEqual((code, result["status"]), (200, "model_error"))
        self.assertEqual(result["budget"]["tool_calls_used"], 0)
        self.assertNotIn(identifier, server.ACTIVE_RESEARCH)
        self.assertEqual(self.request("/api/research/" + identifier)[1]["status"], "model_error")

    def test_interrupted_tool_resumes_with_balanced_messages_and_spent_budget(self):
        identifier = self.prepare()
        factory = self.make_index

        def interrupting_index(*args, **kwargs):
            index = factory(*args, **kwargs)
            index.search.side_effect = OSError("Simulated tool interruption.")
            return index

        self.start_patch("ayqyn.retrieval.hybrid.HybridIndex", side_effect=interrupting_index)
        self.driver.return_value = tool_turn("search", {
            "query": "contracts", "role": "after", "document_id": None, "limit": 2,
        })
        code, first = self.run_id(identifier)
        self.assertEqual((code, first["status"]), (200, "interrupted"))
        self.assertIsNotNone(self.load_state(identifier).data["pending_call"])
        self.assertNotIn(identifier, server.ACTIVE_RESEARCH)

        def resumed(messages, *args, **kwargs):
            replies = [m for m in messages if m["role"] == "tool"]
            self.assertEqual(len(replies), 1)
            self.assertEqual(replies[0]["tool_call_id"], "call-1")
            self.assertIn("error", json.loads(replies[0]["content"]))
            return tool_turn("submit_findings", partial_result(), "call-2")

        self.driver.side_effect = resumed
        code, result = self.run_id(identifier)
        self.assertEqual((code, result["status"]), (200, "insufficient_data"))
        self.assertEqual(result["budget"]["model_calls_used"], 2)
        self.assertEqual(result["budget"]["tool_calls_used"], 2)
        self.assertIsNone(self.load_state(identifier).data["pending_call"])
        self.assertEqual(sum(e["kind"] == "tool_interrupted" for e in result["journal"]), 1)

    def test_prepare_index_failure_is_explicit_and_does_not_call_model(self):
        with patch.object(MockIndex, "_build", side_effect=ValueError("Mock index unavailable.")):
            code, result = self.request("/api/research/prepare", self.payload())
        self.assertEqual((code, result["status"]), (200, "index_error"))
        self.driver.assert_not_called()
        self.assertEqual(self.request("/api/research/" + result["id"])[1]["status"], "index_error")

    def test_interrupted_model_preserves_read_evidence_on_resume(self):
        identifier = self.prepare()
        self.script(self.read_actions(identifier))
        self.driver.side_effect = list(self.driver.side_effect) + [OSError("Simulated interruption.")]
        code, result = self.run_id(identifier)
        self.assertEqual((code, result["status"]), (200, "interrupted"))
        self.assertEqual(result["budget"]["model_calls_used"], 3)
        self.assertEqual(result["budget"]["tool_calls_used"], 2)
        self.assertTrue(self.load_state(identifier).data["read_ids"])
        self.driver.side_effect = None
        self.driver.return_value = tool_turn("submit_findings", {
            "findings": [self.finding(identifier)], "outcome": "insufficient_data",
            "gaps": ["Other source candidates were not assessed."], "reason": "Previously read evidence survives resume.",
        }, "call-4")
        code, result = self.run_id(identifier)
        self.assertEqual((code, result["status"]), (200, "insufficient_data"))
        self.assertEqual(result["budget"]["model_calls_used"], 4)
        self.assertEqual(result["budget"]["tool_calls_used"], 3)
        self.assertEqual(result["validation_errors"], [])

    def test_clarification_is_saved_and_stops_further_turns(self):
        identifier = self.prepare()
        document_id = self.load_state(identifier).packet["documents"][0]["id"]
        question = "Which version does the referenced annex belong to?"
        self.driver.return_value = tool_turn("request_clarification", {
            "question": question, "document_ids": [document_id],
        })
        code, result = self.run_id(identifier)
        self.assertEqual((code, result["status"]), (200, "needs_clarification"))
        self.assertEqual(self.driver.call_count, 1)
        self.assertEqual(result["gaps"], [question])
        self.assertFalse(result["findings"])
        self.assertEqual(self.request("/api/research/" + identifier)[1], result)

    def test_restore_index_failure_is_persisted_for_polling(self):
        identifier = self.prepare()
        with patch.object(MockIndex, "_build", side_effect=ValueError("Mock cache failure.")):
            self.run_id(identifier)
        self.driver.assert_not_called()
        self.assertNotIn(identifier, server.ACTIVE_RESEARCH)
        self.assertEqual(self.request("/api/research/" + identifier)[1]["status"], "index_error")

    def test_duplicate_run_is_rejected_while_polling_remains_available(self):
        identifier = self.prepare()
        entered, release = threading.Event(), threading.Event()

        def blocked(*args, **kwargs):
            entered.set()
            if not release.wait(timeout=3):
                raise ValueError("Mock request was not released.")
            return tool_turn("submit_findings", partial_result())

        self.driver.side_effect = blocked
        with ThreadPoolExecutor(max_workers=1) as pool:
            running = pool.submit(self.run_id, identifier)
            try:
                self.assertTrue(entered.wait(timeout=2))
                self.assertEqual(self.run_id(identifier)[0], 409)
                self.assertEqual(self.request("/api/research/" + identifier)[1]["status"], "running")
            finally:
                release.set()
            self.assertEqual(running.result(timeout=5)[1]["status"], "insufficient_data")
        self.assertNotIn(identifier, server.ACTIVE_RESEARCH)

    def test_tool_allowlist_and_argument_shape_errors_can_be_repaired(self):
        identifier = self.prepare()
        self.script([
            ("shell", {"command": "not executed"}),
            ("list_documents", {"extra": "forbidden"}),
            ("search", {"query": "contracts", "role": "after", "document_id": None, "limit": True}),
            ("submit_findings", partial_result()),
        ])
        code, result = self.run_id(identifier)
        self.assertEqual((code, result["status"]), (200, "insufficient_data"))
        events = [e for e in result["journal"] if e["kind"] == "tool_executed"]
        self.assertEqual([e["result"]["accepted"] for e in events], [False, False, False, True])
        self.assertEqual(result["budget"]["tool_calls_used"], 4)
        self.indexes[-1].search.assert_not_called()

    def test_host_origin_content_type_and_body_limit_guards(self):
        for path in ("/api/research/prepare", "/api/research/run"):
            limit = 56_000_000 if path.endswith("prepare") else 29_000_000
            for headers, expected in (
                ({"Host": "untrusted.invalid"}, 403),
                ({"Origin": "https://untrusted.invalid"}, 403),
                ({"Content-Type": "text/plain"}, 400),
                ({"Content-Length": str(limit + 1)}, 400),
            ):
                with self.subTest(path=path, headers=tuple(headers)):
                    # Header guards reject before body consumption. Sending a body in a
                    # second TCP write can race the early close on Windows.
                    self.assertEqual(self.request(path, raw=b"", headers=headers)[0], expected)
        self.assertEqual(self.request("/api/research/r-" + "0" * 32,
                                      headers={"Host": "untrusted.invalid"})[0], 403)
        self.driver.assert_not_called()
        self.assertFalse(self.indexes)

    def test_invalid_ids_and_private_research_paths_are_not_accessible(self):
        for identifier in ("../outside", "r-" + "0" * 31, "r-" + "G" * 32, 12, None):
            with self.subTest(identifier=identifier):
                self.assertEqual(self.run_id(identifier)[0], 400)
        identifier = self.prepare()
        for path in (f"/api/research/{identifier}/state.json",
                     f"/api/research/{identifier}%2F..%2Fpacket.json",
                     f"/output/research/{identifier}/state.json"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        self.driver.assert_not_called()

    def test_missing_valid_id_is_not_an_internal_server_error(self):
        identifier = "r-" + "0" * 32
        self.assertEqual(self.request("/api/research/" + identifier)[0], 404)
        self.assertEqual(self.run_id(identifier)[0], 404)
        self.assertNotIn(identifier, server.ACTIVE_RESEARCH)

    def test_invalid_budget_numbers_and_unknown_fields_are_rejected(self):
        for budget in ({"max_tool_calls": True}, {"max_tool_calls": 0},
                       {"max_model_calls": 65}, {"max_seconds": 601},
                       {"max_seconds": 1.5}, {"unknown": 2}):
            with self.subTest(budget=budget):
                self.assertEqual(self.request("/api/research/prepare", self.payload(budget=budget))[0], 400)
        self.assertFalse(self.indexes)
        self.driver.assert_not_called()

    def test_non_object_budget_is_a_client_error(self):
        for budget in (1, "invalid", [1], [], False):
            with self.subTest(budget_type=type(budget).__name__):
                self.assertEqual(self.request("/api/research/prepare", self.payload(budget=budget))[0], 400)

    def test_invalid_task_json_and_config_are_client_errors(self):
        for changes in ({"task": None}, {"task": " "}, {"task": "x" * 12001},
                        {"config": ["invalid"]}):
            with self.subTest(fields=tuple(changes)):
                self.assertEqual(self.request("/api/research/prepare", self.payload(**changes))[0], 400)
        for raw in (b"[]", b"null", b"{"):
            self.assertEqual(self.request("/api/research/run", raw=raw)[0], 400)
        self.assertFalse(self.indexes)
        self.driver.assert_not_called()


if __name__ == "__main__":
    unittest.main()
