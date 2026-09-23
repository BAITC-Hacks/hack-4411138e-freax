"""Short source-based control before another paid R8/R9 evaluation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from ayqyn.documents.store import DocumentStore
from ayqyn.documents.packets import read_packet
from ayqyn.agent.runner import DEFAULT_BUDGET,run_research
from ayqyn.agent.context import compact_messages
from ayqyn.agent.inventory import build_inventory,build_tasks,task_summary,update_tasks
from ayqyn.agent.state import ResearchState
from ayqyn.agent.tools import ResearchTools
from ayqyn.agent.metrics import research_metrics
from test_packets import upload
from test_research import FakeIndex


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        packet=read_packet([
            upload(['1. Responsibilities','1.1. Team Alpha:','1.1.1. Reviews supplier contracts.',
                    'a. Checks delivery deadlines.','b. Checks delivered quality.',
                    '1.1.2. Prepares monthly reports.'],name='before.docx',role='before'),
            upload(['1. Responsibilities','1.1. Team Beta:','1.1.1. Reviews supplier contracts.',
                    'a. Checks delivery deadlines.','b. Checks delivered quality.',
                    '1.1.2. Prepares monthly reports.','1.2. Team Alpha retains the right to review supplier contracts.'],name='after.docx',role='after')],mode='manual')
        self.state=ResearchState(Path(self.temp.name)/'run',packet,'Compare explicit assignments',DEFAULT_BUDGET)
        self.store=DocumentStore(packet)
        self.state.data.update(candidates=build_inventory(self.store),research_policy=3)
        self.state.data['research_tasks']=build_tasks(self.store,self.state.data['candidates'])
        self.tools=ResearchTools(self.state,self.store,FakeIndex(self.store))
        self.old,self.new=list(self.store.documents.values())

    def read_all(self):
        for doc in self.store.documents.values():self.store.read_context(doc['paragraphs'][0]['id'],'document')

    def finding(self,assertion='assignment_change'):
        evidence=lambda doc:[{'fragment_id':p['id'],'quote':p['text']} for p in doc['paragraphs'][1:5]]
        return {'group':'function','category':'changed','assertion_type':assertion,
                'function':'Review supplier contracts; check deadlines and quality',
                'owner_before':'Team Alpha','owner_after':'Team Beta',
                'before_evidence':evidence(self.old),'after_evidence':evidence(self.new),
                'explanation':'The explicit assignment in section 1.1 changes Alpha to Beta.',
                'limitations':['The after document also retains an Alpha review right; exclusivity is not established.'],
                'claim_checks':[]}

    def result(self):
        return {'result_id':'contract-review','finding':self.finding(),'status':'checked',
                'open_question':'Does another act terminate the retained Alpha review right?',
                'next_step':'Check an operative reorganization act if supplied.'}

    def test_explicit_assignment_is_accepted_without_exclusive_transfer_checks(self):
        self.read_all()
        accepted=self.state.submit(self.store,[self.finding()],'insufficient_data',['Full study incomplete.'],'Two explicit assignments compared.')
        self.assertTrue(accepted['accepted'],accepted)
        self.assertEqual(self.state.data['findings'][0]['assertion_type'],'assignment_change')

    def test_two_assignments_do_not_establish_exclusive_transfer(self):
        self.read_all()
        result=self.state.submit(self.store,[self.finding('exclusive_transfer')],'insufficient_data',[], 'Two assignments compared.')
        self.assertFalse(result['accepted'])
        self.assertIn('Exclusive transfer',str(result['errors']))

    def test_compaction_and_reload_keep_checked_result_not_just_action_ids(self):
        self.read_all()
        record=self.result()
        self.assertTrue(self.state.save_checked_results(self.store,[record])['accepted'])
        self.state.data['read_ids']=list(self.store.read_ids)
        self.state.data['messages']=[{'role':'system','content':'policy'},{'role':'user','content':'task'}]
        for n in range(8):
            self.state.data['messages'] += [{'role':'assistant','tool_calls':[{'id':str(n),'function':{'name':'read_context','arguments':'{}'}}]},
                                           {'role':'tool','tool_call_id':str(n),'content':'x'*16000}]
        self.state.save()
        loaded=ResearchState(self.state.path)
        compact=compact_messages(loaded,self.store)
        memory=json.loads(compact[2]['content'])
        result=memory['checked_results'][0]
        for field in ['finding','status','open_question','next_step']:self.assertEqual(result[field],record[field])
        self.assertNotIn('history',result)
        accepted=ResearchTools(loaded,self.store,FakeIndex(self.store)).execute('submit_findings',{
            'findings':[],'saved_result_ids':['contract-review'],'outcome':'insufficient_data',
            'gaps':['Other tasks remain.'],'reason':'Use preserved source-validated result.'})
        self.assertTrue(accepted['accepted'],accepted)
        self.assertEqual(loaded.data['findings'][0]['after_evidence'],record['finding']['after_evidence'])

    def test_duplicate_result_id_cannot_inflate_function_count(self):
        self.read_all()
        record=self.result()
        self.assertTrue(self.state.save_checked_results(self.store,[record])['accepted'])
        duplicate={**record,'result_id':'same-function-again'}
        self.assertFalse(self.state.save_checked_results(self.store,[duplicate])['accepted'])
        self.assertEqual(len(self.state.data['checked_results']),1)

    def test_submission_cannot_double_count_saved_and_new_result(self):
        self.read_all()
        self.assertTrue(self.state.save_checked_results(self.store,[self.result()])['accepted'])
        accepted=self.tools.execute('submit_findings',{
            'findings':[self.finding()],'saved_result_ids':['contract-review'],
            'outcome':'insufficient_data','gaps':['Other tasks remain.'],'reason':'Partial review.'})
        self.assertTrue(accepted['accepted'],accepted)
        self.assertEqual(len(accepted['deduplicated']),1)
        self.assertEqual(len(self.state.data['findings']),1)
        accepted=self.tools.execute('submit_findings',{
            'findings':[],'saved_result_ids':['contract-review'],
            'outcome':'insufficient_data','gaps':['Other tasks remain.'],'reason':'Partial review.'})
        self.assertTrue(accepted['accepted'],accepted)
        self.assertEqual(len(self.state.data['findings']),1)

    def test_tasks_follow_document_heading_and_keep_continuations(self):
        task=next(t for t in self.state.data['research_tasks'].values() if t['role']=='before' and 'Team Alpha' in t['title'])
        texts=[self.store.fragments[key]['text'] for key in task['fragment_ids']]
        self.assertTrue(any('deadlines' in text for text in texts))
        self.assertTrue(any('quality' in text for text in texts))
        self.assertTrue(any('monthly reports' in text for text in texts))
        self.assertLess(len(self.state.data['research_tasks']),len(self.state.data['candidates']))
        self.assertEqual(task['status'],'not_checked')

    def update_payload(self,records,tasks=None):
        return {'hypothesis_id':None,'claim':'','assessment':'open','supporting':[],
                'contradicting':[],'gaps':[],'revision_reason':'','candidate_updates':[],
                'result_updates':records,'task_updates':tasks or []}

    def test_valid_result_survives_invalid_sibling_and_task_closure(self):
        self.read_all()
        good=self.result()
        bad=copy.deepcopy(good);bad['result_id']='monthly-report'
        bad['finding']['function']='Prepares monthly reports'
        for side,doc in [('before',self.old),('after',self.new)]:
            bad['finding'][side+'_evidence']=[{'fragment_id':doc['paragraphs'][5]['id'],'quote':doc['paragraphs'][5]['text']}]
        task=next(iter(self.state.data['research_tasks'].values()))
        closing={'task_id':task['id'],'status':'checked','reviewed_candidate_ids':[],
                 'summary':'One result exists.','open_questions':[],'next_step':None}
        result=self.tools.execute('update_research_state',self.update_payload([good,bad],[closing]))
        self.assertFalse(result['accepted']);self.assertTrue(result['partial'])
        self.assertEqual(result['accepted_result_ids'],['contract-review'])
        self.assertEqual({e['result_id'] for e in result['rejected_results']},{'monthly-report'})
        self.assertEqual({e['code'] for e in result['rejected_results']},{'owner_evidence_missing'})
        self.assertEqual(result['task_update_errors'][0]['task_id'],task['id'])
        self.assertTrue(result['task_update_errors'][0]['missing_candidate_ids'])
        self.assertNotEqual(task['status'],'checked')
        for error in result['rejected_results']:
            hint=error['required_evidence'][0]
            self.assertEqual(hint['relation'],'structural_ancestor')
            bad['finding'][error['field']].append({k:hint[k] for k in ['fragment_id','quote']})
        repaired=self.tools.execute('update_research_state',self.update_payload([bad]))
        self.assertTrue(repaired['accepted'],repaired)
        self.assertEqual(set(self.state.data['checked_results']),{'contract-review','monthly-report'})

    def test_retry_of_same_record_is_idempotent(self):
        self.read_all()
        for _ in range(2):self.assertTrue(self.state.save_checked_results(self.store,[self.result()])['accepted'])
        self.assertEqual(len(self.state.data['checked_results']['contract-review']['history']),1)

    def test_conflicting_submission_versions_are_not_merged(self):
        self.read_all();self.state.save_checked_results(self.store,[self.result()])
        newer=self.finding();newer['explanation']='A conflicting explanation.'
        result=self.tools.execute('submit_findings',{'findings':[newer],'saved_result_ids':['contract-review'],
            'outcome':'insufficient_data','gaps':['Other tasks remain.'],'reason':'Partial.'})
        self.assertFalse(result['accepted'])
        self.assertEqual(result['errors'][0]['code'],'conflicting_result_versions')
        self.assertEqual(result['errors'][0]['entry'],'contract-review')
        self.assertEqual(self.state.data['findings'],[])

    def test_neighbor_is_not_offered_as_owner_evidence(self):
        self.read_all()
        bad=self.result();bad['finding']['owner_after']='Team Alpha'
        bad['finding']['after_evidence']=[bad['finding']['after_evidence'][1]]
        rejected=self.state.save_checked_results(self.store,[bad])
        self.assertFalse(rejected['accepted'])
        error=next(e for e in rejected['rejected_results'] if e['field']=='after_evidence')
        self.assertEqual(error['required_evidence'],[])

    def test_duty_to_detect_duplication_is_not_two_assignments(self):
        packet=read_packet([upload(['1. Team Alpha:',
            '1.1. Identifies insufficient or duplicate assurance coverage.'],name='after.docx',role='after')],mode='manual')
        store=DocumentStore(packet)
        doc=next(iter(store.documents.values()));store.read_context(doc['paragraphs'][0]['id'],'document')
        ev=[{'fragment_id':p['id'],'quote':p['text']} for p in doc['paragraphs']]
        finding={'group':'risk','category':'duplication','assertion_type':'observation','function':'Duplicate coverage',
            'owner_before':None,'owner_after':'Team Alpha','before_evidence':[],'after_evidence':ev,
            'explanation':'The text mentions duplication.','limitations':['Candidate only.'],
            'claim_checks':[{'kind':'duplication_assignment','evidence':[e],'result':'An assignment.'} for e in ev]}
        result=self.state.submit(store,[finding],'insufficient_data',[],'Partial.')
        self.assertFalse(result['accepted'])
        self.assertIn('two duplication_assignment',str(result['errors']))

    def test_driver_repairs_evidence_then_compacts_and_submits_saved_id(self):
        self.read_all()
        bad=self.result()
        for side in ['before','after']:bad['finding'][side+'_evidence']=bad['finding'][side+'_evidence'][1:]
        step=0
        def driver(messages,*args,**kwargs):
            nonlocal step
            if step==0:
                name,arguments='update_research_state',self.update_payload([bad])
            elif step==1:
                reply=json.loads(next(m['content'] for m in reversed(messages) if m['role']=='tool'))
                self.assertEqual({e['result_id'] for e in reply['rejected_results']},{'contract-review'})
                for error in reply['rejected_results']:
                    hint=error['required_evidence'][0]
                    bad['finding'][error['field']].append({k:hint[k] for k in ['fragment_id','quote']})
                name,arguments='update_research_state',self.update_payload([bad])
                self.state.data['messages'].insert(2,{'role':'user','content':'Archived earlier context. '*4000})
            else:
                memory=json.loads(messages[2]['content'])
                self.assertEqual(memory['checked_results'][0]['result_id'],'contract-review')
                self.assertLess(len(json.dumps(messages)),len(json.dumps(self.state.data['messages'])))
                name,arguments='submit_findings',{'findings':[],'saved_result_ids':['contract-review'],
                    'outcome':'insufficient_data','gaps':['Other tasks remain.'],'reason':'Saved result survives.'}
            step+=1
            return {'role':'assistant','tool_calls':[{'id':'call-'+str(step),'type':'function',
                    'function':{'name':name,'arguments':json.dumps(arguments)}}]},{}
        result=run_research(self.state,self.store,FakeIndex(self.store),{},driver=driver)
        self.assertEqual(result['status'],'insufficient_data')
        self.assertEqual(len(result['findings']),1)
        self.assertEqual(step,3)

    def test_group_cannot_close_from_one_read_member(self):
        task=next(t for t in self.state.data['research_tasks'].values() if t['role']=='before' and 'Team Alpha' in t['title'])
        unit=self.state.data['candidates'][task['candidate_ids'][-1]]
        self.store.read_context_page(unit['fragment_ids'][0])
        update={'task_id':task['id'],'status':'checked','reviewed_candidate_ids':[unit['id']],
                'summary':'Checked one function.','open_questions':[],'next_step':None}
        self.assertFalse(update_tasks(self.state,self.store,[update])['accepted'])
        update['status']='partial'
        self.assertTrue(update_tasks(self.state,self.store,[update])['accepted'])
        self.assertEqual(self.state.data['research_tasks'][task['id']]['status'],'partial')
        self.read_all();update.update(status='checked',reviewed_candidate_ids=task['candidate_ids'],summary='All units assessed.')
        self.assertTrue(update_tasks(self.state,self.store,[update])['accepted'])

    def test_bad_result_rolls_back_entire_state_update(self):
        self.read_all()
        bad=self.result();bad['finding']['after_evidence'][0]['quote']='Invented assignment.'
        before=copy.deepcopy(self.state.data)
        result=self.tools.execute('update_research_state',{'hypothesis_id':None,'claim':'','assessment':'open',
            'supporting':[],'contradicting':[],'gaps':[],'revision_reason':'',
            'candidate_updates':[],'task_updates':[],'result_updates':[bad]})
        self.assertFalse(result['accepted'])
        self.assertEqual(self.state.data,before)

    def test_identical_numbers_in_separate_headings_do_not_merge_tasks(self):
        other=read_packet([upload(['1. Actual policy','1.1. Owner:','1.1.1. Reviews contracts.',
                                  '1. Table of contents','1.1. Owner listing','1.1.1. Page reference.'],
                                 name='repeat.docx',role='before')],mode='manual')
        store=DocumentStore(other)
        tasks=build_tasks(store,build_inventory(store))
        body=next(t for t in tasks.values() if any('Reviews contracts' in store.fragments[key]['text'] for key in t['fragment_ids']))
        self.assertNotIn('Page reference.',' '.join(store.fragments[key]['text'] for key in body['fragment_ids']))

    def test_metrics_count_exact_repeats_and_distinct_saved_function_records(self):
        self.read_all();self.state.save_checked_results(self.store,[self.result()])
        arguments={'fragment_id':self.old['paragraphs'][1]['id'],'scope':'section','offset':0}
        for turn in [1,2]:
            result=self.store.read_context_page(**arguments)
            self.state.event('tool_executed',turn=turn,tool='read_context',arguments=arguments,result=result)
        metrics=research_metrics(self.state)
        self.assertEqual(metrics['exact_repeated_read_calls'],1)
        self.assertEqual(metrics['unique_checked_function_records'],1)
        self.assertGreater(metrics['repeated_fragment_deliveries'],0)

    def test_metrics_include_truncated_reply_that_did_not_execute_an_action(self):
        self.state.data['usage']=[{'prompt_tokens':100,'completion_tokens':20}]
        for n,usage in enumerate([self.state.data['usage'][0],{'prompt_tokens':150,'completion_tokens':8000}],1):
            path=self.state.path/f'turn-{n:03d}'
            path.mkdir()
            (path/'manifest.json').write_text(json.dumps({'usage':usage,'truncated':n==2}),encoding='utf-8')
        metrics=research_metrics(self.state)
        self.assertEqual(metrics['prompt_tokens'],250)
        self.assertEqual(metrics['completion_tokens'],8020)
        self.assertEqual(metrics['usage_source'],'provider_manifests')


if __name__=='__main__':unittest.main()
