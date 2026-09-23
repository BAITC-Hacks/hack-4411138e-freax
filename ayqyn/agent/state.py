"""Durable research state. Evidence validation is not semantic verification."""
import copy
import json
import os
from pathlib import Path
from ayqyn.storage.runs import utc_now

GROUPS = {
    'function': {'preserved','reworded','changed','unmatched'},
    'structure': {'preserved','renamed','created','split','merged','added_to_list','removed_from_list','unresolved'},
    'risk': {'potential_loss','duplication','conflict','contradiction','insufficient_data'},
}


def atomic_json(path, value, secrets=()):
    text=json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)
    for secret in secrets:
        if secret: text=text.replace(secret,'[REDACTED]')
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w',encoding='utf-8') as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class ResearchState:
    def __init__(self, path, packet=None, task=None, budget=None, secrets=()):
        self.path=Path(path)
        self.secrets=tuple(s for s in secrets if s)
        if packet is None:
            self.data=json.loads((self.path/'state.json').read_text(encoding='utf-8'))
            self.packet=json.loads((self.path/'packet.json').read_text(encoding='utf-8'))
            if self.data.get('schema_version')!=1:
                raise ValueError('Неизвестная версия состояния исследования.')
        else:
            self.path.mkdir(parents=True,exist_ok=False)
            self.packet=copy.deepcopy(packet)
            self.data={'schema_version':1,'id':self.path.name,'created_at':utc_now(),'updated_at':utc_now(),
                       'task':task,'status':'preparing','stop_reason':None,'hypotheses':{},'findings':[],
                       'gaps':[],'clarifications':[],'read_ids':[],'coverage':{},'journal':[],
                       'messages':[],'pending_call':None,'validation_errors':[],
                       'budget':{**budget,'model_calls_used':0,'tool_calls_used':0,'elapsed_seconds':0},
                       'index':{},'usage':[]}
            atomic_json(self.path/'packet.json',self.packet,self.secrets)
            self.save()

        self.data.setdefault('candidates',{})
        self.data.setdefault('research_tasks',{})
        self.data.setdefault('checked_results',{})
        self.data.setdefault('function_work',{})
        self.data.setdefault('unfinished_work',[])

    def save(self):
        self.data['updated_at']=utc_now()
        atomic_json(self.path/'state.json',self.data,self.secrets)

    def event(self, kind, **fields):
        self.data['journal'].append({'sequence':len(self.data['journal'])+1,'time':utc_now(),'kind':kind,**copy.deepcopy(fields)})

    def update_function_work(self,store,values):
        """Persist model-identified functions; read candidates never auto-confirm a match."""
        if not isinstance(values,list) or len(values)>12:
            return {'accepted_work_ids':[],'work_errors':[{'work_id':None,'errors':['Expected at most 12 compact function work updates.']}]}
        accepted,errors=[],[]
        fields={'work_id','function','before_ids','after_ids','candidate_ids','counter_evidence_ids',
                'open_question','next_action','status','result_id','resolution'}
        statuses={'ready_to_compare','needs_read','needs_search','completed','insufficient_data'}
        ids=[v.get('work_id') for v in values if isinstance(v,dict) and isinstance(v.get('work_id'),str)]
        duplicates={key for key in ids if ids.count(key)>1}
        for value in values:
            key=value.get('work_id') if isinstance(value,dict) else None
            issues=[]
            if not isinstance(value,dict) or set(value)!=fields:
                errors.append({'work_id':key,'errors':['Invalid function work fields.']});continue
            if not isinstance(key,str) or not 1<=len(key)<=80 or value['status'] not in statuses:
                errors.append({'work_id':key,'errors':['Invalid function work identity/status.']});continue
            if key in duplicates:
                errors.append({'work_id':key,'errors':['Duplicate work_id in one update; no version was selected.']});continue
            for field in ['function','open_question','next_action']:
                if not isinstance(value[field],str) or not value[field].strip() or len(value[field])>1000:
                    issues.append('Function work requires concise '+field+'.')
            for field in ['before_ids','after_ids','candidate_ids','counter_evidence_ids']:
                ids=value[field]
                if not isinstance(ids,list) or len(ids)>20 or any(not isinstance(i,str) or i not in store.fragments for i in ids):
                    issues.append('Unknown or excessive fragment IDs in '+field+'.');continue
                if len(set(ids))!=len(ids):issues.append('Duplicate IDs in '+field+'.')
                if field!='candidate_ids' and not set(ids)<=store.read_ids:
                    issues.append('Read the full context before assigning '+field+'.')
                if field in {'before_ids','after_ids'} and any(store.documents[store.fragments[i]['document_id']]['role'] not in {field.split('_')[0],'common'} for i in ids):
                    issues.append('Wrong document side in '+field+'.')
            if issues:
                errors.append({'work_id':key,'errors':issues});continue
            previous=self.data['function_work'].get(key)
            if previous and normalized_function(previous['function'])!=normalized_function(value['function']):
                issues.append('A work_id cannot replace a different function. Retain the original question and use a new ID for another function.')
            if not (value['before_ids'] or value['after_ids']):
                issues.append('Identify the function in at least one read source before creating work.')
            if value['status']=='ready_to_compare' and not (value['before_ids'] and value['after_ids']):
                issues.append('Ready to compare requires read sources on both sides, not just search hits.')
            if value['status']=='needs_read' and not value['candidate_ids']:
                issues.append('Needs read requires a concrete candidate or continuation ID.')
            closed=value['status'] in {'completed','insufficient_data'}
            if closed:
                record=self.data['checked_results'].get(value['result_id']) if isinstance(value['result_id'],str) else None
                if not record:
                    issues.append('Closing work requires an accepted saved result_id, not an attempted update.')
                elif normalized_function(record['finding']['function'])!=normalized_function(value['function']):
                    issues.append('The saved result must describe this function; keep its function name stable.')
                elif value['status']=='completed' and record['status']!='checked':
                    issues.append('An unresolved saved result cannot close work as completed.')
                if record:
                    for side in ['before','after']:
                        source_ids={e['fragment_id'] for e in record['finding'][side+'_evidence']}
                        if not source_ids<=set(value[side+'_ids']):
                            issues.append('Closing work must include every saved result source in '+side+'_ids; a result for another assignment cannot close this work.')
                if not isinstance(value['resolution'],str) or not value['resolution'].strip() or len(value['resolution'])>1500:
                    issues.append('Closed work needs a factual resolution, including remaining uncertainty.')
            elif value['result_id'] is not None or value['resolution'] is not None:
                issues.append('Open work has no final result_id or resolution; retain the open question.')
            duplicate=next((wid for wid,w in self.data['function_work'].items() if wid!=key
                            and normalized_function(w['function'])==normalized_function(value['function'])
                            and set(w['before_ids'])==set(value['before_ids']) and set(w['after_ids'])==set(value['after_ids'])),None)
            if duplicate:issues.append('This function/source work already exists: '+duplicate)
            staged={**self.data['function_work'],key:value}
            if len(staged)>40 or len(json.dumps(staged,ensure_ascii=False))>48000:
                issues.append('Function work exceeds compact-state limits; finish started comparisons before opening more.')
            if issues:errors.append({'work_id':key,'errors':issues})
            else:
                self.data['function_work'][key]=copy.deepcopy(value);accepted.append(key)
        return {'accepted_work_ids':accepted,'work_errors':errors}

    def function_work_summary(self,store):
        priorities={'ready_to_compare':0,'needs_read':1,'needs_search':2,'completed':3,'insufficient_data':3}
        result=[]
        for work in sorted(self.data['function_work'].values(),key=lambda w:priorities[w['status']]):
            if work['status'] in {'completed','insufficient_data'}:
                result.append({k:work[k] for k in ['work_id','function','status','result_id','resolution']})
            else:
                entry=copy.deepcopy(work)
                entry['unread_candidate_ids']=[i for i in work['candidate_ids'] if i not in store.read_ids]
                entry['read_candidate_ids']=[i for i in work['candidate_ids'] if i in store.read_ids]
                entry['notice']='Readiness is an agent assessment, not a verified match. A read candidate still needs interpretation.'
                result.append(entry)
        return result

    def evidence_errors(self, store, evidence, side=None):
        errors=[]
        if not isinstance(evidence,list) or len(evidence)>20:
            return ['Ожидается до 20 ссылок на источники.']
        for e in evidence:
            if not isinstance(e,dict) or set(e)!={'fragment_id','quote'}:
                errors.append('Источник должен содержать fragment_id и quote.'); continue
            if not isinstance(e['fragment_id'],str) or not isinstance(e['quote'],str) or len(e['quote'].strip())<5:
                errors.append('Нужны идентификатор и содержательная дословная цитата.'); continue
            checked=store.check_evidence(e['fragment_id'],e['quote'])
            if not checked['exists']:
                errors.append(f'Цитата не существует: {e["fragment_id"]}.'); continue
            if not checked['was_read']:
                errors.append(f'Сначала прочитайте контекст: {e["fragment_id"]}.')
            if side:
                doc=store.documents[checked['document_id']]
                if doc['role'] not in {side,'common'}:
                    errors.append(f'Источник не относится к стороне {side}: {e["fragment_id"]}.')
        return errors

    def update_hypothesis(self, store, value):
        required={'hypothesis_id','claim','assessment','supporting','contradicting','gaps','revision_reason'}
        if set(value)!=required: raise ValueError('Неполные или неизвестные поля гипотезы.')
        if not isinstance(value['hypothesis_id'],str) or not 1<=len(value['hypothesis_id'])<=80:
            raise ValueError('Некорректный ID гипотезы.')
        if value['assessment'] not in {'open','supported','refuted','uncertain'}:
            raise ValueError('Некорректная оценка гипотезы.')
        for field in ['claim','revision_reason']:
            if not isinstance(value[field],str) or not 1<=len(value[field])<=6000:
                raise ValueError('Нужны формулировка гипотезы и основание изменения.')
        validate_strings(value['gaps'],'gaps')
        errors=self.evidence_errors(store,value['supporting'])+self.evidence_errors(store,value['contradicting'])
        if value['assessment']=='supported' and not value['supporting']:
            errors.append('Для поддержанной гипотезы нужны свидетельства.')
        if value['assessment']=='refuted' and not value['contradicting']:
            errors.append('Для опровергнутой гипотезы нужны опровергающие свидетельства.')
        if errors: return {'accepted':False,'errors':errors}
        existing=self.data['hypotheses'].get(value['hypothesis_id'])
        if not existing and len(self.data['hypotheses'])>=30:
            return {'accepted':False,'errors':['Достигнут лимит 30 гипотез.']}
        history=existing['history'][:] if existing else []
        revision={**copy.deepcopy(value),'recorded_at':utc_now(),'revision':len(history)+1}
        history.append(revision)
        stored={**revision,'history':history}
        self.data['hypotheses'][value['hypothesis_id']]=stored
        return {'accepted':True,'hypothesis':revision,'notice':'Это оценка агента, не подтверждение человеком.'}

    def submit(self, store, findings, outcome, gaps, reason, *, draft=False):
        if outcome not in {'completed','insufficient_data'}: raise ValueError('Неизвестный итог.')
        validate_strings(gaps,'gaps')
        if not isinstance(reason,str) or not reason.strip() or len(reason)>6000:
            raise ValueError('Нужна причина завершения.')
        if not isinstance(findings,list) or len(findings)>40:
            raise ValueError('Ожидается до 40 выводов.')
        errors=[]
        coverage=store.get_coverage()
        uncertain=not self.packet.get('ready',False)
        required={'group','category','function','owner_before','owner_after','before_evidence','after_evidence','explanation','limitations'}
        seen=set()
        for number,f in enumerate(findings,1):
            issues=[]
            details=[]
            if not isinstance(f,dict) or not required<=set(f) or set(f)-required-{'claim_checks','assertion_type','comparison'}:
                errors.append({'finding':number,'errors':['Неполные/неизвестные поля вывода.']}); continue
            identity=tuple(' '.join(str(f.get(k) or '').casefold().split()) for k in ['group','category','function','owner_before','owner_after'])
            if identity in seen:
                issues.append('Duplicate function/owner assertion. Submit either the new finding or its saved_result_id, not both.')
            seen.add(identity)
            if f['group'] not in GROUPS or f['category'] not in GROUPS.get(f['group'],set()):
                issues.append('Категория не соответствует группе результата. Для группы '+str(f['group'])+
                              ' допустимы: '+', '.join(sorted(GROUPS.get(f['group'],set())))+'.')
            for field in ['function','explanation']:
                if not isinstance(f[field],str) or not f[field].strip() or len(f[field])>6000:
                    issues.append('Нужны конкретная функция/объект и объяснение.')
            if f['group']=='function' and (self.data.get('research_policy',0)>=4 or f.get('comparison') is not None):
                for message in function_comparison_errors(f):
                    issues.append(message)
                    details.append({'field':'comparison','code':'function_comparison_invalid','message':message,'required_evidence':[]})
            try: validate_strings(f['limitations'],'limitations',minimum=1)
            except ValueError as exc: issues.append(str(exc))
            for side in ['before','after']:
                ev=f[side+'_evidence']
                issues.extend(self.evidence_errors(store,ev,side if f['category']!='insufficient_data' else None))
                owner=f['owner_'+side]
                if owner is not None:
                    if not isinstance(owner,str) or not owner.strip() or len(owner)>1000:
                        issues.append('Владелец должен быть названием субъекта или null.')
                    elif not isinstance(ev,list) or not any(isinstance(e,dict) and isinstance(e.get('quote'),str)
                                                            and ' '.join(owner.split()) in ' '.join(e['quote'].split()) for e in ev):
                        message='Название владельца должно дословно входить в цитируемое доказательство: '+side
                        issues.append(message)
                        details.append({'field':side+'_evidence','code':'owner_evidence_missing','message':message,
                                        'required_evidence':store.owner_evidence_candidates(ev,owner)})
            left,right=f['before_evidence'],f['after_evidence']
            checks=f.get('claim_checks',[])
            if not isinstance(checks,list) or len(checks)>6:
                issues.append('claim_checks: expected up to 6 evidence checks.')
                checks=[]
            checked_kinds=set()
            duplication_assignments=[]
            for check in checks:
                if not isinstance(check,dict) or set(check)!={'kind','evidence','result'}:
                    issues.append('Invalid claim check.');continue
                kind=check['kind']
                if kind not in {'prior_assignment','retained_assignment','creation_basis','comparison','duplication_assignment'}:
                    issues.append('Unknown claim check.');continue
                side={'prior_assignment':'before','retained_assignment':'after','creation_basis':'after','duplication_assignment':'after'}.get(kind)
                check_errors=self.evidence_errors(store,check['evidence'],side)
                issues.extend(check_errors)
                if not check['evidence'] or not isinstance(check['result'],str) or not check['result'].strip():
                    issues.append('Each claim check needs read evidence and a factual result.')
                elif not check_errors:
                    checked_kinds.add(kind)
                    if kind=='duplication_assignment':
                        duplication_assignments.append(assignment_source_ids(store,check['evidence']))
            assertion=f.get('assertion_type','observation')
            if assertion not in {'observation','assignment_change','exclusive_transfer'}:
                issues.append('Unknown assertion_type.')
            if assertion in {'assignment_change','exclusive_transfer'}:
                if f['group']!='function' or f['category']!='changed' or not (left and right and f['owner_before'] and f['owner_after'] and f['owner_before']!=f['owner_after']):
                    issues.append('An assignment change needs two explicit assignments to distinct owners.')
            if self.data.get('research_policy',0)>=2:
                if assertion=='exclusive_transfer':
                    if not {'prior_assignment','retained_assignment'}<=checked_kinds:
                        issues.append('Exclusive transfer requires prior_assignment and retained_assignment checks. Two assignments alone support assignment_change, not exclusivity.')
                    if not coverage['after_fully_read'] or gaps:
                        issues.append('Exclusive transfer cannot be established while the new bundle remains unread or has unresolved gaps.')
                if f['category'] in {'created','split','merged'} and 'creation_basis' not in checked_kinds:
                    issues.append('Cite the operative reorganization basis through creation_basis; a new name alone supports added_to_list, not creation.')
            if not (left or right): issues.append('Нужен хотя бы один источник.')
            if f['category'] in {'preserved','reworded','changed','renamed','split','merged'} and not (left and right):
                issues.append('Для сопоставленного изменения нужны обе редакции.')
            if f['category'] in {'duplication','conflict','contradiction'}:
                if not isinstance(right,list) or len({e.get('fragment_id') for e in right if isinstance(e,dict)})<2:
                    issues.append('Нужны два различных источника обязанностей в новой редакции.')
            if f['category']=='duplication' and not any(a-b and b-a for a in duplication_assignments for b in duplication_assignments):
                issues.append('Duplication needs two duplication_assignment checks with distinct action sources in after. Compare actors, operation, object, stage and conditions. A duty to detect duplication is not an instance of duplication.')
            if f['category']=='potential_loss':
                if not left: issues.append('Нужна прежняя обязанность.')
                if not coverage['after_fully_read'] or gaps or any(h['gaps'] for h in self.data['hypotheses'].values() if h['assessment']!='refuted'):
                    issues.append('Нельзя выводить потенциальную потерю при непрочитанном after или нерешённых пробелах.')
            if uncertain and f['category'] not in {'insufficient_data','unmatched','unresolved'}:
                issues.append('Комплект имеет ошибки или неопределённые роли; допустим только ограниченный итог о недостатке данных.')
            if issues: errors.append({'finding':number,'errors':issues,'details':details})
        hypothesis_gaps=any(h['gaps'] for h in self.data['hypotheses'].values() if h['assessment']!='refuted')
        tasks=self.data['research_tasks']
        pending=sum(t['status']!='checked' for t in tasks.values()) if tasks else sum(c['status'] in {'pending','unresolved'} for c in self.data['candidates'].values())
        if outcome=='completed' and pending:
            errors.append({'finding':None,'errors':[f'{pending} research tasks/candidates remain unverified. Return insufficient_data and this coverage limitation; reading alone is not checking functions.']})
        if outcome=='completed' and (uncertain or not coverage['after_fully_read'] or gaps or hypothesis_gaps):
            errors.append({'finding':None,'errors':['Полная проверка не завершена: используйте insufficient_data и назовите пробелы.']})
        if not draft: self.data['validation_errors']=errors
        if errors: return {'accepted':False,'errors':errors,'instruction':'Исправьте данные или завершите с недостаточностью; ссылки не доказывают интерпретацию.'}
        if draft:
            return {'accepted':True,'notice':'Source-validated agent assessment, not independent semantic verification.'}
        self.data['findings']=[{**copy.deepcopy(f),'id':f'finding-{n}','evidence_validation':'exact_quotes_verified',
                                'human_review':{'status':'unreviewed','comment':''}} for n,f in enumerate(findings,1)]
        self.data.update(status=outcome,stop_reason=reason,gaps=gaps,coverage=coverage)
        return {'accepted':True,'count':len(findings),'outcome':outcome,
                'notice':'Источники существуют. Правильность интерпретации требует отдельной проверки.'}

    def save_checked_results(self,store,values):
        """Each independently evidenced record commits atomically, not the whole batch."""
        maximum=1 if self.data.get('research_policy',0)>=4 else 20
        if not isinstance(values,list) or len(values)>maximum:
            return {'accepted':False,'errors':[f'Expected up to {maximum} result updates; save one function before switching.']}
        accepted,rejected=[],[]
        for value in values:
            result=self._save_checked_result(store,value)
            if result['accepted']:
                accepted.extend(result['saved_result_ids'])
            else:
                key=value.get('result_id') if isinstance(value,dict) else None
                for error in result['errors']:
                    details=error.get('details',[]) if isinstance(error,dict) else []
                    if details:
                        rejected.extend({'result_id':key,**detail} for detail in details)
                        described={detail['message'] for detail in details}
                        rejected.extend({'result_id':key,'field':'finding','code':'validation_error',
                                         'message':message,'required_evidence':[]} for message in error['errors'] if message not in described)
                    else:
                        rejected.append({'result_id':key,'field':'finding','code':'validation_error',
                                         'message':error,'required_evidence':[]})
        accepted=list(dict.fromkeys(accepted))
        return {'accepted':not rejected,'accepted_result_ids':accepted,'saved_result_ids':accepted,
                'rejected_results':rejected,'errors':rejected}

    def _save_checked_result(self,store,value):
        if not isinstance(value,dict) or set(value)!={'result_id','finding','status','open_question','next_step'}:
            return {'accepted':False,'errors':['Invalid saved-result fields.']}
        key=value['result_id']
        if not isinstance(key,str) or not 1<=len(key)<=80 or value['status'] not in {'checked','partial','insufficient_data'}:
            return {'accepted':False,'errors':['Invalid result identity/status.']}
        errors=[]
        for field in ['open_question','next_step']:
            if value[field] is not None and (not isinstance(value[field],str) or not 1<=len(value[field])<=1500):
                errors.append('Invalid '+field)
        finding=value['finding']
        checked=self.submit(store,[finding],'insufficient_data',[], 'Validate durable result.',draft=True)
        if not checked['accepted']:errors.extend(checked['errors'])
        if errors:return {'accepted':False,'errors':errors}
        if value['status']=='checked' and finding['category'] in {'unmatched','unresolved','insufficient_data'}:
            return {'accepted':False,'errors':['Unresolved correspondence is not a checked change.']}
        staged=copy.deepcopy(self.data['checked_results'])
        signature=lambda f:tuple(' '.join(str(f.get(k) or '').casefold().split()) for k in ['group','function','owner_before','owner_after'])
        duplicate=next((rid for rid,record in staged.items() if rid!=key and signature(record['finding'])==signature(finding)),None)
        if duplicate:
            return {'accepted':False,'errors':['This function/owner record already exists as '+duplicate+'; revise that ID.']}
        previous=staged.get(key,{})
        for work in self.data['function_work'].values():
            if work['result_id']==key and (normalized_function(work['function'])!=normalized_function(finding['function'])
                    or work['status']=='completed' and value['status']!='checked'):
                return {'accepted':False,'errors':['Reopen linked function work '+work['work_id']+' before replacing its completed result with a different or unresolved function.']}
        if previous and all(previous[k]==v for k,v in value.items()):
            return {'accepted':True,'saved_result_ids':[key]}
        revision={**copy.deepcopy(value),'recorded_at':utc_now(),'evidence_validation':'exact_quotes_verified'}
        staged[key]={**revision,'history':previous.get('history',[])+[revision]}
        if len(staged)>40 or len(json.dumps([{k:v for k,v in r.items() if k!='history'} for r in staged.values()],ensure_ascii=False))>60000:
            errors.append('Saved results exceed the compact-state bound; use concise exact quotes, not full paragraphs.')
        if errors:return {'accepted':False,'errors':errors}
        self.data['checked_results']=staged
        return {'accepted':True,'saved_result_ids':[value['result_id']]}


def assignment_source_ids(store,evidence):
    """A continued clause is not a bare heading; this is structural, not semantic proof."""
    result=set()
    for item in evidence:
        key=item['fragment_id'];block=store.fragments[key]
        if block.get('block_type')=='heading':continue
        if block['text'].rstrip().endswith(':'):
            section=store._sections[block['document_id']][store._fragment_sections[key]]
            continuation={i for i in section['fragment_ids'] if i!=key
                          and store.fragments[i].get('block_type') not in {'heading','clause'}}
            if not continuation or not continuation<=store.read_ids:continue
        result.add(key)
    return result


def normalized_function(value):
    return ' '.join(value.casefold().split())


def function_comparison_errors(finding):
    """Check the declared comparison contract, not semantic entailment of its sources."""
    value=finding.get('comparison')
    fields={'action','object','conditions','stage'}
    if not isinstance(value,dict) or set(value)!={'before','after','changed_fields'}:
        return ['comparison: describe one function on both sides and its changed_fields.']
    for side in ['before','after']:
        record=value[side]
        if not isinstance(record,dict) or set(record)!=fields:
            return ['comparison: each side needs action, object, conditions and stage.']
        for field,text in record.items():
            if text is not None and (not isinstance(text,str) or not text.strip() or len(text)>1000):
                return ['comparison: each dimension must be concise text or null if unknown.']
        if finding['category']!='unmatched' and (not record['action'] or not record['object']):
            return ['comparison: a matched function needs action and object on both sides.']
    changed=value['changed_fields']
    if not isinstance(changed,list) or any(not isinstance(x,str) or x not in fields|{'owner'} for x in changed) or len(set(changed))!=len(changed):
        return ['comparison: use distinct action/object/owner/conditions/stage changed_fields.']
    errors=[]
    if finding['category']=='changed' and not changed:
        errors.append('comparison: changed requires a concrete changed field, not a changed section.')
    if finding['category'] in {'preserved','reworded'} and changed:
        errors.append('comparison: preserved/reworded cannot claim a substantive field change.')
    if finding.get('assertion_type') in {'assignment_change','exclusive_transfer'} and 'owner' not in changed:
        errors.append('comparison: an assignment change must identify owner as changed.')
    for field in changed:
        before,after=([finding['owner_before'],finding['owner_after']] if field=='owner'
                      else [value['before'][field],value['after'][field]])
        if before is None or after is None:
            errors.append('comparison: unknown '+field+' is not an established difference; retain an unresolved question.')
        elif ' '.join(before.casefold().split())==' '.join(after.casefold().split()):
            errors.append('comparison: identical '+field+' values cannot explain a change.')
    return errors


def validate_strings(value, name, minimum=0):
    if not isinstance(value,list) or not minimum<=len(value)<=20 or not all(isinstance(v,str) and 0<len(v)<=3000 for v in value):
        raise ValueError(f'{name}: нужен список содержательных строк (до 20).')
