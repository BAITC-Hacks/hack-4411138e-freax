"""OCR -> persisted sources -> real retrieval -> read -> accepted partial finding."""
import base64
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ayqyn.agent.runner import DEFAULT_BUDGET
from ayqyn.agent.state import ResearchState
from ayqyn.agent.tools import ResearchTools
from ayqyn.api.workspace import workspace_result
from ayqyn.documents.packets import read_packet
from ayqyn.documents.store import DocumentStore
from ayqyn.retrieval.hybrid import HybridIndex
from test_pdf_input import pdf
from test_packets import upload


class OcrSourceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        raw=pdf([['1. New department rules.']],image_only=True)
        packet=read_packet([upload(['БВА контролирует исполнение договоров.'],name='old.docx',role='before'),
            {'name':'scan.pdf','data':base64.b64encode(raw).decode(),'role':'after'}],mode='manual')
        self.state=ResearchState(Path(temp.name)/'research',packet,'Compare duties',DEFAULT_BUDGET)
        self.store=DocumentStore(self.state.packet)
        self.doc=next(d for d in self.state.packet['documents'] if d['format']=='pdf')
        originals=self.state.path/'originals'; originals.mkdir()
        (originals/(self.doc['sha256']+'.pdf')).write_bytes(raw)
        self.embedded=[]
        def embed(texts):
            self.embedded.extend(texts)
            return [[1.,float('контролирует' in t)+1] for t in texts]
        self.embed=embed
        self.index=HybridIndex(self.store,self.state.path/'index',{},embedder=embed)
        self.index.build()
        self.tools=ResearchTools(self.state,self.store,self.index)
        self.observation={'status':'success','engine':'rapidocr','text':'Сектор контролирует исполнение договоров.',
            'lines':[{'text':'Сектор контролирует исполнение договоров.','confidence':.71,
                      'box':[[0,0],[250,0],[250,30],[0,30]]}],
            'truncated':False,'coordinate_space':'render_pixels_top_left','render_size':[600,800],
            'page_size_points':[300,400]}

    def recognize(self):
        with patch('ayqyn.documents.ocr.recognize_page',return_value=deepcopy(self.observation)):
            return self.tools.execute('ocr_page',{'document_id':self.doc['id'],'page':1})

    def test_full_source_search_read_citation_reload_path(self):
        before_count=len(self.embedded)
        result=self.recognize(); key=result['fragment_ids'][0]
        self.assertEqual(result['index_status'],'hybrid')
        self.assertEqual(len(self.embedded)-before_count,1)  # Native vectors reused.
        self.assertNotIn(key,self.store.read_ids)
        hits=self.tools.execute('search',{'query':'Сектор контролирует','role':'after','document_id':None,'limit':5})['hits']
        self.assertEqual(hits[0]['id'],key); self.assertEqual(hits[0]['source'],'ocr')
        page=self.tools.execute('read_context',{'fragment_id':key,'scope':'section'})
        source=next(p for p in page['fragments'] if p['id']==key)
        self.assertEqual(source['box'],self.observation['lines'][0]['box'])
        self.assertFalse(source['verified']); self.assertTrue(source['low_confidence'])
        old=next(p for p in self.store.fragments.values() if self.store.documents[p['document_id']]['role']=='before')
        self.store.read_context(old['id'])
        finding={'group':'function','category':'changed','function':'Контроль исполнения договоров',
            'owner_before':'БВА','owner_after':'Сектор','before_evidence':[{'fragment_id':old['id'],'quote':old['text']}],
            'after_evidence':[{'fragment_id':key,'quote':source['text']}],
            'explanation':'Изменилось явное назначение.','limitations':['Проверить скан.']}
        bad=deepcopy(finding);bad['after_evidence'][0]['quote']='Выдуманный текст обязанности'
        self.assertFalse(self.state.submit(self.store,[bad],'insufficient_data',[],'Partial')['accepted'])
        accepted=self.state.submit(self.store,[finding],'insufficient_data',['Скан требует проверки.'],'Partial')
        self.assertTrue(accepted['accepted'],accepted)
        self.assertEqual(self.state.data['findings'][0]['evidence_validation'],'ocr_transcription_quotes_matched')
        self.assertTrue(any('OCR' in s for s in self.state.data['findings'][0]['limitations']))
        self.assertFalse(self.store.get_coverage()['after_fully_read'])
        self.state.data['read_ids']=list(self.store.read_ids); self.state.save()
        loaded=ResearchState(self.state.path); reloaded=DocumentStore(loaded.packet)
        reloaded.read_ids=set(loaded.data['read_ids'])
        self.assertTrue(reloaded.check_evidence(key,source['text'])['was_read'])
        cached=HybridIndex(reloaded,self.state.path/'index',{},embedder=lambda _:self.fail('Cache should be reused'))
        self.assertTrue(cached.build()['cache_hit'])
        self.assertTrue(any(p['id']==key for d in workspace_result(loaded)['documents'] for p in d['paragraphs']))

    def test_cached_repeat_has_stable_ids_and_no_duplicates_or_embedding_calls(self):
        first=self.recognize(); count=len(self.embedded); total=len(self.store.fragments)
        with patch('ayqyn.documents.ocr.recognize_page',side_effect=AssertionError('Cached')):
            second=self.tools.execute('ocr_page',{'document_id':self.doc['id'],'page':1})
        self.assertEqual(first['fragment_ids'],second['fragment_ids']);self.assertTrue(second['cached'])
        self.assertEqual(len(self.store.fragments),total);self.assertEqual(len(self.embedded),count)
        self.assertEqual(len(self.state.data['candidates']),1)
        self.assertEqual(len(self.state.data['research_tasks']),1)

    def test_failed_embedding_keeps_sources_with_explicit_lexical_fallback(self):
        with patch.object(self.index,'refresh',side_effect=ValueError('Unavailable')):
            result=self.recognize()
        key=result['fragment_ids'][0]
        self.assertEqual(result['index_status'],'lexical_fallback')
        reply=self.tools.execute('search',{'query':'Сектор','role':'after','document_id':None,'limit':5})
        self.assertEqual(reply['method'],'lexical');self.assertEqual(reply['hits'][0]['id'],key)
        self.assertIn(key,DocumentStore(ResearchState(self.state.path).packet).fragments)

    def test_truncation_and_missing_geometry_never_become_complete_read(self):
        self.observation['truncated']=True
        key=self.recognize()['fragment_ids'][0]
        self.store.read_context(key)
        self.assertTrue(self.store.fragments[key]['truncated'])
        self.assertFalse(self.store.get_coverage()['after_fully_read'])
        self.observation.pop('render_size')
        from ayqyn.documents.ocr_sources import fragments_from_ocr
        with self.assertRaisesRegex(ValueError,'coordinates'):
            fragments_from_ocr(self.doc,{**self.observation,'page':1,'document_id':self.doc['id'],'sha256':self.doc['sha256']})
