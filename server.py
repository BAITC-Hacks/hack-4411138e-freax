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
from llm import compare_with_model, classify_with_model
from run_record import new_run_path
from packets import read_packet
from research_agent import prepare_research,restore_research,run_research,public_result
from research_state import ResearchState
from batch import MAX_DOCUMENTS, classify_documents, combine_documents
from time import perf_counter

ROOT = Path(__file__).resolve().parent
STATIC = {'index.html','analyze.html','styles.css','analyze.css','app.js','analysis.js','cases.js','sources.js'}
# User-supplied public design assets and local licensed font subsets only.
for folder,extensions in [('distingt-assets',{'.svg','.png','.json','.pdf'}),('fonts',{'.woff2'})]:
    STATIC.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in extensions)
RESEARCH_ROOT=ROOT/'output'/'research'
ACTIVE_RESEARCH=set()
RESEARCH_LOCK=threading.Lock()
# Explicit frontend asset allowlist; private files remain inaccessible.
STATIC.update({
    'assets/kazakhtelecom-logo.svg','distingt-public.css','distingt-usability.css',
    'assets/favicon.svg','assets/favicon-16x16.png','assets/favicon-32x32.png','assets/apple-touch-icon.png',
    'i18n.js', 'ayqyn.js', 'ayqyn.css', 'demo-sources.js', 'demo.js','report.js','workspace.js','workspace.css','distingt-approved.css','distingt-integration.css','case-store.js','agent-model.js','demo-agent.js',
    'assets/ayqyn-mark.svg', 'assets/c010/demo.json',
    'assets/c010/inputs/C010/before/org.pdf', 'assets/c010/inputs/C010/before/functions.pdf',
    'assets/c010/inputs/C010/after/org.pdf', 'assets/c010/inputs/C010/after/functions.pdf',
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
        raise ValueError('Нужен DOCX с именем и данными файла.')
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
            started = perf_counter()
            trace = []
            def event(stage, count):
                trace.append({'stage': stage, 'count': count, 'elapsed_ms': round((perf_counter()-started)*1000)})
            documents = []
            classification_warning = ''
            classification_usage = {}
            if 'documents' in data:
                packet = data['documents']
                if not isinstance(packet, list) or not 2 <= len(packet) <= MAX_DOCUMENTS:
                    raise ValueError('Загрузите от 2 до 20 документов DOCX.')
                if any(not isinstance(item,dict) or not isinstance(item.get('data'),str) for item in packet):
                    raise ValueError('Некорректные данные документа в пакете.')
                if sum(len(item['data'])*3//4 - (len(item['data'])-len(item['data'].rstrip('='))) for item in packet) > 20_000_000:
                    raise ValueError('Общий размер пакета — до 20 МБ.')
                documents = [decode_document(item) for item in packet]
                event('traceExtract', len(documents))
                classify_documents(documents, packet)
                if data.get('useAI') and any(doc['side'] is None for doc in documents):
                    config = data.get('config') or {}
                    if not isinstance(config,dict): raise ValueError('Некорректные настройки модели.')
                    try:
                        classification_usage = classify_with_model(documents, config)
                    except ValueError as exc:
                        classification_warning = str(exc)
                manifest = [{k: doc.get(k) for k in ('id','name','sha256','side','classification','revision','classification_quote','classification_reason')} for doc in documents]
                unresolved = any(doc['side'] is None for doc in documents)
                sides = {doc['side'] for doc in documents}
                if unresolved or not {'before','after'} <= sides:
                    return self.send_json(200, {'needs_review': True, 'documents': manifest, 'classification_warning': classification_warning})
                event('traceClassify', len(documents))
                before, after = combine_documents(documents, 'before'), combine_documents(documents, 'after')
            else:
                before, after = decode_document(data.get('before')), decode_document(data.get('after'))
                event('traceExtract', 2)
            findings = analyze_rules(before,after)
            for item in findings:
                item['method']='rules'
                item['reviewed']=False
            event('traceRules', len(findings))
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
                    event('traceModel', len(ai))
                    if rejected: warnings.append(f'Отброшено выводов с некорректными источниками: {rejected}.')
                    if not ai: warnings.append('Модель не вернула допустимых находок. Это не доказывает отсутствие рисков.')
                except ValueError as exc:
                    warnings.append(str(exc))
                    mode='fallback'
            if before['sha256']==after['sha256']: warnings.append('Загружены одинаковые файлы. Внутренние пересечения всё ещё могут присутствовать.')
            event('traceSources', sum(len(f['before_ids'])+len(f['after_ids']) for f in findings))
            self.send_json(200,{'before':before,'after':after,'documents':documents,'trace':trace,'findings':findings,'mode':mode,'warnings':warnings,'usage':usage,'classification_usage':classification_usage})
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
