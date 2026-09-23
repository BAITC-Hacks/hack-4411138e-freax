import base64
import json
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from server import Handler
from test_analyzer import docx, para


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def payload(self):
        texts=[['3.4. Структура','Отдел планирования',
                'Отдел осуществляет мониторинг исполнения государственных программ.'],
               ['3.4. Структура','Отдел планирования','Отдел учета','4.1. Функции',
                'Отдел А обеспечивает подготовку ежегодных отчетов о выполнении программ.',
                'Отдел Б обеспечивает подготовку ежегодных отчетов о выполнении программ.']]
        return {side:{'name':side+'.docx','data':base64.b64encode(docx(''.join(para(t) for t in text))).decode()} for side,text in zip(('before','after'),texts)}

    def post(self,payload,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        request=Request(self.base+'/api/analyze',data=json.dumps(payload).encode(),headers=headers)
        with urlopen(request,timeout=10) as response:return json.load(response)

    def test_arbitrary_docx_three_types_and_source_integrity(self):
        result=self.post(self.payload())
        self.assertEqual(result['mode'],'rules')
        self.assertTrue({'department_added','function_loss','duplication'} <= {f['type'] for f in result['findings']})
        for f in result['findings']:
            for side in ('before','after'):
                self.assertTrue(set(f[side+'_ids']) <= {p['id'] for p in result[side]['paragraphs']})

    def test_model_failure_is_explicit_fallback(self):
        data=self.payload();data['useAI']=True
        with patch('server.compare_with_model',side_effect=ValueError('Модель вернула пустой ответ.')):
            result=self.post(data)
        self.assertEqual(result['mode'],'fallback')
        self.assertTrue(result['warnings'])
        self.assertTrue(result['findings'])

    def test_valid_model_proposal_path(self):
        data=self.payload();data['useAI']=True
        candidate={'id':'ai-1','type':'function_loss','title':'test','before_ids':['p3'],'after_ids':[],
                   'status':'risk','explanation':'test','method':'llm','reviewed':False}
        with patch('server.compare_with_model',return_value=([candidate],0,{})):
            result=self.post(data)
        self.assertEqual(result['mode'],'ai')
        self.assertIn(candidate,result['findings'])

    def test_invalid_docx_is_recoverable(self):
        data=self.payload();data['before']['data']=base64.b64encode(b'not a zip').decode()
        with self.assertRaises(HTTPError) as raised:self.post(data)
        self.assertEqual(raised.exception.code,400)
        self.assertTrue(self.post(self.payload())['findings'])

    def test_cross_origin_request_rejected(self):
        with self.assertRaises(HTTPError) as raised:self.post(self.payload(),'https://example.org')
        self.assertEqual(raised.exception.code,403)

    def test_frontend_modules_and_original_logo_are_served(self):
        from server import STATIC, ROOT
        paths = [p for p in STATIC if p.endswith(('.mjs', '.svg'))]
        paths += ['i18n.js', 'icons.js', 'preferences.js', 'analysis.js']
        for path in paths:
            with self.subTest(path=path), urlopen(self.base + '/' + path) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), (ROOT / path).read_bytes())
                self.assertNotIn('application/octet-stream', response.headers['Content-Type'])

    def test_vendor_paths_cannot_escape_allowlist(self):
        for path in ['/vendor/lucide/../../server.py', '/vendor/README.md', '/assets/../.env']:
            with self.subTest(path=path), self.assertRaises(HTTPError) as raised:
                urlopen(self.base + path)
            self.assertEqual(raised.exception.code, 404)

    def test_private_source_files_not_served(self):
        for path in ['/server.py','/.env','/.git/config']:
            with self.subTest(path=path),self.assertRaises(HTTPError) as raised:urlopen(self.base+path)
            self.assertEqual(raised.exception.code,404)


if __name__=='__main__':unittest.main()
