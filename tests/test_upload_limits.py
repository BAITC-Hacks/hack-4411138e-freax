import base64
import io
import json
import threading
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ayqyn.api import server
from test_analyzer import docx, para


class UploadLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.http.server_port}/api/analyze'

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()

    def post(self, documents):
        body = json.dumps({'documents': documents, 'useAI': False}).encode()
        request = Request(self.url, body, {'Content-Type': 'application/json'})
        with urlopen(request, timeout=60) as response:
            return json.load(response)

    def test_exactly_100mb_docx_passes_http_decode_and_parser(self):
        # A valid stored ZIP models a short policy with a large media attachment.
        # No fixture is written to disk and no model is called.
        xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + para('Отдел проверяет резервное питание узлов сети.') + '</w:body></w:document>'
        def archive(padding):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_STORED) as z:
                z.writestr('word/document.xml', xml)
                z.writestr('word/media/attachment.bin', bytes(padding))
            return stream.getvalue()
        raw = archive(100_000_000 - len(archive(0)))
        self.assertEqual(len(raw), 100_000_000)
        documents = [
            {'name': 'before.docx', 'side': 'before', 'data': base64.b64encode(raw).decode()},
            {'name': 'after.docx', 'side': 'after', 'data': base64.b64encode(docx(para('Общие положения.'))).decode()},
        ]
        del raw
        result = self.post(documents)
        self.assertEqual(result['mode'], 'rules')
        self.assertEqual(len(result['documents']), 2)
        self.assertEqual(result['before']['paragraphs'][0]['text'], 'Отдел проверяет резервное питание узлов сети.')

    def test_decoded_size_rejects_one_byte_over_limit(self):
        # 8 and 9 bytes have the same padded base64 length: decoded checking matters.
        with patch.object(server, 'MAX_UPLOAD_BYTES', 8), patch.object(server, 'MAX_ENCODED_FILE_BYTES', 12), patch('ayqyn.api.server.parse_docx') as parser:
            with self.assertRaisesRegex(ValueError, '100 МБ'):
                server.decode_document({'name': 'large.docx', 'data': base64.b64encode(b'123456789').decode()})
            parser.assert_not_called()

    def test_total_packet_limit_is_enforced_before_parsing(self):
        documents = [{'name': name, 'side': side, 'data': base64.b64encode(docx(para('Текст'))).decode()}
                     for name, side in [('before.docx', 'before'), ('after.docx', 'after')]]
        with patch.object(server, 'MAX_PACKET_BYTES', 1), patch('ayqyn.api.server.parse_docx') as parser:
            with self.assertRaises(HTTPError) as raised:
                self.post(documents)
            self.assertEqual(raised.exception.code, 400)
            self.assertIn('200 МБ', json.load(raised.exception)['error'])
            parser.assert_not_called()


if __name__ == '__main__':
    unittest.main()
