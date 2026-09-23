"""Context cost, pagination and coverage invariants, independent of LLM quality."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from ayqyn.documents.store import DocumentStore,ContextLimitError
from ayqyn.documents.packets import read_packet
from ayqyn.agent.context import compact_messages
from ayqyn.agent.inventory import build_inventory,inventory_summary,update_candidates
from ayqyn.agent.state import ResearchState
from ayqyn.agent.runner import DEFAULT_BUDGET
from ayqyn.agent.tools import ResearchTools
from test_research import FakeIndex
from test_packets import upload


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        packet=read_packet([upload(['1. Team Alpha:']+[f'1.{i}. Reviews contracts type {i}. '+('Evidence. '*30) for i in range(1,81)],name='old.docx',role='before'),
                            upload(['1. Team Beta:']+[f'1.{i}. Reviews contracts type {i}. '+('Evidence. '*30) for i in range(1,81)],name='new.docx',role='after')],mode='manual')
        self.state=ResearchState(Path(self.temp.name)/'research',packet,'Compare functions',DEFAULT_BUDGET)
        self.store=DocumentStore(packet)
        self.state.data.update(candidates=build_inventory(self.store),research_policy=2)
        self.tools=ResearchTools(self.state,self.store,FakeIndex(self.store))

    def test_document_and_large_section_are_paged_without_false_coverage(self):
        doc=next(iter(self.store.documents.values()))
        for scope in ['document','section']:
            self.store.read_ids.clear()
            offset=0;seen=[]
            while True:
                result=self.store.read_context_page(doc['paragraphs'][0]['id'],scope,offset)
                self.assertLessEqual(len(json.dumps(result,ensure_ascii=False)),18000)
                ids=[p['id'] for p in result['fragments']]
                seen+=ids
                self.assertEqual(self.store.read_ids,set(seen))
                if offset==0:
                    self.assertTrue(result['truncated'])
                    self.assertFalse(self.store.get_coverage()['documents'][0]['fully_read'])
                for p in result['fragments']:
                    self.assertEqual(p['text'],self.store.fragments[p['id']]['text'])
                offset=result['next_offset']
                if offset is None:break
            self.assertEqual(seen,[p['id'] for p in doc['paragraphs']])
            self.assertEqual(len(seen),len(set(seen)))

    def test_oversized_fragment_does_not_mark_read(self):
        p=next(iter(self.store.fragments.values()))
        with self.assertRaises(ContextLimitError): self.store.read_context_page(p['id'],limit_chars=40)
        self.assertFalse(self.store.read_ids)

    def test_reading_everything_does_not_verify_candidates(self):
        for doc in self.store.documents.values():self.store.read_context(doc['paragraphs'][0]['id'],'document')
        result=self.state.submit(self.store,[],'completed',[],'All text was returned.')
        self.assertFalse(result['accepted'])
        self.assertTrue(self.state.submit(self.store,[],'insufficient_data',['Candidates not checked.'],'Partial review.')['accepted'])

    def test_changed_parent_prevents_automatic_text_equivalence(self):
        self.assertEqual(inventory_summary(self.state)['text_match_candidates'],0)

    def test_candidate_requires_read_continuations_and_real_evidence(self):
        candidate=next(iter(self.state.data['candidates'].values()))
        p=self.store.fragments[candidate['fragment_ids'][0]]
        update={'candidate_id':candidate['id'],'status':'reviewed','summary':'Read this unit, not all duties.',
                'evidence':[{'fragment_id':p['id'],'quote':p['text']}]}
        self.assertFalse(update_candidates(self.state,self.store,[update])['accepted'])
        self.store.read_context_page(p['id'])
        self.assertTrue(update_candidates(self.state,self.store,[update])['accepted'])
        self.state.save()
        self.assertEqual(ResearchState(self.state.path).data['candidates'][candidate['id']]['status'],'reviewed')

    def test_compaction_keeps_native_pairs_and_full_archive(self):
        history=[{'role':'system','content':'policy'},{'role':'user','content':'task'}]
        for n in range(12):
            history+=[{'role':'assistant','tool_calls':[{'id':str(n),'type':'function','function':{'name':'read_context','arguments':'{}'}}]},
                      {'role':'tool','tool_call_id':str(n),'content':json.dumps({'text':'x'*17000})}]
        self.state.data['messages']=history
        original=copy.deepcopy(history)
        messages=compact_messages(self.state,self.store)
        self.assertLess(len(json.dumps(messages)),70000)
        self.assertEqual(history,original)
        calls={c['id'] for m in messages for c in m.get('tool_calls',[])}
        replies={m['tool_call_id'] for m in messages if m['role']=='tool'}
        self.assertEqual(calls,replies)
        self.assertEqual(len(calls),3)

    def test_coverage_does_not_return_full_metadata_or_search_results(self):
        coverage=self.tools.execute('get_coverage',{'offset':0})
        self.assertNotIn('sections',coverage['documents'][0])
        self.assertNotIn('searches',coverage)
        self.assertLess(len(json.dumps(coverage)),16000)

    def test_exclusive_transfer_requires_both_alternative_checks(self):
        old,new=[d['paragraphs'][0] for d in self.store.documents.values()]
        for p in [old,new]:self.store.read_context_page(p['id'])
        f={'group':'function','category':'changed','function':'Contract review','owner_before':'Team Alpha','owner_after':'Team Beta',
           'before_evidence':[{'fragment_id':old['id'],'quote':old['text']}],
           'after_evidence':[{'fragment_id':new['id'],'quote':new['text']}],
           'explanation':'Different headings.','limitations':['No exclusivity established.'],'claim_checks':[],'assertion_type':'exclusive_transfer'}
        result=self.state.submit(self.store,[f],'insufficient_data',['Incomplete review.'],'Partial.')
        self.assertFalse(result['accepted'])
        self.assertIn('prior_assignment',str(result['errors']))

    def test_invalid_hypothesis_preserves_independent_candidate_updates_and_budget_identity(self):
        candidate=next(iter(self.state.data['candidates'].values()))
        p=self.store.fragments[candidate['fragment_ids'][0]]
        self.store.read_context_page(p['id'])
        budget=self.state.data['budget']
        result=self.tools.execute('update_research_state',{'hypothesis_id':'h1','claim':'Hypothesis',
            'assessment':'supported','supporting':[],'contradicting':[],'gaps':[],
            'revision_reason':'No evidence.', 'candidate_updates':[{'candidate_id':candidate['id'],
            'status':'reviewed','summary':'Checked.','evidence':[{'fragment_id':p['id'],'quote':p['text']}]}]})
        self.assertFalse(result['accepted'])
        self.assertEqual(self.state.data['candidates'][candidate['id']]['status'],'reviewed')
        self.assertIs(self.state.data['budget'],budget)


if __name__=='__main__':unittest.main()
