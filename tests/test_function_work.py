"""Offline work lifecycle proofs, not evidence of autonomous model quality."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ayqyn.documents.store import DocumentStore
from ayqyn.documents.packets import read_packet
from ayqyn.agent.runner import DEFAULT_BUDGET, run_research
from ayqyn.agent.context import compact_messages
from ayqyn.agent.state import ResearchState
from ayqyn.agent.tools import ResearchTools
from test_packets import upload
from test_research import FakeIndex


class FunctionWorkTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        packet=read_packet([
            upload(['1. Team Alpha:', '1.1. Reviews supplier contracts:', 'a. With written consent.',
                    '1.2. Prepares monthly plans.'],name='before.docx',role='before'),
            upload(['1. Team Beta:', '1.1. Reviews supplier contracts:', 'a. With written consent.',
                    '1.2. Prepares monthly plans.', '2. Team Gamma:', '2.1. May not review supplier contracts.'],name='after.docx',role='after')],mode='manual')
        self.state=ResearchState(Path(self.temp.name)/'run',packet,'Compare functions',DEFAULT_BUDGET)
        self.state.data['research_policy']=5
        self.store=DocumentStore(packet)
        self.index=FakeIndex(self.store)
        self.tools=ResearchTools(self.state,self.store,self.index)
        self.old,self.new=list(self.store.documents.values())
        self.store.read_context_page(self.old['paragraphs'][1]['id'])
        self.network=patch('ayqyn.providers.llm.request_json_api',side_effect=AssertionError('No provider calls in offline work tests.'))
        self.network.start();self.addCleanup(self.network.stop)

    def work(self,identifier='review',status='needs_search'):
        return {'work_id':identifier,'function':'Review supplier contracts',
                'before_ids':[p['id'] for p in self.old['paragraphs'][:3]],'after_ids':[],
                'candidate_ids':[],'counter_evidence_ids':[],
                'open_question':'Who is assigned review in the new policy?',
                'next_action':'Search the new policy for the same operation.',
                'status':status,'result_id':None,'resolution':None}

    def payload(self,works=None,results=None):
        return {'hypothesis_id':None,'claim':'','assessment':'open','supporting':[],
                'contradicting':[],'gaps':[],'revision_reason':'','candidate_updates':[],
                'task_updates':[],'work_updates':works or [],'result_updates':results or []}

    def record(self):
        side={'action':'reviews','object':'supplier contracts','conditions':'with written consent','stage':'review'}
        return {'result_id':'result-review','status':'checked','open_question':None,'next_step':None,
                'finding':{'group':'function','category':'changed','assertion_type':'assignment_change',
                    'function':'Review supplier contracts','owner_before':'Team Alpha','owner_after':'Team Beta',
                    'before_evidence':[{'fragment_id':p['id'],'quote':p['text']} for p in self.old['paragraphs'][:3]],
                    'after_evidence':[{'fragment_id':p['id'],'quote':p['text']} for p in self.new['paragraphs'][:3]],
                    'explanation':'The explicitly assigned team changed; conditions are the same.',
                    'limitations':['Other operations not verified.'],'claim_checks':[],
                    'comparison':{'before':dict(side),'after':dict(side),'changed_fields':['owner']}}}

    def finish(self,work):
        return {**work,'after_ids':[p['id'] for p in self.new['paragraphs'][:3]],
                'status':'completed','result_id':'result-review',
                'resolution':'Both read assignments compared; exclusivity not established.'}

    def test_functions_are_registered_from_reading_without_search_results(self):
        first=self.work();second=self.work('planning')
        second.update(function='Prepare monthly plans',before_ids=[self.old['paragraphs'][3]['id']])
        self.store.read_context_page(self.old['paragraphs'][3]['id'])
        result=self.tools.execute('update_research_state',self.payload([first,second]))
        self.assertTrue(result['accepted'],result)
        self.assertEqual(set(self.state.data['function_work']),{'review','planning'})
        self.assertFalse(self.state.data['checked_results'])
        self.assertFalse(any(a['tool'].startswith('search') for a in self.store.actions))

    def test_both_read_sides_are_saved_without_search_and_linked_in_one_update(self):
        self.store.read_context_page(self.new['paragraphs'][1]['id'])
        work=self.work(status='ready_to_compare');work['after_ids']=[p['id'] for p in self.new['paragraphs'][:3]]
        self.assertTrue(self.tools.execute('update_research_state',self.payload([work]))['accepted'])
        with patch.object(self.index,'search',side_effect=AssertionError('Unnecessary search.')):
            result=self.tools.execute('update_research_state',self.payload([self.finish(work)],[self.record()]))
        self.assertTrue(result['accepted'],result)
        self.assertEqual(self.state.data['function_work']['review']['result_id'],'result-review')
        self.assertEqual(self.state.data['checked_results']['result-review']['finding']['comparison']['changed_fields'],['owner'])

    def test_candidate_search_then_parent_and_continuations_then_save(self):
        work=self.work()
        self.tools.execute('update_research_state',self.payload([work]))
        candidate=self.new['paragraphs'][1]['id']
        actions=[('search',{'query':'Reviews supplier contracts','role':'after','document_id':None,'limit':5,'work_id':'review'}),
                 ('read_context',{'fragment_id':candidate,'scope':'section','offset':0,'work_id':'review','purpose':'Read the candidate owner and conditions.'}),
                 ('update_research_state',self.payload([self.finish(work)],[self.record()])),
                 ('submit_findings',{'findings':[],'saved_result_ids':['result-review'],'outcome':'insufficient_data',
                                     'gaps':['Remaining duties not evaluated.'],'reason':'Only one function compared.','unfinished_work':[]})]
        step=0
        def driver(messages,tools,config,before,after,**kwargs):
            nonlocal step
            if step==1:
                self.assertIn(candidate,self.state.data['function_work']['review']['candidate_ids'])
                self.assertEqual(self.state.data['function_work']['review']['status'],'needs_read')
                self.assertNotIn(candidate,self.store.read_ids)
            if step==2:
                returned=json.loads(messages[-1]['content'])['fragments']
                self.assertTrue(set(p['id'] for p in self.new['paragraphs'][:3])<={p['id'] for p in returned})
                self.assertEqual(self.state.data['function_work']['review']['after_ids'],[])
            name,args=actions[step];step+=1
            return {'role':'assistant','tool_calls':[{'id':'call-'+str(step),'type':'function',
                    'function':{'name':name,'arguments':json.dumps(args)}}]},{}
        self.state.data['read_ids']=list(self.store.read_ids)
        result=run_research(self.state,self.store,self.index,{},driver=driver)
        self.assertEqual(result['status'],'insufficient_data')
        self.assertEqual(len(result['findings']),1)
        self.assertEqual(result['function_work']['review']['status'],'completed')

    def test_compaction_reload_retains_open_question_candidates_and_contradiction(self):
        self.store.read_context_page(self.new['paragraphs'][5]['id'])
        work=self.work(status='needs_read')
        work.update(candidate_ids=[self.new['paragraphs'][1]['id']],counter_evidence_ids=[self.new['paragraphs'][5]['id']])
        self.tools.execute('update_research_state',self.payload([work]))
        self.state.data['messages']=[{'role':'system','content':'policy'},{'role':'user','content':'Compare'}]
        for n in range(8):
            self.state.data['messages'] += [{'role':'assistant','tool_calls':[{'id':str(n),'function':{'name':'read_context','arguments':'{}'}}]},
                                           {'role':'tool','tool_call_id':str(n),'content':'x'*16000}]
        self.state.data['read_ids']=list(self.store.read_ids);self.state.save()
        loaded=ResearchState(self.state.path)
        memory=json.loads(compact_messages(loaded,self.store)[2]['content'])['function_work'][0]
        for field in work:self.assertEqual(memory[field],work[field])
        self.assertEqual(memory['unread_candidate_ids'],work['candidate_ids'])

    def test_reading_a_contradictory_candidate_never_confirms_correspondence(self):
        bad=self.new['paragraphs'][5]['id'];work=self.work(status='needs_read');work['candidate_ids']=[bad]
        self.tools.execute('update_research_state',self.payload([work]))
        self.tools.execute('read_context',{'fragment_id':bad,'scope':'section','work_id':'review','purpose':'Check possible contradiction.'})
        stored=self.state.data['function_work']['review']
        self.assertEqual(stored['status'],'needs_read')
        self.assertEqual(stored['after_ids'],[])
        self.assertIsNone(stored['result_id'])
        self.assertFalse(self.state.data['checked_results'])

    def test_invalid_result_cannot_close_work_or_erase_it(self):
        self.store.read_context_page(self.new['paragraphs'][1]['id'])
        work=self.work();self.tools.execute('update_research_state',self.payload([work]))
        bad=self.record();bad['finding']['after_evidence'][1]['quote']='Invented assignment'
        result=self.tools.execute('update_research_state',self.payload([self.finish(work)],[bad]))
        self.assertFalse(result['accepted'])
        self.assertTrue(result['work_errors'])
        self.assertEqual(self.state.data['function_work']['review'],work)
        self.assertFalse(self.state.data['checked_results'])

    def test_partial_submission_needs_specific_reasons_and_does_not_close_open_work(self):
        self.tools.execute('update_research_state',self.payload([self.work()]))
        args={'findings':[],'outcome':'insufficient_data','gaps':[],'reason':'Incomplete.','saved_result_ids':[]}
        self.assertFalse(self.tools.execute('submit_findings',args)['accepted'])
        args['unfinished_work']=[{'work_id':'review','reason':'A possible new assignment has not been found.'}]
        self.assertTrue(self.tools.execute('submit_findings',args)['accepted'])
        self.assertEqual(self.state.data['function_work']['review']['status'],'needs_search')
        self.assertIn('Review supplier contracts',self.state.data['gaps'][-1])

    def test_readiness_requires_read_sources_not_search_hits(self):
        work=self.work(status='ready_to_compare');work['after_ids']=[self.new['paragraphs'][1]['id']]
        self.assertFalse(self.tools.execute('update_research_state',self.payload([work]))['accepted'])
        self.assertFalse(self.state.data['function_work'])

    def test_repeated_read_requires_a_factual_purpose(self):
        args={'fragment_id':self.old['paragraphs'][1]['id'],'scope':'section','offset':0}
        with self.assertRaisesRegex(ValueError,'uncertainty'):self.tools.execute('read_context',args)
        self.assertTrue(self.tools.execute('read_context',{**args,'purpose':'Check whether written consent applies to this action.'})['fragments'])

    def test_replacing_a_closed_result_requires_explicit_reopening(self):
        self.store.read_context_page(self.new['paragraphs'][1]['id'])
        self.tools.execute('update_research_state',self.payload([self.finish(self.work())],[self.record()]))
        changed=self.record();changed['status']='partial'
        self.assertFalse(self.state.save_checked_results(self.store,[changed])['accepted'])
        self.assertEqual(self.state.data['checked_results']['result-review']['status'],'checked')

    def test_missing_sources_and_fake_saved_result_do_not_create_work(self):
        work=self.work();work['before_ids']=[]
        self.assertFalse(self.tools.execute('update_research_state',self.payload([work]))['accepted'])
        self.store.read_context_page(self.new['paragraphs'][1]['id'])
        self.assertFalse(self.tools.execute('update_research_state',self.payload([self.finish(self.work())]))['accepted'])
        self.assertFalse(self.state.data['function_work'])

    def test_an_overfull_candidate_search_never_discards_previous_evidence(self):
        work=self.work(status='needs_read');work['candidate_ids']=[self.new['paragraphs'][1]['id']]
        self.tools.execute('update_research_state',self.payload([work]))
        with patch.object(self.index,'search',side_effect=AssertionError('Search should not start.')):
            with self.assertRaisesRegex(ValueError,'narrow'):
                self.tools.execute('search',{'query':'Contracts','role':'after','document_id':None,'limit':20,'work_id':'review'})
        self.assertEqual(self.state.data['function_work']['review'],work)

    def test_budget_stop_retains_open_work_with_factual_stop_reason(self):
        self.tools.execute('update_research_state',self.payload([self.work()]))
        self.state.data['budget'].update(max_model_calls=1,max_tool_calls=1)
        def driver(*args,**kwargs):
            return {'role':'assistant','tool_calls':[{'id':'c1','type':'function','function':{
                'name':'get_coverage','arguments':json.dumps({'offset':0,'task_id':None})}}]},{}
        self.state.data['read_ids']=list(self.store.read_ids)
        result=run_research(self.state,self.store,self.index,{},driver=driver)
        self.assertEqual(result['status'],'budget_exhausted')
        self.assertEqual(result['unfinished_work'],[{'work_id':'review','reason':result['stop_reason']}])
        self.assertEqual(result['function_work']['review']['status'],'needs_search')

    def test_duplicate_work_ids_do_not_silently_replace_a_function(self):
        original=self.work();other=copy.deepcopy(original)
        other['function']='Prepare monthly plans'
        result=self.tools.execute('update_research_state',self.payload([original,other]))
        self.assertFalse(result['accepted'])
        self.assertEqual(result['accepted_work_ids'],[])
        self.assertFalse(self.state.data['function_work'])
        self.tools.execute('update_research_state',self.payload([original]))
        self.assertFalse(self.tools.execute('update_research_state',self.payload([other]))['accepted'])
        self.assertEqual(self.state.data['function_work']['review'],original)

    def test_a_saved_result_for_another_source_does_not_close_work(self):
        self.store.read_context_page(self.new['paragraphs'][0]['id'])
        self.store.read_context_page(self.new['paragraphs'][5]['id'])
        self.assertTrue(self.state.save_checked_results(self.store,[self.record()])['accepted'])
        work=self.finish(self.work());work['after_ids']=[self.new['paragraphs'][5]['id']]
        result=self.tools.execute('update_research_state',self.payload([work]))
        self.assertFalse(result['accepted'])
        self.assertIn('another assignment',str(result['work_errors']))
        self.assertFalse(self.state.data['function_work'])

    def test_closed_insufficient_data_cannot_be_discarded_to_submit_completed(self):
        self.store.read_context_page(self.new['paragraphs'][0]['id'],'document')
        self.store.read_context_page(self.old['paragraphs'][0]['id'],'document')
        record=self.record();record.update(status='insufficient_data',open_question='Scope remains unknown.')
        record['finding'].update(category='unmatched',assertion_type='observation')
        work=self.finish(self.work());work.update(status='insufficient_data',resolution='A candidate was read, but its scope remains unknown.')
        self.assertTrue(self.tools.execute('update_research_state',self.payload([work],[record]))['accepted'])
        args={'findings':[],'saved_result_ids':[],'outcome':'completed','gaps':[],'reason':'Everything checked.','unfinished_work':[]}
        self.assertFalse(self.tools.execute('submit_findings',args)['accepted'])
        self.assertTrue(self.tools.execute('submit_findings',{**args,'outcome':'insufficient_data'})['accepted'])
        self.assertIn(work['resolution'],self.state.data['gaps'][-1])

    def test_two_remaining_calls_allow_saving_then_submission_not_new_investigation(self):
        self.store.read_context_page(self.new['paragraphs'][1]['id'])
        work=self.work(status='ready_to_compare');work['after_ids']=[p['id'] for p in self.new['paragraphs'][:3]]
        self.tools.execute('update_research_state',self.payload([work]))
        self.state.data['budget'].update(max_model_calls=2,max_tool_calls=2)
        step=0
        def driver(messages,schemas,*args,**kwargs):
            nonlocal step
            names={s['function']['name'] for s in schemas}
            if step==0:
                self.assertIn('update_research_state',names);self.assertNotIn('search',names)
                name,arguments='update_research_state',self.payload([self.finish(work)],[self.record()])
            else:
                self.assertNotIn('update_research_state',names)
                name,arguments='submit_findings',{'findings':[],'saved_result_ids':['result-review'],
                    'outcome':'insufficient_data','gaps':['Other duties unverified.'],'reason':'Partial review.','unfinished_work':[]}
            step+=1
            return {'role':'assistant','tool_calls':[{'id':'c'+str(step),'type':'function',
                'function':{'name':name,'arguments':json.dumps(arguments)}}]},{}
        self.state.data['read_ids']=list(self.store.read_ids)
        with patch('ayqyn.agent.runner.agent_turn',side_effect=driver):
            result=run_research(self.state,self.store,self.index,{})
        self.assertEqual(result['status'],'insufficient_data')
        self.assertEqual(len(result['findings']),1)
        self.assertEqual(step,2)


if __name__=='__main__':unittest.main()
