"""Loopback-only MVP server. Run evidence is local; credentials stay in memory."""
import argparse
import base64
import binascii
import json
import mimetypes
import os
import re
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote
from analyzer import parse_docx, analyze_rules
from llm import compare_with_model
from run_record import new_run_path
from packets import read_packet
from research_agent import prepare_research,restore_research,run_research,public_result
from research_state import ResearchState

ROOT = Path(__file__).resolve().parent
STATIC = {'index.html','analyze.html','styles.css','analyze.css','app.js','analysis.js','cases.js','sources.js'}
RESEARCH_ROOT=ROOT/'output'/'research'
ACTIVE_RESEARCH=set()
RESEARCH_LOCK=threading.Lock()
# Explicit frontend asset allowlist; private files remain inaccessible.
STATIC.update({
    'assets/kazakhtelecom-logo.svg',
    'i18n.js',
    'icons.js',
    'preferences.js',
    'vendor/lucide/createElement.mjs',
    'vendor/lucide/defaultAttributes.mjs',
    'vendor/lucide/icons/arrow-right.mjs',
    'vendor/lucide/icons/building.mjs',
    'vendor/lucide/icons/check.mjs',
    'vendor/lucide/icons/chevron-left.mjs',
    'vendor/lucide/icons/chevron-right.mjs',
    'vendor/lucide/icons/circle-check.mjs',
    'vendor/lucide/icons/download.mjs',
    'vendor/lucide/icons/external-link.mjs',
    'vendor/lucide/icons/file-text.mjs',
    'vendor/lucide/icons/files.mjs',
    'vendor/lucide/icons/git-compare-arrows.mjs',
    'vendor/lucide/icons/info.mjs',
    'vendor/lucide/icons/list-checks.mjs',
    'vendor/lucide/icons/loader-circle.mjs',
    'vendor/lucide/icons/menu.mjs',
    'vendor/lucide/icons/monitor.mjs',
    'vendor/lucide/icons/moon.mjs',
    'vendor/lucide/icons/plus.mjs',
    'vendor/lucide/icons/search.mjs',
    'vendor/lucide/icons/settings.mjs',
    'vendor/lucide/icons/shield-check.mjs',
    'vendor/lucide/icons/sun.mjs',
    'vendor/lucide/icons/trash.mjs',
    'vendor/lucide/icons/triangle-alert.mjs',
    'vendor/lucide/icons/upload.mjs',
    'vendor/lucide/icons/x.mjs',
})


def research_path(identifier):
    if not isinstance(identifier,str) or not re.fullmatch(r'r-[a-f0-9]{32}',identifier):
        raise ValueError('Некорректный ID исследования.')
    return RESEARCH_ROOT/identifier


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
        if path.startswith('api/research/'):
            try:
                state=ResearchState(research_path(path.removeprefix('api/research/')))
                return self.send_json(200,public_result(state))
            except (ValueError,OSError):
                return self.send_json(404,{'error':'Исследование не найдено.'})
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
        if self.path not in {'/api/analyze','/api/packet/read','/api/research/prepare','/api/research/run'}:
            return self.send_json(404,{'error':'Не найдено.'})
        try:
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json': raise ValueError('Ожидается JSON.')
            length = int(self.headers.get('Content-Length','0'))
            limit=56_000_000 if self.path in {'/api/packet/read','/api/research/prepare'} else 29_000_000
            if not 0 < length <= limit: raise ValueError('Слишком большой или пустой запрос.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise ValueError('Некорректный запрос.')
            if self.path=='/api/packet/read':
                packet=read_packet(data.get('documents'),data.get('mode','auto'),data.get('overrides'))
                return self.send_json(200,packet)
            if self.path.startswith('/api/research/'):
                config=data.get('config') or {}
                if not isinstance(config,dict): raise ValueError('Некорректные настройки модели.')
                if self.path=='/api/research/prepare':
                    packet=read_packet(data.get('documents'),data.get('mode','auto'),data.get('overrides'))
                    state,_,_=prepare_research(packet,data.get('task'),config,budget=data.get('budget'),originals=data.get('documents'))
                    return self.send_json(200,public_result(state))
                path=research_path(data.get('id'))
                with RESEARCH_LOCK:
                    if path.name in ACTIVE_RESEARCH:
                        return self.send_json(409,{'error':'Исследование уже выполняется.'})
                    ACTIVE_RESEARCH.add(path.name)
                try:
                    try:
                        state,store,index=restore_research(path,config)
                    except FileNotFoundError:
                        code,result=404,{'error':'Исследование не найдено.'}
                    else:
                        run_research(state,store,index,config)
                        code,result=200,public_result(state)
                finally:
                    with RESEARCH_LOCK: ACTIVE_RESEARCH.discard(path.name)
                return self.send_json(code,result)
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
                    ai,rejected,usage = compare_with_model(before,after,config,run_dir=new_run_path())
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
