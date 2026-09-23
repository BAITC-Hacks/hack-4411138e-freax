"""Bound model-visible history while retaining the complete durable audit trail."""
import json
from ayqyn.agent.inventory import task_summary


def compact_messages(state, store):
    history=state.data['messages']
    starts=[i for i,m in enumerate(history) if m['role']=='assistant' and m.get('tool_calls')]
    compact=len(json.dumps(history,ensure_ascii=False))>60000
    start=(starts[-3] if len(starts)>=3 else (starts[0] if starts else len(history))) if compact else 2
    hypotheses=[{k:h[k] for k in ['hypothesis_id','claim','assessment','gaps','revision_reason']}
                | {'supporting_ids':[e['fragment_id'] for e in h['supporting']],
                   'contradicting_ids':[e['fragment_id'] for e in h['contradicting']]}
                for h in state.data['hypotheses'].values()]
    events=[]
    for event in state.data['journal']:
        if event.get('kind')!='tool_executed':continue
        result=event.get('result',{})
        events.append({'turn':event['turn'],'tool':event['tool'],'arguments':event.get('arguments'),
                       'accepted':result.get('accepted'),'error':result.get('error'),
                       'returned_ids':[p['id'] for p in result.get('fragments',result.get('hits',[]))],
                       'next_offset':result.get('next_offset')})
    for event in events:
        if event['tool'] not in {'search','read_context','get_coverage'}:
            event.pop('arguments',None)
    memory={'notice':'Full audit is separate. Saved results retain exact quotes, owners, established change, open question and next step. Reuse saved_result_ids for submission; reread only to check context or new evidence.',
            'hypotheses':hypotheses,'budget':state.data['budget'],'coverage':store.coverage_summary(),
            'research_tasks':task_summary(state,limit=4),
            'function_work':state.function_work_summary(store),
            'work_priority':'Finish a ready comparison, then read a concrete promising candidate, then start a new area. Read candidates are not confirmed matches. Retain contrary evidence; report specific unfinished_work reasons at submission.',
            'checked_results':[{k:v for k,v in r.items() if k!='history'} for r in state.data['checked_results'].values()],
            'ocr_pages':[{'ocr_id':key,'document_id':v['document_id'],'page':v['page'],
                          'fragment_ids':v.get('fragment_ids',[]),'index_status':v.get('index_status'),
                          'verified':False,'notice':'OCR transcription: use read_context on fragment_ids before citation; image accuracy and completeness are unverified.'}
                         for key,v in state.data['ocr_pages'].items()],
            'recent_actions':events[-8:] if compact else [],
            'validation_errors':state.data['validation_errors'],'gaps':state.data['gaps']}
    prefix=[m for m in history[:2] if m['role'] in {'system','user'}]
    if not prefix:start=0
    return prefix+[{'role':'user','content':json.dumps(memory,ensure_ascii=False)}]+history[start:]
