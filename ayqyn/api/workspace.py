"""Projection for the existing analyst screen, not another analysis pipeline."""
from copy import deepcopy
from ayqyn.documents.store import DocumentStore
from ayqyn.agent.inventory import inventory_summary,task_summary
from ayqyn.agent.metrics import research_metrics


def progress_result(state):
    store=DocumentStore(state.packet)
    store.read_ids=set(state.data['read_ids'])
    events=[]
    for e in state.data['journal']:
        if e.get('kind')!='tool_executed':continue
        result=e.get('result',{})
        arguments=e.get('arguments') or {}
        events.append({'turn':e['turn'],'tool':e['tool'],'query':arguments.get('query'),
                       'fragment_id':arguments.get('fragment_id'),'offset':arguments.get('offset'),
                       'accepted':result.get('accepted'),'partial':result.get('partial',False),'error':result.get('error'),
                       'accepted_result_ids':result.get('accepted_result_ids',[]),
                       'returned_fragments':len(result.get('fragments',result.get('hits',[]))),
                       'errors':result.get('errors',[])})
    return {'id':state.data['id'],'status':state.data['status'],'stop_reason':state.data['stop_reason'],
            'budget':state.data['budget'],'coverage':store.coverage_summary(),
            'inventory':inventory_summary(state,limit=0),'tasks':task_summary(state,limit=0),
            'metrics':research_metrics(state),'actions':events,'gaps':state.data['gaps']}


def workspace_result(state):
    research=progress_result(state)
    mapping={'function':{'preserved':'function_preserved','reworded':'function_reworded','changed':'function_changed','unmatched':'function_unmatched'},
             'structure':{'preserved':'department_retained','added_to_list':'department_added','removed_from_list':'department_removed',
                          'renamed':'reorganization','created':'reorganization','split':'reorganization','merged':'reorganization','unresolved':'structure_unresolved'},
             'risk':{'potential_loss':'function_loss','duplication':'duplication','conflict':'conflict','contradiction':'contradiction','insufficient_data':'risk_insufficient'}}
    findings=[]
    findings_source=state.data['findings']
    if not findings_source and state.data['status'] in {'budget_exhausted','model_error','interrupted'}:
        findings_source=[{**r['finding'],'id':r['result_id'],'draft':True} for r in state.data['checked_results'].values()]
    for f in findings_source:
        findings.append({**deepcopy(f),'title':f['function'],'type':mapping[f['group']][f['category']],
                         'before_ids':[e['fragment_id'] for e in f['before_evidence']],
                         'after_ids':[e['fragment_id'] for e in f['after_evidence']],
                         'method':'llm','reviewed':False,'status':'unknown','note':''})
    documents=[{**deepcopy(d),'side':d['role'],'classification':'manual' if d['role_reason'].startswith('Роль указана') else 'version',
                'classification_reason':d['role_reason']} for d in state.packet['documents']]
    return {'before':state.packet['before'],'after':state.packet['after'],'documents':documents,
            'findings':findings,'mode':'agent','warnings':state.packet['warnings']+state.data['gaps'],
            'research':research,'trace':[],'saved':True,'research_timestamp':state.data['updated_at']}
