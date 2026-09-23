"""Persistent, idempotent background chat jobs for one local server process."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import re
import threading
from uuid import uuid4

from ayqyn.agent.state import atomic_json
from ayqyn.chat import agent
from ayqyn.chat.errors import ChatError
from ayqyn.chat.snapshots import AnalysisStore, clean, digest, capability
from ayqyn.providers.llm import provider_settings
from ayqyn.providers.embeddings import embedding_settings
from ayqyn.storage.runs import utc_now

ACTIVE = {"queued", "preparing", "answering"}
CONFIG_FIELDS = {"base", "key", "model", "reasoning_effort", "embedding_model", "embedding_dimensions"}
CLIENT_ID = re.compile(r"[A-Za-z0-9_-]{1,100}")
TURN_ID = re.compile(r"t-[a-f0-9]{32}")


class ChatService:
    def __init__(self, root, research_root=None, *, runner=None, max_workers=2):
        self.store = AnalysisStore(root)
        self.research_root = research_root
        self.runner = runner or agent.run_turn
        self.lock = threading.RLock()
        self.unsaved = {}
        self.capacity = threading.BoundedSemaphore(max_workers)
        self.pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="analysis-chat")
        self.recover()

    def close(self):
        self.pool.shutdown(wait=True)

    def _load(self, identifier):
        if identifier in self.unsaved:
            return deepcopy(self.unsaved[identifier])
        path = self.store.path(identifier) / "conversation.json"
        if not path.exists():
            return {"schema_version": 1, "analysis_id": identifier, "conversation_version": 0,
                    "messages": [], "turns": {}, "active_turn": None}
        try:
            if path.is_symlink():
                raise ValueError()
            value = json.loads(path.read_text(encoding="utf-8"))
            if value["schema_version"] != 1 or value["analysis_id"] != identifier:
                raise ValueError()
            return value
        except (ValueError, KeyError, OSError):
            raise ChatError("storage_error", "История чата недоступна.", 500) from None

    def _save(self, state, secrets=()):
        try:
            atomic_json(self.store.path(state["analysis_id"]) / "conversation.json", clean(state, secrets))
            self.unsaved.pop(state['analysis_id'], None)
        except (OSError, ValueError):
            raise ChatError("storage_error", "Не удалось сохранить состояние чата.", 500) from None

    def recover(self):
        # Only invoked when this server starts, never during polling.
        with self.lock:
            for path in self.store.root.glob("a-*/conversation.json"):
                try:
                    self.store.load(path.parent.name)
                    state = self._load(path.parent.name)
                    changed = False
                    for turn in state["turns"].values():
                        if turn["status"] in ACTIVE:
                            self._finish(state, turn, error=ChatError(
                                "interrupted", "Сервер перезапущен. Повторите вопрос новой попыткой.", retryable=True))
                            changed = True
                    if changed:
                        self._save(state)
                except (ChatError, KeyError, TypeError):
                    # Do not rewrite corrupted files. GET reports a storage error.
                    continue

    @staticmethod
    def _public_turn(state, turn):
        result = {k: deepcopy(turn.get(k)) for k in
                ("analysis_id", "turn_id", "client_message_id", "status", "started_at", "finished_at",
                 "assistant_message", "error")} | {"schema_version": 1, "conversation_version": state["conversation_version"]}
        end = datetime.fromisoformat(turn['finished_at']) if turn.get('finished_at') else datetime.now(timezone.utc)
        result['elapsed_ms'] = max(0, round((end - datetime.fromisoformat(turn['started_at'])).total_seconds() * 1000))
        return result

    def history(self, identifier):
        with self.lock:
            self.store.load(identifier)
            state = self._load(identifier)
            active = state["turns"].get(state["active_turn"])
            return {k: deepcopy(state[k]) for k in
                    ("schema_version", "analysis_id", "conversation_version", "messages")} | {
                    "active_turn": self._public_turn(state, active) if active else None, "chat": capability()}

    def turn(self, identifier, turn_id):
        with self.lock:
            self.store.load(identifier)
            state = self._load(identifier)
            if not isinstance(turn_id, str) or not TURN_ID.fullmatch(turn_id) or turn_id not in state["turns"]:
                raise ChatError("turn_not_found", "Ответ не найден в этом анализе.", 404)
            return self._public_turn(state, state["turns"][turn_id])

    def submit(self, identifier, value):
        if not isinstance(value, dict) or set(value) - {"client_message_id", "expected_version", "text", "finding_ids", "config"}:
            raise ChatError("invalid_request", "Неизвестные поля запроса.")
        cid, text = value.get("client_message_id"), value.get("text")
        version = value.get("expected_version")
        ids, config = value.get("finding_ids", []), deepcopy(value.get("config", {}))
        if (not isinstance(cid, str) or not CLIENT_ID.fullmatch(cid) or
                not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000 or
                type(version) is not int or version < 0 or not isinstance(ids, list) or len(ids) > 5 or
                any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids)):
            raise ChatError("invalid_request", "Нужны ID сообщения, версия, вопрос до 4000 символов и до пяти находок.")
        if not isinstance(config, dict) or set(config) - CONFIG_FIELDS:
            raise ChatError("invalid_request", "Неизвестные настройки модели.")
        for field in CONFIG_FIELDS - {"embedding_dimensions"}:
            if field in config and (not isinstance(config[field], str) or len(config[field]) > 4096):
                raise ChatError("invalid_request", "Некорректные настройки модели.")
        if "reasoning_effort" in config and config["reasoning_effort"] not in {"none", "low", "medium", "high"}:
            raise ChatError("invalid_request", "Некорректный режим рассуждения.")
        try:
            embedding_settings(config)
        except ValueError:
            raise ChatError("invalid_request", "Некорректные настройки поиска.") from None
        public_config = {k: v for k, v in config.items() if k != "key"}
        fingerprint = digest({"text": text.strip(), "finding_ids": ids, "config": public_config})
        secrets = (config.get("key", ""), os.getenv("OPENAI_API_KEY", ""))
        request = clean({"text": text.strip(), "finding_ids": ids}, secrets)
        with self.lock:
            snapshot = self.store.load(identifier)
            state = self._load(identifier)
            for turn in state["turns"].values():
                if turn["client_message_id"] == cid:
                    if turn["fingerprint"] != fingerprint:
                        raise ChatError("idempotency_conflict", "Этот ID уже использован для другого вопроса.", 409)
                    return (202 if turn["status"] in ACTIVE else 200), self._public_turn(state, turn)
            if identifier in self.unsaved:
                self._save(state, secrets)
            if not set(ids) <= {f["id"] for f in snapshot["findings"]}:
                raise ChatError("invalid_request", "Находка не принадлежит этому анализу.")
            if state["active_turn"]:
                raise ChatError("turn_in_progress", "Предыдущий ответ ещё готовится.", 409,
                                active_turn_id=state["active_turn"], conversation_version=state["conversation_version"])
            if version != state["conversation_version"]:
                raise ChatError("version_conflict", "Обновите историю перед отправкой вопроса.", 409,
                                conversation_version=state["conversation_version"])
            if len(state["turns"]) >= 100:
                raise ChatError("capacity_exceeded", "Достигнут лимит 100 вопросов для этого анализа.", 429)
            try:
                base, key, model = provider_settings(config)
            except ValueError:
                raise ChatError("model_required", "Настройте модель с инструментами для чата.", 422) from None
            config.update(base=base, key=key, model=model)
            secrets = (*secrets, key)
            if not self.capacity.acquire(blocking=False):
                raise ChatError("capacity_exceeded", "Сервер занят. Повторите позже.", 429, retryable=True)
            turn_id = "t-" + uuid4().hex
            turn = {"analysis_id": identifier, "turn_id": turn_id, "client_message_id": cid,
                    "fingerprint": fingerprint, "status": "queued", "started_at": utc_now(),
                    "finished_at": None, "assistant_message": None, "error": None}
            history = deepcopy(state["messages"])
            state["messages"].append({"id": "m-" + uuid4().hex, "role": "user", "turn_id": turn_id,
                                      "client_message_id": cid, "created_at": utc_now(), **request})
            state["turns"][turn_id] = turn
            state["active_turn"] = turn_id
            state["conversation_version"] += 1
            try:
                self._save(state, secrets)
            except ChatError:
                self.capacity.release()
                raise
            response = self._public_turn(state, turn)
            try:
                self.pool.submit(self._run, identifier, turn_id, snapshot, history, request, config, secrets)
            except RuntimeError:
                self._finish(state, turn, error=ChatError("interrupted", "Сервер останавливается.", retryable=True))
                try:
                    self._save(state, secrets)
                finally:
                    self.capacity.release()
                raise ChatError("capacity_exceeded", "Сервер останавливается.", 503, retryable=True) from None
            return 202, response

    def _progress(self, identifier, turn_id, status):
        with self.lock:
            state = self._load(identifier)
            state["turns"][turn_id]["status"] = status
            self._save(state)

    @staticmethod
    def _finish(state, turn, answer=None, error=None):
        if error:
            turn["status"] = error.code if error.code in {"interrupted", "budget_exhausted"} else "failed"
            turn["error"] = error.public()
            state["messages"].append({"id": "m-" + uuid4().hex, "role": "assistant", "turn_id": turn["turn_id"],
                                      "created_at": utc_now(), "error": error.public()})
        else:
            message = {"id": "m-" + uuid4().hex, "role": "assistant", "turn_id": turn["turn_id"],
                       "created_at": utc_now(), **answer}
            turn.update(status="completed", assistant_message=message)
            state["messages"].append(message)
        turn["finished_at"] = utc_now()
        state["active_turn"] = None
        state["conversation_version"] += 1

    def _run(self, identifier, turn_id, snapshot, history, request, config, secrets):
        answer, error = None, None
        try:
            try:
                answer = self.runner(snapshot, history, request, config,
                                     self.store.path(identifier) / "turns" / turn_id,
                                     lambda status: self._progress(identifier, turn_id, status),
                                     research_root=self.research_root)
            except ChatError as exc:
                error = exc
            except Exception:
                error = ChatError("internal_error", "Ответ не завершён из-за внутренней ошибки.", 500, retryable=True)
            with self.lock:
                state = self._load(identifier)
                self._finish(state, state["turns"][turn_id], answer=answer, error=error)
                try:
                    self._save(state, secrets)
                except ChatError:
                    # Never leave polling stuck or claim a durably saved successful answer.
                    turn = state['turns'][turn_id]
                    turn.update(status='failed', assistant_message=None,
                                error=ChatError('storage_error', 'Ответ не удалось сохранить.', 500, retryable=True).public())
                    state['messages'][-1] = {'id': 'm-' + uuid4().hex, 'role': 'assistant',
                                            'turn_id': turn_id, 'created_at': utc_now(), 'error': turn['error']}
                    self.unsaved[identifier] = clean(state, secrets)
        finally:
            self.capacity.release()
