"""Loopback-only MVP server. Uploaded documents and keys stay in request memory."""
import argparse
import base64
import binascii
import json
import mimetypes
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote
from analyzer import parse_docx, analyze_rules
from llm import compare_with_model

ROOT = Path(__file__).resolve().parent
STATIC = {'index.html','analyze.html','styles.css','analyze.css','app.js','analysis.js','cases.js','sources.js'}


def decode_document(value):
    if not isinstance(value, dict) or not isinstance(value.get('name'),str) or not isinstance(value.get('data'),str):
        raise ValueError('Нужны два DOCX: до и после.')
    if len(value['data']) > 14_000_000: raise ValueError('Максимальный размер DOCX — 10 МБ.')
    try: data = base64.b64decode(value['data'], validate=True)
    except (ValueError,binascii.Error): raise ValueError('Повреждена загрузка файла.') from None
    if len(data)>10_000_000: raise ValueError('Максимальный размер DOCX — 10 МБ.')
    return parse_docx(data, value['name'])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def safe_host(self):
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

    def send_json(self, code, value):
        data = json.dumps(value,ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.safe_host(): return self.send_json(403,{'error':'Недопустимый адрес сервера.'})
        path = unquote(urlparse(self.path).path).lstrip('/') or 'analyze.html'
        if path=='api/config':
            return self.send_json(200, {'hasKey':bool(os.getenv('OPENAI_API_KEY')), 'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),
                                        'base':os.getenv('OPENAI_BASE_URL','https://api.openai.com/v1')})
        candidate = (ROOT/path).resolve()
        source = candidate.parent == (ROOT/'sources').resolve() and candidate.suffix=='.docx'
        if not ((path in STATIC or source) and candidate.is_file() and candidate.is_relative_to(ROOT)):
            return self.send_json(404,{'error':'Не найдено.'})
        data = candidate.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',mimetypes.guess_type(candidate)[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        origin = self.headers.get('Origin')
        allowed = {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
        if not self.safe_host() or (origin and origin not in allowed): return self.send_json(403,{'error':'Недопустимый источник запроса.'})
        if self.path != '/api/analyze': return self.send_json(404,{'error':'Не найдено.'})
        try:
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json': raise ValueError('Ожидается JSON.')
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 29_000_000: raise ValueError('Слишком большой или пустой запрос.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise ValueError('Некорректный запрос.')
            before, after = decode_document(data.get('before')), decode_document(data.get('after'))
            findings = analyze_rules(before,after)
            for item in findings:
                item['method']='rules'
                item['reviewed']=False
            warnings=[]
            mode='rules'
            usage={}
            if data.get('useAI'):
                config = data.get('config') or {}
                if not isinstance(config,dict): raise ValueError('Некорректные настройки модели.')
                try:
                    ai,rejected,usage = compare_with_model(before,after,config)
                    # AI is the semantic pass; exact rule findings remain visible for cross-checking.
                    findings.extend(ai)
                    mode='ai'
                    if rejected: warnings.append(f'Отброшено выводов с некорректными источниками: {rejected}.')
                    if not ai: warnings.append('Модель не вернула допустимых находок. Это не доказывает отсутствие рисков.')
                except ValueError as exc:
                    warnings.append(str(exc))
                    mode='fallback'
            if before['sha256']==after['sha256']: warnings.append('Загружены одинаковые файлы. Внутренние пересечения всё ещё могут присутствовать.')
            self.send_json(200,{'before':before,'after':after,'findings':findings,'mode':mode,'warnings':warnings,'usage':usage})
        except (ValueError,UnicodeError) as exc:
            self.send_json(400,{'error':str(exc)})
        except Exception:
            self.send_json(500,{'error':'Не удалось обработать документы. Проверьте формат и повторите загрузку.'})


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'http://127.0.0.1:{server.server_port}',flush=True)
    server.serve_forever()
