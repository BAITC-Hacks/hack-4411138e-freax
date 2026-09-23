"""Replay one archived update in memory; never modifies the source run or uses API."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ayqyn.documents.store import DocumentStore
from ayqyn.agent.inventory import build_inventory,build_tasks
from ayqyn.agent.state import ResearchState
from ayqyn.agent.tools import ResearchTools


def replay(path,turn):
    original_hash=hashlib.sha256((path/'state.json').read_bytes()).hexdigest()
    state=ResearchState(path)
    events=[e for e in state.data['journal'] if e['kind']=='tool_executed']
    action=next(e for e in events if e['turn']==turn and e['tool']=='update_research_state')
    store=DocumentStore(state.packet)
    store.read_ids={p['id'] for e in events if e['turn']<turn and e['tool']=='read_context'
                    for p in e['result']['fragments']}
    state.data.update(checked_results={},hypotheses={},findings=[],candidates=build_inventory(store))
    state.data['research_tasks']=build_tasks(store,state.data['candidates'])
    tools=ResearchTools(state,store,None)
    with patch('ayqyn.providers.llm.request_json_api',side_effect=AssertionError('Network forbidden in replay.')):
        first=tools.execute('update_research_state',copy.deepcopy(action['arguments']))
        assert first['accepted_result_ids'],first
        assert first['rejected_results'],first
        assert first['task_update_errors'],first
        records={r['result_id']:copy.deepcopy(r) for r in action['arguments']['result_updates']}
        rejected_ids={e['result_id'] for e in first['rejected_results']}
        for error in first['rejected_results']:
            assert error['code']=='owner_evidence_missing',error
            assert error['required_evidence'],error
            hint=error['required_evidence'][0]
            records[error['result_id']]['finding'][error['field']].append({k:hint[k] for k in ['fragment_id','quote']})
        repair={**copy.deepcopy(action['arguments']),'result_updates':[records[key] for key in rejected_ids],
                'candidate_updates':[],'task_updates':[],'hypothesis_id':None}
        second=tools.execute('update_research_state',repair)
        assert second['accepted'],second
        before=copy.deepcopy(state.data['checked_results'])
        retry=tools.execute('update_research_state',copy.deepcopy(repair))
        assert retry['accepted'] and before==state.data['checked_results']
        for error in first['task_update_errors']:
            assert state.data['research_tasks'][error['task_id']]['status']!='checked'
        final=tools.execute('submit_findings',{'findings':[],
            'saved_result_ids':list(state.data['checked_results']),'outcome':'insufficient_data',
            'gaps':['Offline replay covers one update, not the whole study.'],'reason':'Source-contract replay only.'})
        assert final['accepted'],final
    assert hashlib.sha256((path/'state.json').read_bytes()).hexdigest()==original_hash
    return {'source_run':path.name,'turn':turn,'api_calls':0,'source_run_unchanged':True,
            'first_update':first,'repair':second,'idempotent_retry':True,
            'retained_result_ids':list(state.data['checked_results']),
            'submitted_count':len(state.data['findings']),
            'limitation':'Contract acceptance only, not semantic G01-G15 acceptance.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('run',type=Path)
    parser.add_argument('--turn',type=int,default=4)
    args=parser.parse_args()
    print(json.dumps(replay(args.run,args.turn),ensure_ascii=False,indent=2))
