"""Observed effort/coverage, separate from semantic acceptance."""
from collections import Counter
import json


def research_metrics(state):
    events=[e for e in state.data['journal'] if e.get('kind')=='tool_executed']
    reads=[e for e in events if e['tool']=='read_context' and e.get('result',{}).get('fragments')]
    signatures=Counter(json.dumps({k:e['arguments'].get(k,0 if k=='offset' else None) for k in ['fragment_id','scope','offset']},sort_keys=True) for e in reads)
    deliveries=Counter(p['id'] for e in reads for p in e['result']['fragments'])
    records=[r['finding'] for r in state.data['checked_results'].values()
             if r['status']=='checked' and r['finding']['group']=='function']
    function_keys={tuple(' '.join(str(f.get(k) or '').casefold().split()) for k in ['function','owner_before','owner_after']) for f in records}
    # A truncated provider reply spends tokens even when no action is accepted.
    recorded=[]
    incomplete=0
    for path in state.path.glob('turn-*/manifest.json'):
        try:
            usage=json.loads(path.read_text(encoding='utf-8')).get('usage')
            if isinstance(usage,dict):recorded.append(usage)
            else:incomplete+=1
        except (OSError,ValueError):incomplete+=1
    usage=recorded if len(recorded)>=len(state.data['usage']) and recorded else state.data['usage']
    return {'tool_calls':len(events),'search_calls':sum(e['tool']=='search' for e in events),
            'read_calls':len(reads),'exact_repeated_read_calls':sum(n-1 for n in signatures.values()),
            'unique_read_fragments':len(deliveries),'fragment_deliveries':sum(deliveries.values()),
            'repeated_fragment_deliveries':sum(n-1 for n in deliveries.values()),
            'unique_checked_function_records':len(function_keys),
            'function_work_status_counts':dict(Counter(w['status'] for w in state.data['function_work'].values())),
            'task_status_counts':dict(Counter(t['status'] for t in state.data['research_tasks'].values())),
            'prompt_tokens':sum(u.get('prompt_tokens',0) for u in usage),
            'completion_tokens':sum(u.get('completion_tokens',0) for u in usage),
            'cached_prompt_tokens':sum(u.get('prompt_tokens_details',{}).get('cached_tokens',0) for u in usage),
            'usage_source':'provider_manifests' if usage is recorded else 'state',
            'requests_with_unknown_usage':incomplete,
            'stop_status':state.data['status'],'stop_reason':state.data['stop_reason'],
            'limitation':'Function count deduplicates exact normalized function/owner records assessed by the agent, not independent semantic verification. Repeated context fragments may be legitimate headings/neighbor checks.'}
