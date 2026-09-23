"""Technical tests with a simulated provider; not a live LLM quality score."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from document_store import DocumentStore
from packets import read_packet
from research_agent import run_research,DEFAULT_BUDGET,restore_research
from research_state import ResearchState
from research_tools import ResearchTools,TOOL_SCHEMAS
from test_packets import upload


def packet():
    return read_packet([
        upload(['1. Положение. Старая редакция','2.3. Департамент закупок контролирует исполнение договоров с поставщиками.'],name='old.docx',role='before'),
        upload(['1. Положение. Новая редакция','2.1. Управление торгов проводит тендеры.'],name='new.docx',role='after'),
        upload(['1. Приложение. Новая редакция','7.2. Сектор сопровождения контролирует исполнение договоров с поставщиками.'],name='annex.docx',role='after')],mode='manual')


class FakeIndex:
    """Deliberately lexical: only for tool plumbing tests, never called hybrid quality."""
    def __init__(self, store): self.store,self.config=store,{}
    def search(self,**kwargs): return self.store.search_fragments(**kwargs)


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.state=ResearchState(Path(self.temp.name)/'research',packet(),'Проверь гипотезу потери.',DEFAULT_BUDGET)
        self.store=DocumentStore(self.state.packet)
        self.tools=ResearchTools(self.state,self.store,FakeIndex(self.store))
        self.old=next(p for p in self.store.fragments.values() if 'Департамент закупок контролирует' in p['text'])
        self.new=next(p for p in self.store.fragments.values() if 'Сектор сопровождения контролирует' in p['text'])

    def tearDown(self): self.temp.cleanup()

    def evidence(self,p): return {'fragment_id':p['id'],'quote':p['text']}

    def hypothesis(self,**changes):
        return {'hypothesis_id':'h1','claim':'Возможно, контроль исполнения договоров не закреплён.',
                'assessment':'open','supporting':[],'contradicting':[],'gaps':['Нужно проверить приложения.'],
                'revision_reason':'Начальная непроверенная гипотеза задачи.',**changes}

    def finding(self):
        return {'group':'function','category':'changed','function':'Контроль исполнения договоров с поставщиками',
                'owner_before':'Департамент закупок','owner_after':'Сектор сопровождения',
                'before_evidence':[self.evidence(self.old)],'after_evidence':[self.evidence(self.new)],
                'explanation':'Изменилось явное закрепление функции.','limitations':['Фактическое исполнение и исключительная передача не доказаны.']}

    def read_all(self):
        for doc in self.store.documents.values(): self.store.read_context(doc['paragraphs'][0]['id'],scope='document')

    def test_minimum_six_native_tools(self):
        self.assertTrue({'list_documents','search','read_context','update_research_state','get_coverage','submit_findings'}<=
                        {s['function']['name'] for s in TOOL_SCHEMAS})

    def test_unread_or_foreign_evidence_rejected(self):
        result=self.state.update_hypothesis(self.store,self.hypothesis(assessment='supported',supporting=[self.evidence(self.old)]))
        self.assertFalse(result['accepted'])
        result=self.state.update_hypothesis(self.store,self.hypothesis(assessment='supported',supporting=[{'fragment_id':'foreign:p1','quote':'какая-то обязанность'}]))
        self.assertFalse(result['accepted'])

    def test_revision_and_reload_preserve_budget_and_evidence(self):
        self.assertTrue(self.tools.execute('update_research_state',self.hypothesis())['accepted'])
        self.store.read_context(self.new['id'])
        revised=self.hypothesis(assessment='refuted',contradicting=[self.evidence(self.new)],gaps=[],revision_reason='Приложение закрепляет действие за другим владельцем.')
        self.assertTrue(self.tools.execute('update_research_state',revised)['accepted'])
        self.state.data['budget']['tool_calls_used']=3
        self.state.data['read_ids']=list(self.store.read_ids)
        self.state.save()
        loaded=ResearchState(self.state.path)
        self.assertEqual(loaded.data['budget']['tool_calls_used'],3)
        self.assertEqual([h['assessment'] for h in loaded.data['hypotheses']['h1']['history']],['open','refuted'])
        self.assertEqual(loaded.data['hypotheses']['h1']['contradicting'][0]['fragment_id'],self.new['id'])

    def test_empty_search_does_not_authorize_potential_loss(self):
        self.store.read_context(self.old['id'])
        self.tools.execute('search',{'query':'несуществующая функция','role':'after','document_id':None,'limit':2})
        f=self.finding();f.update(group='risk',category='potential_loss',after_evidence=[],owner_after=None)
        result=self.state.submit(self.store,[f],'completed',[],'Поиск завершён.')
        self.assertFalse(result['accepted'])

    def test_wrong_quote_returns_repair_errors_and_valid_quote_can_submit(self):
        self.read_all()
        bad=self.finding();bad['after_evidence'][0]['quote']='Сектор сопровождения утверждает договоры.'
        result=self.state.submit(self.store,[bad],'completed',[],'Проверен комплект.')
        self.assertFalse(result['accepted'])
        self.assertFalse(self.state.data['findings'])
        result=self.state.submit(self.store,[self.finding()],'completed',[],'Приложение найдено и прочитано.')
        self.assertTrue(result['accepted'])
        self.assertEqual(self.state.data['findings'][0]['human_review']['status'],'unreviewed')

    def test_wrong_side_and_invented_owner_rejected(self):
        self.read_all()
        f=self.finding();f['owner_after']='Главный аудитор'
        self.assertFalse(self.state.submit(self.store,[f],'completed',[],'Готово.')['accepted'])
        f=self.finding();f['after_evidence']=f['before_evidence']
        self.assertFalse(self.state.submit(self.store,[f],'completed',[],'Готово.')['accepted'])

    def test_unknown_versions_can_only_finish_as_insufficient(self):
        self.state.packet['ready']=False
        self.read_all()
        self.assertFalse(self.state.submit(self.store,[self.finding()],'completed',[],'Готово.')['accepted'])
        self.assertTrue(self.state.submit(self.store,[],'insufficient_data',['Версия приложения не установлена.'],'Нужно уточнение.')['accepted'])

    def test_bad_arguments_and_unknown_tools_cannot_execute(self):
        for name,args in [('shell',{'cmd':'test'}),('list_documents',{'path':'outside'}),('search',{'query':'a','role':None,'document_id':None,'limit':True})]:
            with self.subTest(name=name),self.assertRaises(ValueError): self.tools.execute(name,args)

    def test_native_loop_can_change_hypothesis_based_on_actual_tool_result(self):
        def driver(messages,*args,**kwargs):
            results=[json.loads(m['content']) for m in messages if m['role']=='tool']
            n=len(results)
            if n==0: name,arguments='update_research_state',self.hypothesis()
            elif n==1: name,arguments='search',{'query':'контролирует исполнение договоров','role':'after','document_id':None,'limit':5}
            elif n==2:
                hit=results[-1]['hits'][0]
                name,arguments='read_context',{'fragment_id':hit['id'],'scope':'document'}
            elif n==3:
                evidence=[{'fragment_id':p['id'],'quote':p['text']} for p in results[-1]['fragments'] if 'Сектор сопровождения контролирует' in p['text']]
                name,arguments='update_research_state',self.hypothesis(assessment='refuted',contradicting=evidence,gaps=[],revision_reason='В прочитанном приложении найдено назначение.')
            else: name,arguments='submit_findings',{'findings':[],'outcome':'insufficient_data','gaps':['Остальные документы ещё не прочитаны.'],'reason':'Гипотеза опровергнута, полный анализ не завершён.'}
            return {'role':'assistant','content':None,'tool_calls':[{'id':f'call-{n}','type':'function','function':{'name':name,'arguments':json.dumps(arguments)}}]},{}
        result=run_research(self.state,self.store,FakeIndex(self.store),{},driver=driver)
        self.assertEqual(result['status'],'insufficient_data')
        self.assertEqual([h['assessment'] for h in result['hypotheses']['h1']['history']],['open','refuted'])
        self.assertEqual([e['tool'] for e in result['journal'] if e['kind']=='tool_executed'],['update_research_state','search','read_context','update_research_state','submit_findings'])
        self.assertEqual(result['budget']['tool_calls_used'],5)

    def test_budget_exhaustion_preserves_partial_state(self):
        self.state.data['budget']['max_tool_calls']=1
        def driver(*args,**kwargs):
            return {'role':'assistant','content':None,'tool_calls':[{'id':'call-1','type':'function','function':{'name':'update_research_state','arguments':json.dumps(self.hypothesis())}}]},{}
        result=run_research(self.state,self.store,FakeIndex(self.store),{},driver=driver)
        self.assertEqual(result['status'],'budget_exhausted')
        self.assertIn('h1',ResearchState(self.state.path).data['hypotheses'])

    def test_failed_model_does_not_claim_completion(self):
        def fails(*args,**kwargs): raise ValueError('Provider unavailable')
        result=run_research(self.state,self.store,FakeIndex(self.store),{},driver=fails)
        self.assertEqual(result['status'],'model_error')
        self.assertEqual(result['budget']['tool_calls_used'],0)

    def test_late_model_response_does_not_execute_action(self):
        now=[0.0]
        def driver(*args,**kwargs):
            now[0]=self.state.data['budget']['max_seconds']+1
            return {'role':'assistant','content':None,'tool_calls':[{'id':'late','type':'function',
                'function':{'name':'update_research_state','arguments':json.dumps(self.hypothesis())}}]},{}
        result=run_research(self.state,self.store,FakeIndex(self.store),{},driver=driver,clock=lambda:now[0])
        self.assertEqual(result['status'],'budget_exhausted')
        self.assertEqual(result['budget']['tool_calls_used'],0)
        self.assertFalse(result['hypotheses'])

    def test_pending_call_resume_does_not_fabricate_execution_or_reset_budget(self):
        pending={'id':'interrupted','type':'function','function':{'name':'list_documents','arguments':'{}'}}
        self.state.data.update(status='interrupted',pending_call=pending,messages=[
            {'role':'assistant','content':None,'tool_calls':[pending]}])
        self.state.data['budget'].update(model_calls_used=3,tool_calls_used=2,elapsed_seconds=7)
        def driver(messages,*args,**kwargs):
            self.assertEqual(messages[-1]['role'],'tool')
            self.assertIn('error',json.loads(messages[-1]['content']))
            return {'role':'assistant','content':None,'tool_calls':[{'id':'finish','type':'function',
                'function':{'name':'submit_findings','arguments':json.dumps({'findings':[],
                    'outcome':'insufficient_data','gaps':['Interrupted operation needs verification.'],
                    'reason':'Sources not checked.'})}}]},{}
        result=run_research(self.state,self.store,FakeIndex(self.store),{},driver=driver)
        self.assertEqual(result['status'],'insufficient_data')
        self.assertEqual(result['budget']['model_calls_used'],4)
        self.assertEqual(result['budget']['tool_calls_used'],3)
        self.assertGreaterEqual(result['budget']['elapsed_seconds'],7)
        self.assertEqual([e['tool'] for e in result['journal'] if e['kind']=='tool_executed'],['submit_findings'])

    def test_restore_keeps_search_scope_and_prior_embedding_usage(self):
        args={'query':'договоров','role':'after','document_id':None,'limit':2}
        result=self.tools.execute('search',args)
        self.state.event('tool_executed',tool='search',arguments=args,result=result)
        self.state.data.update(status='interrupted',index={'usage':{'query':{
            'provider_requests':2,'total_tokens':17,'token_usage_complete':True}}})
        self.state.save()
        index=Mock(config={},metadata={'usage':{'query':{
            'provider_requests':0,'total_tokens':0,'token_usage_complete':True}}})
        with patch('hybrid_search.HybridIndex',return_value=index):
            state,store,_=restore_research(self.state.path,{})
        self.assertEqual(store.get_coverage()['search_scopes'][0]['query'],'договоров')
        self.assertEqual(state.data['index']['usage']['query']['provider_requests'],2)
        self.assertEqual(state.data['index']['usage']['query']['total_tokens'],17)
        self.assertFalse(store.read_ids)

    def test_journal_is_immutable_snapshot_and_secrets_are_redacted(self):
        state=ResearchState(Path(self.temp.name)/'private',packet(),'task',DEFAULT_BUDGET,secrets=['private-key'])
        value={'used':0,'error':'private-key'}
        state.event('test',result=value);value['used']=100
        state.save()
        self.assertEqual(state.data['journal'][0]['result']['used'],0)
        self.assertNotIn('private-key',(state.path/'state.json').read_text(encoding='utf-8'))


if __name__=='__main__': unittest.main()
