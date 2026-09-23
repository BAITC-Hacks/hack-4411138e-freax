import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ayqyn.providers.llm import compare_with_model

DOC = {'name':'test.docx','sha256':'test-hash','paragraphs':[{'id':'p1','section':'1','text':'Function'}]}


class RunRecordTests(unittest.TestCase):
    def call(self, response, path):
        with patch('urllib.request.urlopen') as request:
            request.return_value.__enter__.return_value.read.return_value = response
            return compare_with_model(DOC, DOC, {'base':'https://api.openai.com/v1', 'model':'test', 'key':'test-secret-key'}, run_dir=path)

    def test_actual_request_and_raw_response_are_recorded_without_key(self):
        raw = json.dumps({'id':'run-test','model':'returned-model','choices':[{'finish_reason':'stop','message':{'content':'{"findings":[]}'}}]}).encode()
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'mock-run'
            self.call(raw, path)
            manifest = json.loads((path/'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['status'], 'completed')
            self.assertEqual(manifest['returned_model'], 'returned-model')
            self.assertFalse(manifest['truncated'])
            self.assertEqual((path/'response.raw.json').read_bytes(), raw)
            self.assertIn('ayqyn/providers/llm.py', manifest['code_sha256'])
            for file in path.iterdir():
                self.assertNotIn(b'test-secret-key', file.read_bytes())

    def test_truncation_retains_failed_response(self):
        raw = b'{"choices":[{"finish_reason":"length","message":{"content":"incomplete"}}]}'
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'mock-run'
            with self.assertRaises(ValueError): self.call(raw, path)
            manifest = json.loads((path/'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['status'], 'failed')
            self.assertTrue(manifest['truncated'])
            self.assertEqual((path/'response.raw.json').read_bytes(), raw)

    def test_accidentally_echoed_key_is_redacted(self):
        raw = b'{"model":"test-secret-key","choices":[{"finish_reason":"stop","message":{"content":"{\\"findings\\":[]}"}}]}'
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'mock-run'
            self.call(raw,path)
            self.assertTrue(json.loads((path/'manifest.json').read_text())['secret_redacted'])
            for file in path.iterdir(): self.assertNotIn(b'test-secret-key',file.read_bytes())
