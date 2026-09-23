"""Read-only tools for questions about one saved analysis."""
from copy import deepcopy
import json

from ayqyn.agent.tools import obj, TEXT, NULL_TEXT, STRINGS, validate_shape

CITATION = obj({"id": TEXT, "fragment_id": TEXT, "quote": TEXT})
BLOCK = obj({"kind": {"type": "string", "enum": ["claim", "explanation", "limitation", "question"]},
             "basis": {"type": "string", "enum": ["source", "analysis", "user", "conversation"]},
             "text": TEXT, "citation_ids": STRINGS, "finding_ids": STRINGS})
DEFINITIONS = {
    "get_analysis_summary": ("Режим, ограничения и находки исходного анализа. Это не доказанные факты.", obj({})),
    "get_finding": ("Прежний вывод с каноническими адресами источников для перепроверки.", obj({"finding_id": TEXT})),
    "list_documents": ("Документы только текущего анализа, их роли, ограничения и первый адрес.", obj({})),
    "search": ("Гибридный поиск; совпадение не считается чтением, отсутствие совпадения не доказывает потерю.", obj({
        "query": TEXT, "role": {"type": ["string", "null"], "enum": ["before", "after", "common", "unknown", None]},
        "document_id": NULL_TEXT, "limit": {"type": "integer", "minimum": 1, "maximum": 20}})),
    "read_context": ("Прочитать пункт с заголовками и продолжениями; next_offset означает непрочитанный остаток.", obj({
        "fragment_id": TEXT, "scope": {"type": "string", "enum": ["section", "document"]},
        "offset": {"type": "integer", "minimum": 0, "maximum": 20000}})),
    "get_coverage": ("Фактическое чтение в текущем ответе; прочтение не доказывает правильность понимания.", obj({})),
    "finish_answer": ("Завершить ответ с точными прочитанными цитатами. Ошибка валидации требует исправления.", obj({
        "outcome": {"type": "string", "enum": ["answered", "insufficient_data", "needs_clarification"]},
        "blocks": {"type": "array", "items": BLOCK},
        "citations": {"type": "array", "items": CITATION},
        "analysis_relation": {"type": "string", "enum": ["supports", "challenges", "not_determined"]},
        "claims_absence": {"type": "boolean"},
        "limitations": STRINGS}))
}
SCHEMAS = [{"type": "function", "function": {"name": name, "description": description,
            "parameters": schema, "strict": True}} for name, (description, schema) in DEFINITIONS.items()]


class ChatTools:
    def __init__(self, snapshot, store, search):
        self.snapshot, self.store, self.search = snapshot, store, search
        self.findings = {f["id"]: f for f in snapshot["findings"]}
        self.answer = None

    def execute(self, name, arguments):
        if name not in DEFINITIONS:
            raise ValueError("Инструмент недоступен в чате.")
        validate_shape(arguments, DEFINITIONS[name][1])
        if name == "get_analysis_summary":
            return {"mode": self.snapshot["analysis_mode"], "synthetic": self.snapshot["synthetic"],
                    "limitations": self.snapshot["limitations"],
                    "research_status": self.snapshot['result'].get('research', {}).get('status'),
                    "research_stop_reason": self.snapshot['result'].get('research', {}).get('stop_reason'),
                    "review_context": "server_snapshot_only",
                    "findings": [{"id": f["id"], "type": f.get("type", f.get("category")),
                                  "title": f.get("title", f.get("function"))} for f in self.findings.values()],
                    "notice": "Это прежние кандидаты. Оценки аналитика в браузере серверу неизвестны."}
        if name == "get_finding":
            key = arguments["finding_id"]
            if key not in self.findings:
                raise ValueError("Находка не принадлежит текущему анализу.")
            return deepcopy(self.findings[key])
        if name == "list_documents":
            documents = self.store.list_documents()
            for doc in documents:
                blocks = self.store.documents[doc["id"]]["paragraphs"]
                doc["first_fragment_id"] = blocks[0]["id"] if blocks else None
            return {"documents": documents}
        if name == "read_context":
            return self.store.read_context_page(**arguments)
        if name == "search":
            return self.search(**arguments)
        if name == "get_coverage":
            return self.store.coverage_summary()
        return self.finish(arguments)

    def finish(self, value):
        if not 1 <= len(value["blocks"]) <= 20 or len(value["citations"]) > 20:
            raise ValueError("Нужны 1–20 блоков ответа и не более 20 цитат.")
        if type(value["claims_absence"]) is not bool:
            raise ValueError("claims_absence должен быть boolean.")
        citations = {}
        for item in value["citations"]:
            cid, key, quote = item["id"], item["fragment_id"], item["quote"]
            if not cid or len(cid) > 80 or cid in citations:
                raise ValueError("Идентификаторы цитат должны быть уникальны.")
            p = self.store.fragments.get(key)
            checked = self.store.check_evidence(key, quote)
            if not checked["exists"] or not checked["was_read"] or len(quote.strip()) < 5 or quote not in p["text"]:
                raise ValueError("Нужна точная цитата из прочитанного в этом ходе источника: " + key)
            doc = self.store.documents[p["document_id"]]
            citations[cid] = {**item, "document_id": doc["id"], "document_name": doc["name"],
                              "sha256": doc["sha256"], "side": doc["role"], "section": p.get("section"),
                              "page": p.get("page"), "printed_page": p.get("printed_page"),
                              "source_locator": p.get("source_locator", {"side": doc["role"], "original_fragment_id": key})}
        cited = set()
        for block in value["blocks"]:
            if not block["text"].strip() or len(block["text"]) > 6000:
                raise ValueError("Пустой или слишком длинный блок ответа.")
            if not set(block["citation_ids"]) <= citations.keys() or not set(block["finding_ids"]) <= self.findings.keys():
                raise ValueError("В блоке есть неизвестная цитата или находка.")
            cited.update(block["citation_ids"])
            if block["basis"] == "source" and not block["citation_ids"]:
                raise ValueError("Утверждение об источнике требует цитаты.")
            if block["kind"] == "claim" and block["basis"] == "analysis" and not block["finding_ids"]:
                raise ValueError("Ссылка на прежнюю находку требует finding_ids.")
        if cited != citations.keys():
            raise ValueError("Цитаты должны быть привязаны к блокам ответа.")
        if value["analysis_relation"] == "challenges" and not citations:
            raise ValueError("Для опровержения нужны прочитанные источники.")
        if value["outcome"] == "needs_clarification" and not any(b["kind"] == "question" for b in value["blocks"]):
            raise ValueError("Уточнение должно содержать вопрос.")
        if value["outcome"] == "insufficient_data" and not value["limitations"]:
            raise ValueError("Опишите недостаток данных.")
        coverage = self.store.coverage_summary()
        if value["claims_absence"] and (not coverage["after_fully_read"] or
                                        not self.snapshot["packet"].get("ready") or not value["limitations"]):
            raise ValueError("Отсутствие нельзя утверждать без полного чтения after и оговорок о комплекте.")
        answer = {**deepcopy(value), "citations": list(citations.values()), "human_review": "unreviewed",
                  "coverage": coverage}
        if len(json.dumps(answer, ensure_ascii=False)) > 60000:
            raise ValueError("Ответ превышает допустимый размер.")
        self.answer = answer
        return {"accepted": True}
