"""Persistent chat jobs, concurrency and failure paths; no provider requests."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from ayqyn.agent.state import atomic_json
from ayqyn.chat.errors import ChatError
from ayqyn.chat.service import ACTIVE, ChatService


LOCAL_CONFIG = {"base": "http://127.0.0.1:9999/v1", "model": "offline-test"}
ANSWER = {"outcome": "answered", "blocks": [{"kind": "explanation", "text": "Проверьте источник.",
           "basis": "analysis", "finding_ids": ["finding-one"]}], "citations": [], "limitations": []}


def result_fixture(finding_id="finding-one", prefix="p"):
    result = {"mode": "rules", "documents": [], "warnings": ["Требуется проверка сотрудником."],
              "findings": [{"id": finding_id, "type": "function_loss", "title": "Проверить функцию",
                            "before_ids": [prefix + "1"], "after_ids": [], "method": "rules",
                            "reviewed": False, "explanation": "Соответствие не установлено."}]}
    for side in ("before", "after"):
        result[side] = {"name": side + ".docx", "sha256": ("a" if side == "before" else "b") * 64,
                        "paragraphs": [{"id": prefix + "1", "text": "Отдел готовит годовой отчёт.",
                                        "section": "1", "block_type": "clause"}]}
    return result


def question(cid="request-one", version=0, **kwargs):
    return {"client_message_id": cid, "expected_version": version,
            "text": "Что изменилось?", "config": dict(LOCAL_CONFIG), **kwargs}


def wait_terminal(service, identifier, turn_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        value = service.turn(identifier, turn_id)
        if value["status"] not in ACTIVE:
            return value
        time.sleep(0.005)
    raise AssertionError("Chat turn did not finish within five seconds")


class ChatServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ, {"OPENAI_API_KEY": "", "OPENAI_MODEL": "", "OPENAI_BASE_URL": ""})
        env.start()
        self.addCleanup(env.stop)
        transport = patch("ayqyn.providers.llm.request_json_api", side_effect=AssertionError("Live API forbidden"))
        self.transport = transport.start()
        self.addCleanup(transport.stop)
        self.addCleanup(self.transport.assert_not_called)
        self.runner = Mock(return_value=deepcopy(ANSWER))
        self.service = ChatService(self.root, runner=self.runner, max_workers=1)
        self.addCleanup(self.service.close)
        self.identifier = self.service.store.save(result_fixture())["analysis_id"]

    def assert_error(self, code, fn, *args):
        with self.assertRaises(ChatError) as raised:
            fn(*args)
        self.assertEqual(raised.exception.code, code)
        return raised.exception

    def blocked_runner(self):
        entered, release = threading.Event(), threading.Event()
        def run(*args, **kwargs):
            args[5]("answering")
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Test gate was not released")
            return deepcopy(ANSWER)
        self.runner.side_effect = run
        self.addCleanup(release.set)
        return entered, release

    def test_read_only_history_snapshot_and_source_work_without_model(self):
        snapshot = self.service.store.public(self.identifier)
        history = self.service.history(self.identifier)
        source = self.service.store.source(self.identifier, "before:p1")
        self.assertEqual(snapshot["analysis_mode"], "rules")
        self.assertEqual(snapshot["chat"]["state"], "requires_model")
        self.assertEqual(history["conversation_version"], 0)
        self.assertEqual(history["messages"], [])
        self.assertEqual(source["fragment"]["text"], "Отдел готовит годовой отчёт.")
        self.assertFalse((self.root / self.identifier / "conversation.json").exists())
        self.runner.assert_not_called()

    def test_async_turn_advances_version_and_records_history(self):
        entered, release = self.blocked_runner()
        code, turn = self.service.submit(self.identifier, question(finding_ids=["finding-one"]))
        self.assertEqual(code, 202)
        self.assertEqual(turn["conversation_version"], 1)
        self.assertTrue(entered.wait(2))
        history = self.service.history(self.identifier)
        self.assertEqual(history["active_turn"]["turn_id"], turn["turn_id"])
        self.assertEqual([m["role"] for m in history["messages"]], ["user"])
        release.set()
        finished = wait_terminal(self.service, self.identifier, turn["turn_id"])
        self.assertEqual(finished["status"], "completed")
        self.assertEqual(finished["conversation_version"], 2)
        self.assertGreaterEqual(finished["elapsed_ms"], 0)
        history = self.service.history(self.identifier)
        self.assertIsNone(history["active_turn"])
        self.assertEqual([m["role"] for m in history["messages"]], ["user", "assistant"])

    def test_concurrent_duplicate_delivery_only_runs_once(self):
        entered, release = self.blocked_runner()
        with ThreadPoolExecutor(max_workers=6) as callers:
            results = list(callers.map(lambda _: self.service.submit(self.identifier, question()), range(6)))
        self.assertTrue(entered.wait(2))
        self.assertEqual(len({turn["turn_id"] for _, turn in results}), 1)
        self.assertTrue(all(code == 202 for code, _ in results))
        self.assertEqual(self.runner.call_count, 1)
        release.set()
        wait_terminal(self.service, self.identifier, results[0][1]["turn_id"])
        code, repeated = self.service.submit(self.identifier, question())
        self.assertEqual(code, 200)
        self.assertEqual(repeated["status"], "completed")
        self.assertEqual(self.runner.call_count, 1)
        self.assertEqual(len(self.service.history(self.identifier)["messages"]), 2)

    def test_reusing_client_id_for_another_question_is_conflict(self):
        _, turn = self.service.submit(self.identifier, question())
        wait_terminal(self.service, self.identifier, turn["turn_id"])
        error = self.assert_error("idempotency_conflict", self.service.submit, self.identifier,
                                  question(text="Другой вопрос"))
        self.assertEqual(error.status, 409)
        self.assertEqual(self.runner.call_count, 1)

    def test_stale_version_and_second_active_turn_are_rejected(self):
        entered, release = self.blocked_runner()
        _, turn = self.service.submit(self.identifier, question())
        self.assertTrue(entered.wait(2))
        error = self.assert_error("turn_in_progress", self.service.submit, self.identifier, question("second", 1))
        self.assertEqual(error.details["active_turn_id"], turn["turn_id"])
        release.set()
        wait_terminal(self.service, self.identifier, turn["turn_id"])
        error = self.assert_error("version_conflict", self.service.submit, self.identifier, question("second", 1))
        self.assertEqual(error.details["conversation_version"], 2)
        _, second = self.service.submit(self.identifier, question("second", 2))
        wait_terminal(self.service, self.identifier, second["turn_id"])
        self.assertEqual(len(self.runner.call_args.args[1]), 2)

    def test_global_capacity_released_after_completion(self):
        other = self.service.store.save(result_fixture("finding-other"))["analysis_id"]
        entered, release = self.blocked_runner()
        _, turn = self.service.submit(self.identifier, question())
        self.assertTrue(entered.wait(2))
        error = self.assert_error("capacity_exceeded", self.service.submit, other, question())
        self.assertEqual(error.status, 429)
        self.assertEqual(self.service.history(other)["conversation_version"], 0)
        release.set()
        wait_terminal(self.service, self.identifier, turn["turn_id"])
        _, second = self.service.submit(other, question())
        self.assertEqual(wait_terminal(self.service, other, second["turn_id"])["status"], "completed")

    def test_foreign_finding_source_and_turn_do_not_cross_analysis(self):
        other = self.service.store.save(result_fixture("foreign-finding", "other"))["analysis_id"]
        self.assert_error("invalid_request", self.service.submit, self.identifier,
                          question(finding_ids=["foreign-finding"]))
        self.assert_error("source_not_found", self.service.store.source, self.identifier, "before:other1")
        _, turn = self.service.submit(other, question())
        wait_terminal(self.service, other, turn["turn_id"])
        self.assert_error("turn_not_found", self.service.turn, self.identifier, turn["turn_id"])

    def test_missing_model_does_not_create_message(self):
        self.assert_error("model_required", self.service.submit, self.identifier, question(config={}))
        self.assertEqual(self.service.history(self.identifier)["messages"], [])
        self.runner.assert_not_called()

    def test_invalid_requests_do_not_advance_history(self):
        bad = [None, [], question(expected_version=True), question(text=" "), question(text="x" * 4001),
               question(client_message_id="../unsafe"), question(finding_ids=["finding-one"] * 2),
               question(config={"unknown": "option"}), question(config={"embedding_dimensions": True}),
               question(config={"reasoning_effort": "unbounded"}), question(unexpected=True)]
        for value in bad:
            with self.subTest(value=value):
                self.assert_error("invalid_request", self.service.submit, self.identifier, value)
        self.assertEqual(self.service.history(self.identifier)["conversation_version"], 0)
        self.runner.assert_not_called()

    def test_provider_error_is_terminal_and_never_exposes_secret(self):
        secret = "private-test-token-123"
        self.runner.side_effect = ChatError("provider_error", "Провайдер недоступен.", 502, retryable=True)
        payload = question(config={**LOCAL_CONFIG, "key": secret}, text="Не показывай " + secret)
        _, turn = self.service.submit(self.identifier, payload)
        final = wait_terminal(self.service, self.identifier, turn["turn_id"])
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["error"]["code"], "provider_error")
        self.assertTrue(final["error"]["retryable"])
        self.assertIsNone(final["assistant_message"])
        self.assertNotIn(secret, json.dumps(self.service.history(self.identifier)))
        for path in self.root.rglob("*.json"):
            self.assertNotIn(secret, path.read_text(encoding="utf-8"))

    def test_unexpected_provider_exception_does_not_leak_exception_body(self):
        self.runner.side_effect = RuntimeError("Authorization: Bearer do-not-expose")
        _, turn = self.service.submit(self.identifier, question())
        final = wait_terminal(self.service, self.identifier, turn["turn_id"])
        self.assertEqual(final["error"]["code"], "internal_error")
        self.assertNotIn("do-not-expose", json.dumps(final))
        self.assertIsNone(self.service.history(self.identifier)["active_turn"])

    def test_provider_error_redacts_json_escaped_key_from_public_and_disk(self):
        secret = 'private-test-"quoted"-key\\tail'
        self.runner.side_effect = ChatError("provider_error", "Provider echoed " + secret, 502, retryable=True)
        _, turn = self.service.submit(self.identifier, question(config={**LOCAL_CONFIG, "key": secret}))
        final = wait_terminal(self.service, self.identifier, turn["turn_id"])
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["error"]["message"], "Provider echoed [REDACTED]")
        encoded_secret = json.dumps(secret)[1:-1]
        history = self.service.history(self.identifier)
        self.assertEqual(history["messages"][-1]["error"]["message"], "Provider echoed [REDACTED]")
        for public in (final, history):
            self.assertNotIn(encoded_secret, json.dumps(public))
        for path in self.root.rglob("*.json"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(secret, text)
            self.assertNotIn(encoded_secret, text)

    def test_executor_rejection_and_terminal_write_error_release_global_capacity(self):
        other = self.service.store.save(result_fixture("other-finding"))["analysis_id"]
        writes = []
        def fail_terminal_write(*args, **kwargs):
            writes.append(args)
            if len(writes) == 2:
                raise OSError("Disk full while saving executor failure")
            return atomic_json(*args, **kwargs)
        with patch.object(self.service.pool, "submit", side_effect=RuntimeError("Executor stopped")), \
                patch("ayqyn.chat.service.atomic_json", side_effect=fail_terminal_write):
            self.assert_error("storage_error", self.service.submit, self.identifier, question())
        self.assertEqual(len(writes), 2)
        self.runner.assert_not_called()
        code, turn = self.service.submit(other, question())
        self.assertEqual(code, 202)
        self.assertEqual(wait_terminal(self.service, other, turn["turn_id"])["status"], "completed")

    def test_restart_marks_unfinished_job_interrupted_without_replay(self):
        _, turn = self.service.submit(self.identifier, question())
        wait_terminal(self.service, self.identifier, turn["turn_id"])
        self.service.close()
        path = self.root / self.identifier / "conversation.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        saved_turn = state["turns"][turn["turn_id"]]
        saved_turn.update(status="answering", finished_at=None, assistant_message=None)
        state.update(active_turn=turn["turn_id"], conversation_version=1)
        state["messages"] = state["messages"][:1]
        path.write_text(json.dumps(state), encoding="utf-8")
        replay = Mock(side_effect=AssertionError("Restart must not replay provider requests"))
        restored = ChatService(self.root, runner=replay)
        self.addCleanup(restored.close)
        final = restored.turn(self.identifier, turn["turn_id"])
        self.assertEqual(final["status"], "interrupted")
        self.assertEqual(final["error"]["code"], "interrupted")
        self.assertEqual(final["conversation_version"], 2)
        self.assertIsNone(restored.history(self.identifier)["active_turn"])
        self.assertEqual(len(restored.history(self.identifier)["messages"]), 2)
        replay.assert_not_called()

    def test_initial_storage_failure_rejects_and_releases_capacity(self):
        with patch("ayqyn.chat.service.atomic_json", side_effect=OSError("Disk full")):
            self.assert_error("storage_error", self.service.submit, self.identifier, question())
        self.runner.assert_not_called()
        self.assertEqual(self.service.history(self.identifier)["messages"], [])
        _, turn = self.service.submit(self.identifier, question())
        self.assertEqual(wait_terminal(self.service, self.identifier, turn["turn_id"])["status"], "completed")

    def test_final_storage_failure_stops_polling_and_retains_recoverable_failure(self):
        entered, release = self.blocked_runner()
        _, turn = self.service.submit(self.identifier, question())
        self.assertTrue(entered.wait(2))
        with patch("ayqyn.chat.service.atomic_json", side_effect=OSError("Disk full")):
            release.set()
            final = wait_terminal(self.service, self.identifier, turn["turn_id"])
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["error"]["code"], "storage_error")
        self.assertIsNone(final["assistant_message"])
        self.assertIsNone(self.service.history(self.identifier)["active_turn"])
        _, retry = self.service.submit(self.identifier, question("retry", final["conversation_version"]))
        self.assertEqual(wait_terminal(self.service, self.identifier, retry["turn_id"])["status"], "completed")

    def test_corrupt_history_is_not_silently_reset(self):
        path = self.root / self.identifier / "conversation.json"
        path.write_text("{broken json", encoding="utf-8")
        self.assert_error("storage_error", self.service.history, self.identifier)
        self.assert_error("storage_error", self.service.submit, self.identifier, question())
        self.assertEqual(path.read_text(encoding="utf-8"), "{broken json")
        self.runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
