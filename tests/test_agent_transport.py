import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from ayqyn.providers.llm import agent_turn,request_json_api
from ayqyn.agent.tools import TOOL_SCHEMAS
from test_llm import BEFORE,AFTER


class AgentTransportTests(unittest.TestCase):
    def test_native_tool_call_protocol_and_capture(self):
        response={'model':'model-snapshot','choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,
            'tool_calls':[{'id':'call1','type':'function','function':{'name':'list_documents','arguments':'{}'}}]}}],
            'usage':{'total_tokens':22}}
        with tempfile.TemporaryDirectory() as temp,patch('urllib.request.urlopen') as call:
            call.return_value.__enter__.return_value.read.return_value=json.dumps(response).encode()
            message,usage=agent_turn([{'role':'user','content':'Compare'}],TOOL_SCHEMAS,
                {'base':'http://127.0.0.1:11434/v1','model':'test'},BEFORE,AFTER,run_dir=Path(temp)/'turn')
            body=json.loads(call.call_args.args[0].data)
            self.assertEqual(body['tool_choice'],'required')
            self.assertFalse(body['parallel_tool_calls'])
            self.assertNotIn('response_format',body)
            self.assertEqual(message['tool_calls'][0]['function']['name'],'list_documents')
            manifest=json.loads((Path(temp)/'turn'/'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['finish_reason'],'tool_calls')
            self.assertEqual(manifest['returned_model'],'model-snapshot')
            self.assertEqual(usage['total_tokens'],22)

    def test_truncated_actions_are_not_executed(self):
        response={'choices':[{'finish_reason':'length','message':{'role':'assistant','content':None,'tool_calls':[]}}]}
        with tempfile.TemporaryDirectory() as temp,patch('urllib.request.urlopen') as call:
            call.return_value.__enter__.return_value.read.return_value=json.dumps(response).encode()
            with self.assertRaises(ValueError):
                agent_turn([],TOOL_SCHEMAS,{'base':'http://localhost:1234/v1','model':'test'},BEFORE,AFTER,run_dir=Path(temp)/'turn')
            self.assertEqual(json.loads((Path(temp)/'turn'/'manifest.json').read_text(encoding='utf-8'))['status'],'failed')

    def test_embeddings_do_not_inherit_key_for_another_base(self):
        with patch.dict('os.environ',{'OPENAI_API_KEY':'private-key','OPENAI_BASE_URL':'https://api.openai.com/v1'}),patch('urllib.request.urlopen') as call:
            call.return_value.__enter__.return_value.read.return_value=b'{"data": []}'
            request_json_api({'base':'http://localhost:1234/v1'},'/embeddings',{'model':'local-embedding','input':['text']})
            self.assertNotIn('Authorization',call.call_args.args[0].headers)


if __name__=='__main__': unittest.main()
