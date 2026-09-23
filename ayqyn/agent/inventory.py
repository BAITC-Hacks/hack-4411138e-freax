"""Source-section checklist, not an automatically verified function register."""
from collections import Counter, defaultdict
import re


def text_key(text):
    # Numbering is navigation, not evidence of functional change.
    return ' '.join(re.sub(r'^\s*\d+(?:\.\d+)*\.?\s*', '', text).casefold().split())


def build_inventory(store):
    records=[]
    for doc in store.documents.values():
        for section in store._sections[doc['id']].values():
            ids=section['fragment_ids']
            p=store.fragments[ids[0]]
            parents=[]
            parent=store._parents[p['id']]
            while parent:
                parents.append(parent)
                parent=store._parents[parent]
            text=' '.join(store.fragments[key]['text'] for key in ids)
            context=' | '.join(store.fragments[key]['text'] for key in reversed(parents))
            records.append({'id':f'c{len(records)+1}','document_id':doc['id'],'role':doc['role'],
                            'section':section['section'],'fragment_ids':ids,'parent_ids':parents,
                            'preview':text[:240],'context_preview':context[-240:],
                            'status':'pending','text_match_ids':[],
                            '_key':(text_key(text),tuple(text_key(store.fragments[key]['text']) for key in reversed(parents)))})
    by_key=defaultdict(list)
    by_body=defaultdict(list)
    by_section=defaultdict(list)
    for item in records:
        by_key[(item['role'],item['_key'])].append(item)
        by_body[(item['role'],item['_key'][0])].append(item)
        by_section[(item['role'],item['section'])].append(item)
    for item in records:
        if item['role'] in {'before','after'}:
            other='after' if item['role']=='before' else 'before'
            matches=by_key[(other,item['_key'])]
            item['text_match_count']=len(matches)
            item['text_match_ids']=[x['id'] for x in matches[:8]]
            body_matches=by_body[(other,item['_key'][0])]
            body_ids={x['id'] for x in body_matches}
            same_number=[x for x in by_section[(other,item['section'])] if x['id'] not in body_ids]
            item['context_changed']=bool(body_matches) and not item['text_match_ids']
            item['comparison_hints']=[{'candidate_id':x['id'],'fragment_id':x['fragment_ids'][0],
                                      'basis':'equal_body' if x in body_matches else 'same_number_navigation_only',
                                      'preview':x['preview'],'context':x['context_preview']}
                                     for x in (body_matches+same_number)[:2]]
    for item in records:
        del item['_key']
    return {item['id']:item for item in records}


def inventory_summary(state, offset=0, limit=12):
    records=list(state.data.get('candidates',{}).values())
    pending=[r for r in records if r['status']=='pending']
    pending.sort(key=lambda r:(bool(r['text_match_ids']),not r.get('context_changed',False),not bool(re.fullmatch(r'\d+\.\d+(?:\.\d+)*',r['section'])),r['role']!='before',int(r['id'][1:])))
    regions={}
    for r in records:
        key=(r['role'],r['section'].split('.')[0])
        region=regions.setdefault(key,{'role':r['role'],'section':key[1],'units':0,'unmatched_text':0,'context_changed':0})
        region['units']+=1
        region['unmatched_text']+=not bool(r['text_match_ids'])
        region['context_changed']+=r.get('context_changed',False)
    return {'total':len(records),'status_counts':dict(Counter(r['status'] for r in records)),
            'text_match_candidates':sum(bool(r['text_match_ids']) for r in records),
            'pending_count':len(pending),'offset':offset,
            'next_offset':offset+limit if offset+limit<len(pending) else None,
            'regions':list(regions.values()),
            'pending':[{k:r[k] for k in ['id','role','section','fragment_ids','preview','context_preview','text_match_ids','text_match_count','comparison_hints','context_changed'] if k in r}
                       for r in pending[offset:offset+limit]],
            'limitation':'Checklist of source sections, NOT a complete extracted function register. Text matches include structural parents but do not establish semantic equivalence. Pending sections are not verified.'}


def update_candidates(state, store, values):
    errors=[]
    if not isinstance(values,list) or len(values)>40:
        return {'accepted':False,'errors':['At most 40 candidate updates.']}
    for value in values:
        if set(value)!={'candidate_id','status','summary','evidence'}:
            errors.append('Invalid candidate fields.');continue
        candidate=state.data.get('candidates',{}).get(value['candidate_id'])
        if not candidate:
            errors.append('Unknown candidate: '+str(value['candidate_id']));continue
        if value['status'] not in {'reviewed','unresolved','not_function'} or not value['summary'].strip():
            errors.append('Candidate needs assessment and summary.');continue
        errors.extend(state.evidence_errors(store,value['evidence']))
        if not all(key in store.read_ids for key in candidate['fragment_ids']):
            errors.append('Read all candidate continuations: '+candidate['id'])
        if not any(e['fragment_id'] in candidate['fragment_ids'] for e in value['evidence']):
            errors.append('Cite the candidate itself: '+candidate['id'])
    if errors: return {'accepted':False,'errors':errors}
    for value in values:
        candidate=state.data['candidates'][value['candidate_id']]
        candidate.setdefault('history',[]).append({k:v for k,v in value.items() if k!='candidate_id'})
        candidate.update({k:v for k,v in value.items() if k!='candidate_id'})
    return {'accepted':True,'updated':[v['candidate_id'] for v in values]}


def build_tasks(store,candidates):
    """Group by explicit section hierarchy/table, without inferring a legal owner."""
    tasks={}
    for doc in store.documents.values():
        members=[c for c in candidates.values() if c['document_id']==doc['id']]
        groups={}
        for c in members:
            fragment=store.fragments[c['fragment_ids'][0]]
            if fragment.get('table_id'):
                anchor=next(p['id'] for p in doc['paragraphs'] if p.get('table_id')==fragment['table_id'])
            else:
                # Use actual ancestry, never a global number lookup: a table of
                # contents or an appendix may repeat the same section numbers.
                chain=[fragment['id']]+c['parent_ids']
                anchors=[key for key in chain if re.fullmatch(r'\d+(?:\.\d+)?',store.fragments[key].get('section',''))
                         and store._children.get(key)]
                anchor=anchors[0] if anchors else (c['parent_ids'][-1] if c['parent_ids'] else doc['paragraphs'][0]['id'])
            groups.setdefault(anchor,[]).append(c)
        for anchor,group in groups.items():
            seed=store.fragments[anchor]
            identifier=f't{len(tasks)+1}'
            changed=sum(not bool(c['text_match_ids']) for c in group)
            tasks[identifier]={'id':identifier,'document_id':doc['id'],'role':doc['role'],
                'title':seed['text'],'section':seed.get('section',''),'anchor_id':anchor,
                'candidate_ids':[c['id'] for c in group],
                'fragment_ids':[key for c in group for key in c['fragment_ids']],
                'status':'not_checked','reviewed_candidate_ids':[],
                'open_questions':[],'next_step':None,'summary':'',
                'text_changed_units':changed,'context_changed_units':sum(c.get('context_changed',False) for c in group),
                'priority':changed/max(1,len(group))**0.5}
    for task in tasks.values():
        others=[t for t in tasks.values() if t['role'] in {'before','after'} and t['role']!=task['role']]
        hints=[t for t in others if text_key(t['title'])==text_key(task['title'])]
        hints+=[t for t in others if t['section']==task['section'] and t not in hints]
        task['comparison_hints']=[{'task_id':t['id'],'anchor_id':t['anchor_id'],'title':t['title'],
                                  'basis':'heading_or_number_navigation_only'} for t in hints[:2]]
    return tasks


def task_summary(state,offset=0,limit=8,task_id=None):
    tasks=list(state.data.get('research_tasks',{}).values())
    if task_id:
        task=state.data['research_tasks'].get(task_id)
        if not task: raise ValueError('Unknown research task.')
        members=[state.data['candidates'][key] for key in task['candidate_ids']]
        return {'task':{k:task[k] for k in ['id','title','role','status','anchor_id','reviewed_candidate_ids','open_questions','next_step']},
                'members':[{k:c[k] for k in ['id','section','fragment_ids','preview','status']} for c in members[offset:offset+24]],
                'next_offset':offset+24 if offset+24<len(members) else None}
    pending=[t for t in tasks if t['status']!='checked']
    pending.sort(key=lambda t:(-t['priority'],t['role']!='before',int(t['id'][1:])))
    fields=['id','title','role','section','anchor_id','status','text_changed_units','context_changed_units','comparison_hints','open_questions','next_step']
    return {'total':len(tasks),'status_counts':dict(Counter(t['status'] for t in tasks)),
            'pending_count':len(pending),'tasks':[{**{k:t[k] for k in fields},'source_units':len(t['candidate_ids']),
                'reviewed_units':len(t['reviewed_candidate_ids'])} for t in pending[offset:offset+limit]],
            'next_offset':offset+limit if limit and offset+limit<len(pending) else None,
            'limitation':'Source-derived heading/section groups, not inferred legal owners. Text-change counts prioritize investigation, not conclusions. checked requires all member units read and explicitly assessed.'}


def update_tasks(state,store,values):
    from copy import deepcopy
    staged=deepcopy(state.data['research_tasks'])
    errors=[]
    for value in values:
        task=staged.get(value['task_id'])
        if not task:
            errors.append('Unknown task: '+value['task_id']);continue
        reviewed=set(task['reviewed_candidate_ids'])|set(value['reviewed_candidate_ids'])
        if reviewed-set(task['candidate_ids']):
            errors.append('Reviewed units must belong to '+task['id']);continue
        unread=[key for key in reviewed if not set(state.data['candidates'][key]['fragment_ids'])<=store.read_ids]
        if unread:
            errors.append('Read every continuation before assessing units: '+', '.join(unread));continue
        if value['status']=='checked' and (reviewed!=set(task['candidate_ids']) or value['open_questions']):
            errors.append('Cannot close '+task['id']+': every unit must be read/assessed and open questions resolved. Use partial or insufficient_data.');continue
        if value['status']=='not_checked' and reviewed:
            errors.append('A task with assessments is at least partial.');continue
        task.update(status=value['status'],reviewed_candidate_ids=[key for key in task['candidate_ids'] if key in reviewed],
                    summary=value['summary'],open_questions=value['open_questions'],next_step=value['next_step'])
    if errors:return {'accepted':False,'errors':errors}
    state.data['research_tasks']=staged
    return {'accepted':True,'updated_task_ids':[v['task_id'] for v in values]}
