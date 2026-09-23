"""Local evidence for an actual provider request; never stores auth headers."""
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def new_run_path():
    return ROOT / 'output' / 'runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8])


class RunRecord:
    def __init__(self, path, before, after, base, body, secret=''):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=False)
        self.secret = secret
        self.started = time.perf_counter()
        try:
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, stderr=subprocess.DEVNULL, timeout=5).decode().strip()
        except (OSError, subprocess.SubprocessError):
            commit = None
        code_files = ['llm.py','analyzer.py','server.py','run_record.py','function_analysis.py','scripts/run_analysis.py',
                      'packets.py','pdf_input.py','document_store.py','hybrid_search.py','embeddings.py',
                      'research_state.py','research_tools.py','research_agent.py','scripts/run_research.py']
        self.meta = {
            'run_id': self.path.name, 'started_at': utc_now(), 'finished_at': None,
            'status': 'request_prepared', 'provider_base': base, 'requested_model': body['model'],
            'returned_model': None, 'response_id': None, 'finish_reason': None,
            'truncated': None, 'response_received': False, 'duration_seconds': None,
            'parameters': {k: v for k, v in body.items() if k != 'messages'},
            'input_files': [{'name': d['name'], 'sha256': d.get('sha256'), 'paragraphs': len(d['paragraphs'])} for d in (before, after)],
            'git_commit': commit,
            'code_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in code_files if (ROOT / name).exists()},
            'request_sha256': hashlib.sha256(json.dumps(body).encode('utf-8')).hexdigest(),
            'secret_redacted': False, 'error': None,
        }
        self.write_json('request.json', body)
        self.write_json('inputs.json', {'before': before, 'after': after})
        self.write_json('manifest.json', self.meta)

    def write_bytes(self, name, data):
        if self.secret:
            secret = self.secret.encode('utf-8')
            if secret in data:
                data = data.replace(secret, b'[REDACTED]')
                self.meta['secret_redacted'] = True
        (self.path / name).write_bytes(data)

    def write_json(self, name, value):
        self.write_bytes(name, json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8'))

    def received(self, raw):
        self.meta['response_received'] = True
        self.meta['response_sha256'] = hashlib.sha256(raw).hexdigest()
        self.write_bytes('response.raw.json', raw)
        try:
            response = json.loads(raw)
            choice = response['choices'][0]
            self.meta.update(returned_model=response.get('model'), response_id=response.get('id'),
                             finish_reason=choice.get('finish_reason'),
                             truncated=choice.get('finish_reason') == 'length', usage=response.get('usage'))
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            pass

    def finish(self, error=None, accepted=None, rejected=None):
        self.meta.update(finished_at=utc_now(), duration_seconds=round(time.perf_counter() - self.started, 3),
                         status='failed' if error else 'completed', error=error,
                         accepted_count=accepted, rejected_count=rejected)
        self.write_json('manifest.json', self.meta)
