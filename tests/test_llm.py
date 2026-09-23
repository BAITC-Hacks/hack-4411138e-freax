import json
import unittest
from unittest.mock import patch
from ayqyn.providers.llm import validate_findings, compare_with_model

BEFORE={'name':'before.docx','paragraphs':[{'id':'p1','text':'Function','section':'1'}]}
AFTER={'name':'after.docx','paragraphs':[{'id':'p1','text':'Function A','section':'1'},{'id':'p2','text':'Function B','section':'2'}]}


def finding(**overrides):
    result={'type':'function_loss','title':'Possible loss','before_ids':['p1'],'after_ids':[], 'explanation':'Check other documents.'}
    result.update(overrides)
    return result


class GroundingTests(unittest.TestCase):
    def test_server_key_is_not_sent_to_another_provider(self):
        response={'choices':[{'finish_reason':'stop','message':{'content':'{"findings":[]}'}}]}
        with patch.dict('os.environ',{'OPENAI_API_KEY':'private-key','OPENAI_BASE_URL':'https://api.openai.com/v1'}),patch('urllib.request.urlopen') as request:
            request.return_value.__enter__.return_value.read.return_value=json.dumps(response).encode()
            compare_with_model(BEFORE,AFTER,{'base':'http://127.0.0.1:11434/v1','model':'local'})
            self.assertNotIn('Authorization',request.call_args.args[0].headers)

    def test_nonexistent_evidence_is_rejected(self):
        accepted,rejected=validate_findings({'findings':[finding(before_ids=['p999'])]},BEFORE,AFTER)
        self.assertEqual((accepted,rejected),([],1))

    def test_duplicate_citations_are_not_two_independent_sources(self):
        accepted,rejected=validate_findings({'findings':[finding(type='duplication',after_ids=['p1','p1'])]},BEFORE,AFTER)
        self.assertEqual((accepted,rejected),([],1))

    def test_valid_candidates_are_never_auto_confirmed(self):
        accepted,rejected=validate_findings({'findings':[finding(status='confirmed')]},BEFORE,AFTER)
        self.assertEqual(rejected,0)
        self.assertEqual(accepted[0]['status'],'risk')
        self.assertFalse(accepted[0]['reviewed'])

    def test_missing_before_rejects_loss(self):
        accepted,rejected=validate_findings({'findings':[finding(before_ids=[],after_ids=['p1'])]},BEFORE,AFTER)
        self.assertEqual((accepted,rejected),([],1))

    def test_truncated_and_empty_provider_responses_fail(self):
        for response in [{'choices':[]},{'choices':[None]},{'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}, {'choices':[{'finish_reason':'stop','message':{'content':''}}]}]:
            with self.subTest(response=response),patch('urllib.request.urlopen') as request:
                request.return_value.__enter__.return_value.read.return_value=json.dumps(response).encode()
                with self.assertRaises(ValueError):compare_with_model(BEFORE,AFTER,{'base':'http://127.0.0.1:11434/v1','model':'test'})

    def test_valid_provider_response(self):
        response={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'findings':[finding()]})}}],'usage':{'total_tokens':42}}
        with patch('urllib.request.urlopen') as request:
            request.return_value.__enter__.return_value.read.return_value=json.dumps(response).encode()
            accepted,rejected,usage=compare_with_model(BEFORE,AFTER,{'base':'http://127.0.0.1:11434/v1','model':'test'})
            self.assertEqual(len(accepted),1)
            self.assertEqual(rejected,0)
            self.assertEqual(usage['total_tokens'],42)


if __name__=='__main__':unittest.main()
