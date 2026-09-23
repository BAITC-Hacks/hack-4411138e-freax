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
from urllib.parse import urlparse, unquote, parse_qs, quote
from ayqyn.documents.analyzer import parse_docx, analyze_rules
from ayqyn.providers.llm import compare_with_model, classify_with_model
from ayqyn.storage.runs import new_run_path
from ayqyn.documents.packets import read_packet
from ayqyn.agent.runner import prepare_research,restore_research,run_research,public_result
from ayqyn.agent.state import ResearchState
from ayqyn.api.workspace import workspace_result,progress_result
from ayqyn.analysis.batch import MAX_DOCUMENTS, classify_documents, combine_documents
from time import perf_counter

from ayqyn.paths import ROOT
RESEARCH_ROOT=ROOT/'output'/'research'
ACTIVE_RESEARCH=set()
RESEARCH_LOCK=threading.Lock()


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
        path = unquote(urlparse(self.path).path).lstrip('/')
        if path in {'', 'api/health'}:
            return self.send_json(200, {'service':'AYQYN', 'status':'ok', 'frontend':False})
        if path=='api/config':
            return self.send_json(200, {'hasKey':bool(os.getenv('OPENAI_API_KEY')), 'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),
                                        'base':os.getenv('OPENAI_BASE_URL','https://api.openai.com/v1')})
        if path.startswith('api/research/'):
            try:
                state=ResearchState(research_path(path.removeprefix('api/research/')))
                view=parse_qs(urlparse(self.path).query).get('view',[''])[0]
                if view=='original':
                    identifier=parse_qs(urlparse(self.path).query).get('document',[''])[0]
                    doc=next((d for d in state.packet['documents'] if d['id']==identifier),None)
                    if not doc or not re.fullmatch(r'[a-f0-9]{64}',doc.get('sha256') or '') or doc['format'] not in {'docx','pdf','xlsx'}:
                        raise ValueError('Document not in this research.')
                    data=(state.path/'originals'/(doc['sha256']+'.'+doc['format'])).read_bytes()
                    self.send_response(200)
                    self.send_header('Content-Type','application/octet-stream')
                    self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(doc['name'],safe=''))
                    self.send_header('Content-Length',str(len(data)))
                    self.send_header('Cache-Control','no-store')
                    self.send_header('X-Content-Type-Options','nosniff')
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if view=='workspace': return self.send_json(200,workspace_result(state))
                if view=='progress': return self.send_json(200,progress_result(state))
                return self.send_json(200,public_result(state))
            except (ValueError,OSError):
                return self.send_json(404,{'error':'Исследование не найдено.'})
        candidate = (ROOT/path).resolve()
        source = candidate.parent == (ROOT/'sources').resolve() and candidate.suffix=='.docx'
        if not (source and candidate.is_file() and candidate.is_relative_to(ROOT)):
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
                if data.get('classifyOnly') is True:
                    return self.send_json(200,{'needs_review':False,'documents':manifest,'classification_warning':classification_warning})
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


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'http://127.0.0.1:{server.server_port}',flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
