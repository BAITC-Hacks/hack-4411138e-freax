"""One bounded function write; interpretation still requires a separate evaluation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from ayqyn.documents.store import DocumentStore
from ayqyn.documents.packets import read_packet
from ayqyn.agent.runner import DEFAULT_BUDGET
from ayqyn.agent.context import compact_messages
from ayqyn.agent.state import ResearchState
from ayqyn.agent.tools import ResearchTools, TOOL_SCHEMAS, validate_shape
from test_packets import upload
from test_research import FakeIndex


class FunctionUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        packet=read_packet([
            upload(['1. Team Alpha:', '1.1. Prepares monthly plans and collaborates with reviewers.'], name='before.docx',role='before'),
            upload(['1. Team Beta:', '1.1. Prepares monthly plans and collaborates with reviewers.'], name='after.docx',role='after')],mode='manual')
        self.state=ResearchState(Path(self.temp.name)/'run',packet,'Compare',DEFAULT_BUDGET)
        self.state.data['research_policy']=4
        self.store=DocumentStore(packet)
        self.tools=ResearchTools(self.state,self.store,FakeIndex(self.store))
        self.old,self.new=list(self.store.documents.values())
        for doc in [self.old,self.new]:self.store.read_context_page(doc['paragraphs'][1]['id'])

    def record(self,identifier='planning',action='Prepares',object_='monthly plans'):
        side={'action':action,'object':object_,'conditions':None,'stage':None}
        return {'result_id':identifier,'status':'checked','open_question':None,'next_step':None,
                'finding':{'group':'function','category':'changed','assertion_type':'assignment_change',
                    'function':action+' '+object_,'owner_before':'Team Alpha','owner_after':'Team Beta',
                    'before_evidence':[{'fragment_id':p['id'],'quote':p['text']} for p in self.old['paragraphs']],
                    'after_evidence':[{'fragment_id':p['id'],'quote':p['text']} for p in self.new['paragraphs']],
                    'explanation':'Only the explicit owner changes. No exclusive transfer is established.',
                    'limitations':['No operative reorganization act supplied.'],'claim_checks':[],
                    'comparison':{'before':dict(side),'after':dict(side),'changed_fields':['owner']}}}

    def payload(self,records):
        return {'hypothesis_id':None,'claim':'','assessment':'open','supporting':[],
                'contradicting':[],'gaps':[],'revision_reason':'','candidate_updates':[],
                'result_updates':records,'task_updates':[],'work_updates':[]}

    def test_same_action_and_object_accept_owner_change_with_parent_evidence(self):
        record=self.record()
        result=self.tools.execute('update_research_state',self.payload([record]))
        self.assertTrue(result['accepted'],result)
        saved=self.state.data['checked_results']['planning']['finding']
        self.assertEqual(saved['comparison']['before'],saved['comparison']['after'])
        self.assertEqual(saved['comparison']['changed_fields'],['owner'])
        for side,doc in [('before',self.old),('after',self.new)]:
            self.assertEqual(len(saved[side+'_evidence']),2)
            self.assertEqual(doc['paragraphs'][1]['parent_id'],doc['paragraphs'][0]['id'])

    def test_two_actions_in_same_clause_remain_independent_after_compaction_and_submission(self):
        records=[self.record(),self.record('reviewers','Collaborates with','reviewers')]
        for record in records:
            self.assertTrue(self.tools.execute('update_research_state',self.payload([record]))['accepted'])
        self.state.data['messages']=[{'role':'system','content':'policy'},{'role':'user','content':'Compare'}]
        for n in range(8):
            self.state.data['messages'] += [{'role':'assistant','tool_calls':[{'id':str(n),'function':{'name':'read_context','arguments':'{}'}}]},
                                           {'role':'tool','tool_call_id':str(n),'content':'x'*16000}]
        self.state.save()
        loaded=ResearchState(self.state.path)
        memory=json.loads(compact_messages(loaded,self.store)[2]['content'])
        self.assertEqual([r['finding']['comparison'] for r in memory['checked_results']],
                         [r['finding']['comparison'] for r in records])
        result=ResearchTools(loaded,self.store,FakeIndex(self.store)).execute('submit_findings',{
            'findings':[],'saved_result_ids':['planning','reviewers'],'outcome':'insufficient_data',
            'gaps':['Other duties not checked.'],'reason':'Two assignments compared.'})
        self.assertTrue(result['accepted'],result)
        self.assertEqual(len(loaded.data['findings']),2)

    def test_native_schema_and_executor_reject_a_batch_before_mutation(self):
        schema=next(s['function']['parameters'] for s in TOOL_SCHEMAS if s['function']['name']=='update_research_state')
        payload=self.payload([self.record(),self.record('reviewers','Collaborates with','reviewers')])
        self.assertEqual(schema['properties']['result_updates']['maxItems'],1)
        with self.assertRaisesRegex(ValueError,'result_updates'):validate_shape(payload,schema)
        before=copy.deepcopy(self.state.data)
        with self.assertRaisesRegex(ValueError,'result_updates'):self.tools.execute('update_research_state',payload)
        self.assertFalse(self.state.save_checked_results(self.store,payload['result_updates'])['accepted'])
        self.assertEqual(self.state.data,before)

    def test_changed_section_without_specific_difference_is_rejected_by_result_id(self):
        record=self.record();record['finding']['comparison']['changed_fields']=[]
        result=self.tools.execute('update_research_state',self.payload([record]))
        self.assertFalse(result['accepted'])
        self.assertEqual({e['result_id'] for e in result['rejected_results']},{'planning'})
        self.assertEqual({e['field'] for e in result['rejected_results']},{'comparison'})
        record['finding']['comparison']['changed_fields']=['owner']
        self.assertTrue(self.tools.execute('update_research_state',self.payload([record]))['accepted'])

    def test_identical_or_unknown_dimension_is_not_a_proven_change(self):
        for field in ['action','conditions']:
            record=self.record();record['finding']['comparison']['changed_fields'].append(field)
            result=self.tools.execute('update_research_state',self.payload([record]))
            self.assertFalse(result['accepted'],result)
        self.assertEqual(self.state.data['checked_results'],{})

    def test_assignment_change_still_does_not_prove_exclusivity(self):
        record=self.record();record['finding']['assertion_type']='exclusive_transfer'
        result=self.tools.execute('update_research_state',self.payload([record]))
        self.assertFalse(result['accepted'])
        self.assertIn('Exclusive transfer',str(result))

    def test_new_policy_requires_comparison_but_old_records_remain_loadable(self):
        record=self.record();record['finding'].pop('comparison')
        self.assertFalse(self.tools.execute('update_research_state',self.payload([record]))['accepted'])
        self.state.data['research_policy']=3
        self.assertTrue(self.tools.execute('update_research_state',self.payload([record]))['accepted'])
        self.state.save()
        loaded=ResearchState(self.state.path)
        self.assertNotIn('comparison',loaded.data['checked_results']['planning']['finding'])


if __name__=='__main__':unittest.main()
