"""Offline chat contract checks; scripted providers are not an LLM quality score."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from ayqyn.analysis.batch import classify_documents, combine_documents
from ayqyn.agent.state import ResearchState
from ayqyn.chat import agent
from ayqyn.chat.errors import ChatError
from ayqyn.chat.snapshots import AnalysisStore, legacy_packet
from ayqyn.chat.tools import ChatTools
from ayqyn.documents.store import DocumentStore
from test_analyzer import document


OLD = "2.1. Отдел закупок контролирует исполнение договоров с поставщиками."
NEW = "2.1. Сектор сопровождения контролирует исполнение договоров с поставщиками."


def legacy_result(batch=False):
    before = document("1. Положение о закупках", OLD, "3. Заключительные положения")
    after = document("1. Положение о сопровождении", NEW, "3. Заключительные положения")
    before["name"], after["name"] = "before.docx", "after.docx"
    documents = classify_documents([before, after], [{"side": "before"}, {"side": "after"}]) if batch else []
    if batch:
        before = combine_documents(documents, "before")
        after = combine_documents(documents, "after")
    return {"before": before, "after": after, "mode": "rules", "warnings": ["Нужна проверка аналитика."],
            "findings": [{"id": "f1", "type": "function_loss", "title": "Возможная потеря контроля",
                          "before_ids": [before["paragraphs"][1]["id"]], "after_ids": []}],
            **({"documents": documents} if batch else {})}


def snapshot():
    result = legacy_result()
    packet, findings = legacy_packet(result)
    return {"analysis_mode": result["mode"], "synthetic": False, "limitations": result["warnings"],
            "packet": packet, "findings": findings, "result": deepcopy(result)}


def answer(fragment="after:p2", quote=NEW, **changes):
    value = {"outcome": "answered", "blocks": [{"kind": "claim", "basis": "source",
             "text": "Контроль закреплён за сектором сопровождения.", "citation_ids": ["c1"], "finding_ids": []}],
             "citations": [{"id": "c1", "fragment_id": fragment, "quote": quote}],
             "analysis_relation": "challenges", "claims_absence": False,
             "limitations": ["Фактическое исполнение не проверено."]}
    value.update(changes)
    return value


def clarification():
    return {"outcome": "needs_clarification", "blocks": [{"kind": "question", "basis": "conversation",
            "text": "Какую из функций вы имеете в виду?", "citation_ids": [], "finding_ids": []}],
            "citations": [], "analysis_relation": "not_determined", "claims_absence": False, "limitations": []}


def read_call(fragment="after:p2", scope="section"):
    return "read_context", {"fragment_id": fragment, "scope": scope, "offset": 0}


class ScriptedProvider:
    def __init__(self, *steps):
        self.steps, self.calls = list(steps), []

    def __call__(self, messages, schemas, config, before, after, **kwargs):
        self.calls.append({"messages": deepcopy(messages), "schemas": deepcopy(schemas), **kwargs})
        if not self.steps:
            raise AssertionError("Unexpected model call; fake provider script exhausted")
        name, arguments = self.steps.pop(0)
        return {"role": "assistant", "content": None, "tool_calls": [{"id": "call-" + str(len(self.calls)),
                "type": "function", "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}}]}, {"total_tokens": 5}


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = AnalysisStore(Path(self.temp.name))

    def test_pair_ids_and_all_structural_links_are_namespaced_without_mutation(self):
        result = legacy_result()
        for doc in [result["before"], result["after"]]:
            doc["paragraphs"][1].update(parent_id="p1", previous_id="p1", next_id="p3", heading_id="p1",
                                        table_id="t1", row_id="t1:r1", row_fragment_ids=["p2"],
                                        header_row_ids=["t1:r0"], header_fragment_ids=["p1"], first_row_fragment_ids=["p1"])
        original = deepcopy(result)
        packet, findings = legacy_packet(result)
        self.assertEqual(result, original)
        self.assertEqual(findings[0]["before_ids"], ["before:p2"])
        self.assertEqual(len({p["id"] for d in packet["documents"] for p in d["paragraphs"]}), 6)
        for doc in packet["documents"]:
            side, p = doc["role"], doc["paragraphs"][1]
            self.assertEqual(p["parent_id"], side + ":p1")
            self.assertEqual(p["previous_id"], side + ":p1")
            self.assertEqual(p["next_id"], side + ":p3")
            self.assertEqual(p["heading_id"], side + ":p1")
            self.assertEqual(p["table_id"], side + ":t1")
            self.assertEqual(p["row_id"], side + ":t1:r1")
            self.assertEqual(p["row_fragment_ids"], [side + ":p2"])
            self.assertEqual(p["header_row_ids"], [side + ":t1:r0"])
            self.assertEqual(p["header_fragment_ids"], [side + ":p1"])
            self.assertEqual(p["first_row_fragment_ids"], [side + ":p1"])
            self.assertEqual(p["source_locator"], {"side": side, "original_fragment_id": "p2"})

    def test_batch_keeps_global_ids_and_rewrites_local_links(self):
        result = legacy_result(batch=True)
        for doc in result["documents"]:
            doc["paragraphs"][1].update(parent_id="p1", previous_id="p1", next_id="p3", row_fragment_ids=["p2"])
        original = deepcopy(result)
        packet, findings = legacy_packet(result)
        self.assertEqual(result, original)
        self.assertEqual(findings[0]["before_ids"], ["d1:p2"])
        for doc in packet["documents"]:
            p = doc["paragraphs"][1]
            self.assertEqual(p["id"], doc["id"] + ":p2")
            self.assertEqual(p["parent_id"], doc["id"] + ":p1")
            self.assertEqual(p["next_id"], doc["id"] + ":p3")
            self.assertEqual(p["row_fragment_ids"], [doc["id"] + ":p2"])

    def test_saved_research_snapshot_is_stable_immutable_and_content_addressed(self):
        result = legacy_result()
        packet, _ = legacy_packet(result)
        original_result, original_packet = deepcopy(result), deepcopy(packet)
        first = self.store.save(result, packet=packet, research_id="r-" + "1" * 32)
        second = self.store.save(result, packet=packet, research_id="r-" + "1" * 32)
        self.assertEqual(first, second)
        self.assertEqual(first, self.store.load(first["analysis_id"]))
        self.assertEqual(result, original_result)
        self.assertEqual(packet, original_packet)
        result["findings"][0]["title"] = "Исправленный вывод"
        changed = self.store.save(result, packet=packet, research_id="r-" + "1" * 32)
        self.assertNotEqual(first["analysis_id"], changed["analysis_id"])
        self.assertEqual(self.store.load(first["analysis_id"])["result"], original_result)

    def test_completed_research_adapter_is_stable_and_unfinished_research_is_unavailable(self):
        packet = snapshot()["packet"]
        state = ResearchState(Path(self.temp.name) / ("r-" + "2" * 32), packet, "Проверить контроль договоров",
                              {"max_calls": 6, "max_seconds": 60})
        for status in ["preparing", "running", "budget_exhausted", "model_error", "interrupted"]:
            state.data["status"] = status
            public = self.store.from_research(state)
            self.assertIsNone(public["analysis_id"])
            self.assertEqual(public["chat"]["reason_code"], "research_not_finished")
        state.data["status"] = "completed"
        before = deepcopy(state.data), deepcopy(state.packet)
        with patch("ayqyn.chat.snapshots.capability", return_value={"state": "available"}):
            first = self.store.from_research(state)
            second = self.store.from_research(state)
        self.assertEqual(first, second)
        saved = self.store.load(first["analysis_id"])
        self.assertEqual(saved["analysis_mode"], "agent")
        self.assertEqual(saved["research_id"], state.data["id"])
        self.assertEqual((state.data, state.packet), before)

    def test_corrupted_snapshot_fails_closed(self):
        saved = self.store.save(legacy_result())
        path = self.store.path(saved["analysis_id"]) / "snapshot.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["findings"][0]["title"] = "Подмена"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ChatError) as caught:
            self.store.load(saved["analysis_id"])
        self.assertEqual(caught.exception.code, "storage_error")

    def test_snapshot_redacts_json_escaped_secret(self):
        secret = 'fake-key-"slash\\end'
        result = legacy_result()
        result["warnings"].append(secret)
        saved = self.store.save(result, secrets=(secret,))
        self.assertNotIn(secret, json.dumps(saved, ensure_ascii=False))
        self.assertEqual(saved["result"]["warnings"][-1], "[REDACTED]")
        self.assertEqual(saved, self.store.load(saved["analysis_id"]))

    def test_source_resolves_only_current_analysis_and_preserves_original_locator(self):
        saved = self.store.save(legacy_result())
        source = self.store.source(saved["analysis_id"], "after:p2")
        self.assertEqual(source["fragment"]["text"], NEW)
        self.assertEqual(source["fragment"]["source_locator"]["original_fragment_id"], "p2")
        with self.assertRaises(ChatError) as caught:
            self.store.source(saved["analysis_id"], "foreign:p2")
        self.assertEqual(caught.exception.code, "source_not_found")

    def test_demo_and_unreviewed_version_assignments_cannot_create_chat_snapshot(self):
        for flag in ["needs_review", "is_demo", "is_mock"]:
            with self.subTest(flag=flag), self.assertRaises(ChatError) as caught:
                self.store.save({**legacy_result(), flag: True})
            self.assertEqual(caught.exception.code, "chat_unavailable")


class ToolEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = snapshot()
        self.store = DocumentStore(self.snapshot["packet"])
        self.tools = ChatTools(self.snapshot, self.store, self.store.search_fragments)

    def test_search_and_old_finding_do_not_count_as_read_evidence(self):
        self.tools.execute("get_finding", {"finding_id": "f1"})
        hits = self.tools.execute("search", {"query": "контролирует", "role": "after", "document_id": None, "limit": 10})
        self.assertTrue(hits["hits"])
        with self.assertRaises(ValueError):
            self.tools.execute("finish_answer", answer())
        self.assertIsNone(self.tools.answer)

    def test_unread_foreign_and_inexact_citations_rejected_then_exact_quote_accepted(self):
        self.tools.execute(*read_call())
        for bad in [answer("foreign:p2"), answer("before:p2", OLD), answer(quote="Сектор утверждает все договоры.")]:
            with self.subTest(bad=bad["citations"]), self.assertRaises(ValueError):
                self.tools.execute("finish_answer", bad)
        self.assertIsNone(self.tools.answer)
        self.assertTrue(self.tools.execute("finish_answer", answer())["accepted"])
        citation = self.tools.answer["citations"][0]
        self.assertEqual(citation["document_name"], "after.docx")
        self.assertEqual(citation["sha256"], self.snapshot["packet"]["documents"][1]["sha256"])
        self.assertEqual(self.tools.answer["human_review"], "unreviewed")

    def test_unattached_and_unknown_citation_or_finding_are_rejected(self):
        self.tools.execute(*read_call())
        values = []
        unattached = answer()
        unattached["blocks"][0]["citation_ids"] = []
        values.append(unattached)
        foreign = answer()
        foreign["blocks"][0]["citation_ids"] = ["other"]
        values.append(foreign)
        unknown = answer()
        unknown["blocks"][0]["finding_ids"] = ["foreign-finding"]
        values.append(unknown)
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.tools.execute("finish_answer", value)

    def test_absence_needs_full_after_read_ready_packet_and_limitations(self):
        self.tools.execute(*read_call("before:p2"))
        value = answer("before:p2", OLD, claims_absence=True, analysis_relation="supports")
        with self.assertRaises(ValueError):
            self.tools.execute("finish_answer", value)
        self.tools.execute(*read_call(scope="document"))
        self.assertTrue(self.tools.execute("get_coverage", {})["after_fully_read"])
        for ready, limitations in [(False, ["Только загруженный комплект."]), (True, [])]:
            self.snapshot["packet"]["ready"] = ready
            with self.subTest(ready=ready), self.assertRaises(ValueError):
                self.tools.execute("finish_answer", {**value, "limitations": limitations})
        self.snapshot["packet"]["ready"] = True
        self.assertTrue(self.tools.execute("finish_answer", value)["accepted"])

    def test_partial_extraction_never_supports_absence_after_all_available_text_read(self):
        self.snapshot["packet"]["complete_read"] = False
        self.tools.execute(*read_call(scope="document"))
        self.assertFalse(self.tools.execute("get_coverage", {})["after_fully_read"])
        with self.assertRaises(ValueError):
            self.tools.execute("finish_answer", answer(claims_absence=True))

    def test_reading_one_after_document_does_not_cover_other_after_documents(self):
        extra = deepcopy(self.snapshot["packet"]["documents"][1])
        extra["id"], extra["name"] = "annex", "annex.docx"
        for p in extra["paragraphs"]:
            p["id"], p["document_id"] = "annex:" + p["id"], "annex"
        self.snapshot["packet"]["documents"].append(extra)
        self.store = DocumentStore(self.snapshot["packet"])
        tools = ChatTools(self.snapshot, self.store, self.store.search_fragments)
        tools.execute(*read_call(scope="document"))
        self.assertFalse(tools.execute("get_coverage", {})["after_fully_read"])
        with self.assertRaises(ValueError):
            tools.execute("finish_answer", answer(claims_absence=True))

    def test_paginated_document_only_counts_returned_fragments_toward_absence(self):
        result = legacy_result()
        result["after"] = document(NEW, *[f"{i + 3}. Контекст документа. " + "Описание функции и условий. " * 20 for i in range(50)])
        packet, findings = legacy_packet(result)
        snap = {**self.snapshot, "packet": packet, "findings": findings}
        store = DocumentStore(packet)
        tools = ChatTools(snap, store, store.search_fragments)
        page = tools.execute(*read_call("after:p1", scope="document"))
        self.assertIsNotNone(page["next_offset"])
        self.assertFalse(tools.execute("get_coverage", {})["after_fully_read"])
        with self.assertRaises(ValueError):
            tools.execute("finish_answer", answer("after:p1", claims_absence=True))
        seen = {p["id"] for p in page["fragments"]}
        while page["next_offset"] is not None:
            page = tools.execute("read_context", {"fragment_id": "after:p1", "scope": "document", "offset": page["next_offset"]})
            self.assertFalse(seen & {p["id"] for p in page["fragments"]})
            seen.update(p["id"] for p in page["fragments"])
        self.assertEqual(len(seen), 51)
        self.assertTrue(tools.execute("get_coverage", {})["after_fully_read"])
        self.assertTrue(tools.execute("finish_answer", answer("after:p1", claims_absence=True))["accepted"])

    def test_analysis_claims_need_existing_finding_and_summary_keeps_mode(self):
        summary = self.tools.execute("get_analysis_summary", {})
        self.assertEqual(summary["mode"], "rules")
        self.assertEqual(summary["review_context"], "server_snapshot_only")
        value = answer(citations=[], analysis_relation="supports")
        value["blocks"][0].update(basis="analysis", citation_ids=[])
        with self.assertRaises(ValueError):
            self.tools.execute("finish_answer", value)
        value["blocks"][0]["finding_ids"] = ["f1"]
        self.assertTrue(self.tools.execute("finish_answer", value)["accepted"])


class ChatAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snapshot = snapshot()
        self.original = deepcopy(self.snapshot)
        self.progress = []
        self.no_network = patch("ayqyn.providers.llm.agent_turn", side_effect=AssertionError("Live model forbidden"))
        self.no_network.start()
        self.addCleanup(self.no_network.stop)

    def turn(self, provider, history=None, **kwargs):
        return agent.run_turn(self.snapshot, history or [], {"text": "А в новой редакции?", "finding_ids": ["f1"]},
                              {"model": "fake-model", "key": "fake-private-key"}, self.root / "turn", self.progress.append,
                              driver=provider, **kwargs)

    def trace(self):
        return json.loads((self.root / "turn" / "trace.json").read_text(encoding="utf-8"))

    def test_multiturn_question_passes_history_and_selected_finding_without_mutating_analysis(self):
        first = self.turn(ScriptedProvider(*[read_call(), ("finish_answer", answer())]))
        history = [{"role": "user", "text": "Кто контролирует исполнение договоров?"},
                   {"role": "assistant", **first}]
        provider = ScriptedProvider(read_call(), ("finish_answer", answer()))
        second = self.turn(provider, history)
        context = json.loads(provider.calls[0]["messages"][1]["content"])
        self.assertEqual(context["history"][0]["text"], history[0]["text"])
        self.assertEqual(context["history"][1]["citations"], first["citations"])
        self.assertEqual(context["selected_finding_ids"], ["f1"])
        self.assertEqual(second["analysis_relation"], "challenges")
        self.assertEqual(second["metrics"]["model_calls"], 2)
        self.assertEqual(self.snapshot, self.original)

    def test_previous_turn_citation_must_be_read_again(self):
        first = self.turn(ScriptedProvider(read_call(), ("finish_answer", answer())))
        provider = ScriptedProvider(("finish_answer", answer()), read_call(), ("finish_answer", answer()))
        self.turn(provider, [{"role": "assistant", **first}])
        rejection = json.loads(provider.calls[1]["messages"][-1]["content"])
        self.assertFalse(rejection["accepted"])
        self.assertIn("прочитанного", rejection["error"])
        self.assertEqual(self.trace()["counts"]["model_calls"], 3)

    def test_hallucinated_quote_is_returned_for_repair_and_only_fixed_answer_published(self):
        provider = ScriptedProvider(read_call(), ("finish_answer", answer(quote="Выдуманная обязанность отдела.")),
                                    ("finish_answer", answer()))
        result = self.turn(provider)
        rejection = json.loads(provider.calls[2]["messages"][-1]["content"])
        self.assertFalse(rejection["accepted"])
        self.assertEqual(result["citations"][0]["quote"], NEW)
        self.assertEqual([e["accepted"] for e in self.trace()["events"]], [None, False, True])

    def test_unknown_tool_is_rejected_without_execution_and_agent_can_recover(self):
        provider = ScriptedProvider(("delete_analysis", {"id": "all"}), ("finish_answer", clarification()))
        result = self.turn(provider)
        rejection = json.loads(provider.calls[1]["messages"][-1]["content"])
        self.assertFalse(rejection["accepted"])
        self.assertEqual(result["outcome"], "needs_clarification")
        self.assertEqual(self.snapshot, self.original)

    def test_model_call_budget_is_enforced_and_checkpointed(self):
        provider = ScriptedProvider(*[("get_analysis_summary", {})] * agent.MAX_MODEL_CALLS)
        with self.assertRaises(ChatError) as caught:
            self.turn(provider)
        self.assertEqual(caught.exception.code, "budget_exhausted")
        self.assertEqual(len(provider.calls), agent.MAX_MODEL_CALLS)
        self.assertEqual(self.trace()["counts"]["model_calls"], agent.MAX_MODEL_CALLS)

    def test_tool_budget_stops_before_an_extra_model_call(self):
        provider = ScriptedProvider(("list_documents", {}), ("get_analysis_summary", {}), ("finish_answer", clarification()))
        with patch.object(agent, "MAX_TOOL_CALLS", 2), self.assertRaises(ChatError) as caught:
            self.turn(provider)
        self.assertEqual(caught.exception.code, "budget_exhausted")
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(self.trace()["counts"]["tool_calls"], 2)

    def test_repeated_invalid_evidence_reports_failure_instead_of_answer(self):
        provider = ScriptedProvider(*[("finish_answer", answer())] * agent.MAX_MODEL_CALLS)
        with self.assertRaises(ChatError) as caught:
            self.turn(provider)
        self.assertEqual(caught.exception.code, "invalid_evidence")
        self.assertFalse(self.trace()["coverage"]["after_fully_read"])

    def test_deadline_rejects_late_success_and_bounds_provider_timeout(self):
        now = [0.0]
        provider = ScriptedProvider(("finish_answer", clarification()))
        def slow_provider(*args, **kwargs):
            response = provider(*args, **kwargs)
            now[0] = agent.MAX_SECONDS + 1
            return response
        with self.assertRaises(ChatError) as caught:
            self.turn(slow_provider, clock=lambda: now[0])
        self.assertEqual(caught.exception.code, "budget_exhausted")
        self.assertLessEqual(provider.calls[0]["timeout_seconds"], agent.MAX_SECONDS)
        self.assertEqual(self.trace()["counts"]["tool_calls"], 0)

    def test_empty_search_does_not_justify_absence_and_can_finish_insufficient(self):
        class EmptyIndex:
            def __init__(self, store, path, config):
                self.store = store
            def build(self):
                pass
            def search(self, **kwargs):
                return {"hits": [], "matched_count": 0, "method": "hybrid"}
        insufficient = clarification()
        insufficient.update(outcome="insufficient_data", limitations=["Новая редакция не прочитана полностью."])
        insufficient["blocks"][0].update(kind="explanation", text="Совпадений нет, но потеря не доказана.")
        provider = ScriptedProvider(read_call("before:p2"),
                                    ("search", {"query": "контроль исполнения договоров", "role": "after", "document_id": None, "limit": 5}),
                                    ("finish_answer", answer("before:p2", OLD, claims_absence=True, analysis_relation="supports")),
                                    ("finish_answer", insufficient))
        result = self.turn(provider, index_factory=EmptyIndex)
        self.assertFalse(json.loads(provider.calls[3]["messages"][-1]["content"])["accepted"])
        self.assertEqual(result["outcome"], "insufficient_data")
        self.assertFalse(result["claims_absence"])
        self.assertFalse(result["coverage"]["after_fully_read"])

    def test_provider_failure_does_not_echo_secret_and_keeps_trace(self):
        provider = Mock(side_effect=ValueError("failed with fake-private-key"))
        with self.assertRaises(ChatError) as caught:
            self.turn(provider)
        self.assertEqual(caught.exception.code, "provider_error")
        self.assertNotIn("fake-private-key", json.dumps(caught.exception.public()))
        self.assertEqual(self.trace()["counts"]["model_calls"], 1)

    def test_embedding_deadline_uses_remaining_time_before_each_batch(self):
        config = {}
        remaining = iter([12.5, 3.0])
        observed = []
        def delegate(texts):
            observed.append((texts, config["_embedding_timeout_seconds"]))
            return [[1.0]] * len(texts)
        bounded = agent.DeadlineEmbedder(delegate, config, lambda: next(remaining))
        self.assertEqual(bounded(["первый"]), [[1.0]])
        self.assertEqual(bounded(["второй"]), [[1.0]])
        self.assertEqual([item[1] for item in observed], [12.5, 3.0])

    def test_history_omission_is_reported_to_provider_and_user(self):
        history = [{"role": "user", "text": "старое сообщение" * 3000}, {"role": "user", "text": "последний вопрос"}]
        provider = ScriptedProvider(("finish_answer", clarification()))
        result = self.turn(provider, history)
        context = json.loads(provider.calls[0]["messages"][1]["content"])
        self.assertEqual(context["history"], [history[-1]])
        self.assertEqual(context["omitted_history_messages"], 1)
        self.assertEqual(result["metrics"]["history_messages_omitted"], 1)
        self.assertTrue(any("часть истории" in limitation for limitation in result["limitations"]))


if __name__ == "__main__":
    unittest.main()
