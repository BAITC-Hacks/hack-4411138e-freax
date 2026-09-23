"""OCR observations remain separate from source evidence and read coverage."""
import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ayqyn.agent.context import compact_messages
from ayqyn.agent.runner import DEFAULT_BUDGET, public_result
from ayqyn.agent.state import ResearchState
from ayqyn.agent.tools import ResearchTools
from ayqyn.documents.packets import read_packet
from ayqyn.documents.store import DocumentStore
from test_pdf_input import pdf
from test_research import FakeIndex


class OcrToolTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.raw=pdf([[]],image_only=True)
        packet=read_packet([{'name':'scan.pdf','data':base64.b64encode(self.raw).decode(),
                             'role':'before'}],mode='manual')
        self.state=ResearchState(Path(self.temp.name)/'research',packet,'Inspect scan',DEFAULT_BUDGET)
        self.store=DocumentStore(packet)
        self.tools=ResearchTools(self.state,self.store,FakeIndex(self.store))
        self.doc=packet['documents'][0]
        folder=self.state.path/'originals';folder.mkdir()
        self.original=folder/(self.doc['sha256']+'.pdf');self.original.write_bytes(self.raw)
        self.args={'document_id':self.doc['id'],'page':1}

    def test_recognition_is_cached_durable_and_not_canonical_evidence(self):
        coverage=self.store.get_coverage()
        with patch('ayqyn.documents.ocr.recognize_page',return_value={
                'status':'success','engine':'rapidocr','text':'Recognized duty, potentially inaccurate.','truncated':False}) as engine:
            first=self.tools.execute('ocr_page',self.args)
            second=self.tools.execute('ocr_page',self.args)
        self.assertEqual(engine.call_count,1)
        self.assertFalse(first['verified']);self.assertTrue(second['cached'])
        self.assertEqual(self.store.get_coverage(),coverage)
        self.assertFalse(self.store.check_evidence(first['ocr_id'],first['text'])['exists'])
        self.state.save();loaded=ResearchState(self.state.path)
        self.assertEqual(loaded.data['ocr_pages'][first['ocr_id']]['text'],first['text'])
        self.assertFalse(public_result(loaded)['ocr_pages'][0]['verified'])
        self.assertIn(first['ocr_id'],str(compact_messages(loaded,self.store)))

    def test_foreign_id_and_changed_original_are_rejected_before_engine(self):
        with patch('ayqyn.documents.ocr.recognize_page',side_effect=AssertionError('Must not run.')):
            with self.assertRaisesRegex(ValueError,'current packet'):
                self.tools.execute('ocr_page',{'document_id':'foreign','page':1})
            self.original.write_bytes(b'%PDF changed')
            with self.assertRaisesRegex(ValueError,'hash'):
                self.tools.execute('ocr_page',self.args)

    def test_unavailable_engine_is_explicit_and_never_saved_as_evidence(self):
        with patch('ayqyn.documents.ocr.recognize_page',return_value={
                'status':'unavailable','error':'Local OCR engine is not installed.'}):
            result=self.tools.execute('ocr_page',self.args)
        self.assertEqual(result['status'],'unavailable')
        self.assertFalse(self.state.data['ocr_pages'])
        self.assertFalse(self.store.read_ids)

    def test_ocr_uses_remaining_time_and_stops_at_zero(self):
        self.state.data['budget']['elapsed_seconds']=235
        with patch('ayqyn.documents.ocr.recognize_page',return_value={'status':'error','error':'Timeout'}) as engine:
            self.tools.execute('ocr_page',self.args)
            self.assertEqual(engine.call_args.kwargs['timeout_seconds'],5)
            self.state.data['budget']['elapsed_seconds']=240
            self.assertEqual(self.tools.execute('ocr_page',self.args)['status'],'budget_exhausted')
            self.assertEqual(engine.call_count,1)

    def test_page_schema_and_research_limit_prevent_extra_recognition(self):
        with patch('ayqyn.documents.ocr.recognize_page',side_effect=AssertionError('Must not run.')):
            for page in [0,201,True]:
                with self.assertRaises(ValueError):self.tools.execute('ocr_page',{**self.args,'page':page})
            self.state.data['ocr_pages']={str(n):{} for n in range(4)}
            self.assertEqual(self.tools.execute('ocr_page',self.args)['status'],'limit_reached')


if __name__=='__main__':unittest.main()
