"""Adapt existing results without reparsing documents or mutating their IDs."""
from copy import deepcopy
import hashlib
import json
import os
import re
import threading
from uuid import uuid4
from pathlib import Path

from ayqyn.agent.state import atomic_json
from ayqyn.documents.store import DocumentStore
from ayqyn.storage.runs import utc_now
from ayqyn.chat.errors import ChatError

_LINKS = ("parent_id", "previous_id", "next_id", "heading_id", "table_id", "row_id")
_LIST_LINKS = ("row_fragment_ids", "header_row_ids", "header_fragment_ids", "first_row_fragment_ids")
ID = re.compile(r"a-[a-f0-9]{32}")


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def clean(value, secrets=()):
    text = json.dumps(value, ensure_ascii=False, allow_nan=False)
    for secret in secrets:
        if secret:
            # JSON escaping matters when a key is echoed inside a JSON string.
            text = text.replace(json.dumps(secret, ensure_ascii=False)[1:-1], "[REDACTED]")
    return json.loads(text)


def capability():
    from ayqyn.providers.llm import provider_settings
    try:
        provider_settings({})
        state, reason = "available", None
    except ValueError:
        state, reason = "requires_model", "model_required"
    return {"state": state, "reason_code": reason, "review_context": "server_snapshot_only"}


def legacy_packet(result):
    packet = {"documents": [], "warnings": deepcopy(result.get("warnings", [])),
              "ready": True, "complete_read": True, "mixed": False, "duplicates": []}
    mapping = {}
    documents = deepcopy(result.get("documents") or [])
    pair = not documents
    if pair:
        documents = [{**deepcopy(result[side]), "id": side, "side": side} for side in ("before", "after")]
    for doc in documents:
        side = doc["side"]
        doc.update(role=side, format="docx", read_status="read",
                   warnings=doc.get("warnings", []), role_reason="Роль сохранена из выполненного анализа.")
        old_ids = {p["id"] for p in doc["paragraphs"]}
        ids = {key: side + ":" + key if pair else key for key in old_ids}
        # Legacy batch links may still be local pN even though paragraph IDs are dN:pN.
        aliases = {p.get("original_id", p["id"]): ids[p["id"]] for p in doc["paragraphs"]}
        aliases.update(ids)
        for p in doc["paragraphs"]:
            old = p["id"]
            canonical = ids[old]
            mapping[(side, old)] = canonical
            p.update(id=canonical, local_id=p.get("original_id", old), document_id=doc["id"],
                     document_name=doc["name"], format="docx", page=None, printed_page=None,
                     source_locator={"side": side, "original_fragment_id": old})
            for field in _LINKS:
                value = p.get(field)
                if isinstance(value, str):
                    p[field] = aliases.get(value, doc["id"] + ":" + value)
            for field in _LIST_LINKS:
                if isinstance(p.get(field), list):
                    p[field] = [aliases.get(v, doc["id"] + ":" + v) for v in p[field]]
        doc["synthetic"] = bool(re.search(r"synthetic|синтетическ|учебный пример",
                                         "\n".join(p["text"] for p in doc["paragraphs"][:12]), re.I))
        packet["documents"].append(doc)
    for side in ("before", "after"):
        packet[side] = {**deepcopy(result[side]),
                        "paragraphs": [p for d in packet["documents"] if d["role"] == side for p in d["paragraphs"]]}
    findings = deepcopy(result["findings"])
    for f in findings:
        for side in ("before", "after"):
            f[side + "_ids"] = [mapping[(side, key)] for key in f.get(side + "_ids", [])]
    return packet, findings


class AnalysisStore:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.RLock()

    def path(self, identifier):
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            raise ChatError("analysis_not_found", "Анализ не найден.", 404)
        path = self.root / identifier
        if path.is_symlink() or not path.resolve().is_relative_to(self.root.resolve()):
            raise ChatError("analysis_not_found", "Анализ не найден.", 404)
        return path

    def load(self, identifier):
        path = self.path(identifier) / "snapshot.json"
        try:
            if path.is_symlink():
                raise ValueError()
            value = json.loads(path.read_text(encoding="utf-8"))
            checksum = value.pop("snapshot_sha256")
            if value["schema_version"] != 1 or value["analysis_id"] != identifier or digest(value) != checksum:
                raise ValueError()
            value["snapshot_sha256"] = checksum
            return value
        except FileNotFoundError:
            raise ChatError("analysis_not_found", "Анализ не найден.", 404) from None
        except (OSError, ValueError, KeyError, TypeError):
            raise ChatError("storage_error", "Снимок анализа повреждён или недоступен.", 500) from None

    def save(self, result, *, packet=None, research_id=None, secrets=()):
        if result.get("needs_review") or result.get("is_mock") or result.get("is_demo"):
            raise ChatError("chat_unavailable", "Для чата нужен выполненный анализ.", 422)
        if packet is None:
            packet, findings = legacy_packet(result)
        else:
            packet, findings = deepcopy(packet), deepcopy(result["findings"])
            for doc in packet["documents"]:
                for p in doc["paragraphs"]:
                    p["source_locator"] = {"side": doc["role"], "original_fragment_id": p["id"]}
        for i, finding in enumerate(findings, 1):
            finding.setdefault("id", "result-" + str(i))
        if len({f["id"] for f in findings}) != len(findings):
            raise ValueError("Finding identifiers must be unique.")
        payload = clean({"source_kind": "research" if research_id else "analyze", "research_id": research_id,
                         "packet": packet, "findings": findings, "result": deepcopy(result)},
                        (*secrets, os.getenv("OPENAI_API_KEY", "")))
        identifier = "a-" + (digest(payload)[:32] if research_id else uuid4().hex)
        with self.lock:
            if (self.path(identifier) / "snapshot.json").exists():
                return self.load(identifier)
            value = {"schema_version": 1, "analysis_id": identifier, "created_at": utc_now(),
                     "analysis_mode": result["mode"], "synthetic": any(d.get("synthetic") for d in packet["documents"]),
                     "limitations": list(dict.fromkeys(payload["packet"].get("warnings", []) +
                                                       payload["result"].get("warnings", []))), **payload}
            value["snapshot_sha256"] = digest(value)
            directory = self.path(identifier)
            directory.mkdir(parents=True, exist_ok=True)
            atomic_json(directory / "snapshot.json", value)
            return value

    def from_research(self, state):
        if state.data["status"] not in {"completed", "insufficient_data"}:
            return {"analysis_id": None, "chat": {"state": "unavailable", "reason_code": "research_not_finished"}}
        from ayqyn.api.workspace import workspace_result
        snapshot = self.save(workspace_result(state), packet=state.packet,
                             research_id=state.data["id"], secrets=state.secrets)
        return {"analysis_id": snapshot["analysis_id"], "chat": capability()}

    def public(self, identifier):
        snapshot = self.load(identifier)
        return {**{k: snapshot[k] for k in ("schema_version", "analysis_id", "created_at", "source_kind",
                                          "analysis_mode", "synthetic", "limitations", "result")},
                "chat": capability()}

    def source(self, identifier, fragment_id, offset=0):
        snapshot = self.load(identifier)
        store = DocumentStore(snapshot["packet"])
        if fragment_id not in store.fragments:
            raise ChatError("source_not_found", "Источник не найден в этом анализе.", 404)
        try:
            context = store.read_context_page(fragment_id, offset=offset)
        except ValueError:
            raise ChatError("invalid_request", "Некорректная страница контекста.") from None
        p = store.fragments[fragment_id]
        doc = store.documents[p["document_id"]]
        return {"schema_version": 1, "analysis_id": identifier, "fragment": p, "document": {k: doc.get(k) for k in
                ("id", "name", "sha256", "role", "format")}, "context": context}
