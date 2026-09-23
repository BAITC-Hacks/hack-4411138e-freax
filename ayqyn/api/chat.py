"""HTTP adapters for chat. No frontend routes or model work in GET handlers."""
import json
import threading
from urllib.parse import urlparse, parse_qs

from ayqyn.chat.errors import ChatError
from ayqyn.chat.service import ChatService
from ayqyn.chat.snapshots import capability

SERVICE_LOCK = threading.Lock()


def get_service(http_server):
    from ayqyn.api import server
    with SERVICE_LOCK:
        if not hasattr(http_server, "chat_service"):
            http_server.chat_service = ChatService(server.ANALYSIS_ROOT, server.RESEARCH_ROOT)
        return http_server.chat_service


def analysis_features(handler, result, config):
    try:
        saved = get_service(handler.server).store.save(result, secrets=(config.get("key", ""),))
        return {"analysis_id": saved["analysis_id"], "chat": capability()}
    except (OSError, ValueError, KeyError, ChatError):
        return {"analysis_id": None, "chat": {"state": "unavailable", "reason_code": "snapshot_failed",
                                             "review_context": "server_snapshot_only"}}


def research_features(handler, state):
    try:
        return get_service(handler.server).store.from_research(state)
    except (OSError, ValueError, KeyError, ChatError):
        return {"analysis_id": None, "chat": {"state": "unavailable", "reason_code": "snapshot_failed"}}


def handle(handler, method):
    try:
        allowed = {f"http://127.0.0.1:{handler.server.server_port}", f"http://localhost:{handler.server.server_port}"}
        if not handler.safe_host() or handler.headers.get("Origin") not in allowed | {None}:
            raise ChatError("invalid_origin", "Недопустимый источник запроса.", 403)
        parsed = urlparse(handler.path)
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 3:
            raise ChatError("analysis_not_found", "Анализ не найден.", 404)
        identifier, suffix = parts[2], parts[3:]
        service = get_service(handler.server)
        if method == "GET":
            if not suffix:
                result = service.store.public(identifier)
            elif suffix == ["chat"]:
                result = service.history(identifier)
            elif len(suffix) == 3 and suffix[:2] == ["chat", "turns"]:
                result = service.turn(identifier, suffix[2])
            elif suffix == ["source"]:
                query = parse_qs(parsed.query)
                try:
                    offset = int(query.get("offset", ["0"])[0])
                except ValueError:
                    raise ChatError("invalid_request", "Некорректный offset.") from None
                result = service.store.source(identifier, query.get("fragment_id", [""])[0], offset)
            else:
                raise ChatError("not_found", "Метод не найден.", 404)
            return handler.send_json(200, result)
        if suffix != ["chat", "messages"]:
            raise ChatError("not_found", "Метод не найден.", 404)
        if handler.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise ChatError("invalid_request", "Ожидается JSON.")
        try:
            length = int(handler.headers.get("Content-Length", "0"))
            if not 0 < length <= 32768:
                raise ValueError()
            value = json.loads(handler.rfile.read(length))
        except (ValueError, UnicodeError):
            raise ChatError("invalid_request", "Некорректный или слишком большой запрос.") from None
        code, result = service.submit(identifier, value)
        return handler.send_json(code, result)
    except ChatError as exc:
        return handler.send_json(exc.status, {"error": exc.public()})
    except Exception:
        return handler.send_json(500, {"error": {"code": "internal_error",
                                 "message": "Операция чата не завершена.", "retryable": True}})
