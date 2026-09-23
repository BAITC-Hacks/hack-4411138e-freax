"""Bounded research tools, including optional, unverified local page OCR."""
import hashlib
import re
from ayqyn.agent.state import GROUPS
from ayqyn.agent.inventory import inventory_summary,update_candidates,task_summary,update_tasks
from copy import deepcopy


def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


TEXT={'type':'string'}
NULL_TEXT={'type':['string','null']}
STRINGS={'type':'array','items':TEXT}
EVIDENCE={'type':'array','items':obj({'fragment_id':TEXT,'quote':TEXT})}
CHECKS={'type':'array','items':obj({'kind':{'type':'string','enum':['prior_assignment','retained_assignment','creation_basis','comparison','duplication_assignment']},'evidence':EVIDENCE,'result':TEXT})}
UPDATES={'type':'array','items':obj({'candidate_id':TEXT,'status':{'type':'string','enum':['reviewed','unresolved','not_function']},'summary':TEXT,'evidence':EVIDENCE})}
FUNCTION_SIDE=obj({key:NULL_TEXT for key in ['action','object','conditions','stage']})
COMPARISON={**obj({'before':FUNCTION_SIDE,'after':FUNCTION_SIDE,
                  'changed_fields':{'type':'array','items':{'type':'string','enum':['action','object','owner','conditions','stage']}}}),
            'type':['object','null'],
            'description':'One function only. Describe action/object/conditions/stage on each side; null means unknown, not absent. Owners and exact sources are separate finding fields. changed_fields describes substantive differences, not wording or numbering.'}
FINDING=obj({'group':{'type':'string','enum':list(GROUPS)},
             'category':{'type':'string','enum':sorted(set.union(*GROUPS.values())),
                         'description':'; '.join(group+': '+', '.join(sorted(values)) for group,values in GROUPS.items())},
             'assertion_type':{'type':'string','enum':['observation','assignment_change','exclusive_transfer']},
             'function':TEXT,'owner_before':NULL_TEXT,'owner_after':NULL_TEXT,
             'before_evidence':EVIDENCE,'after_evidence':EVIDENCE,'explanation':TEXT,'limitations':STRINGS,'claim_checks':CHECKS,
             'comparison':COMPARISON})
RESULT_UPDATES={'type':'array','maxItems':1,'items':obj({'result_id':TEXT,'finding':FINDING,
                'status':{'type':'string','enum':['checked','partial','insufficient_data']},
                'open_question':NULL_TEXT,'next_step':NULL_TEXT})}
TASK_UPDATES={'type':'array','items':obj({'task_id':TEXT,
              'status':{'type':'string','enum':['not_checked','partial','checked','insufficient_data']},
              'reviewed_candidate_ids':STRINGS,'summary':TEXT,'open_questions':STRINGS,'next_step':NULL_TEXT})}
WORK_UPDATES={'type':'array','maxItems':12,
    'description':'Register distinct functions identified in read sources, even before a search. Keep function names stable. Closing requires a saved result and factual resolution; contract acceptance is not semantic verification.',
    'items':obj({'work_id':TEXT,'function':TEXT,
    'before_ids':STRINGS,'after_ids':STRINGS,'candidate_ids':STRINGS,'counter_evidence_ids':STRINGS,
    'open_question':TEXT,'next_action':TEXT,
    'status':{'type':'string','enum':['ready_to_compare','needs_read','needs_search','completed','insufficient_data']},
    'result_id':NULL_TEXT,'resolution':NULL_TEXT})}
UNFINISHED={'type':'array','maxItems':40,'description':'One short factual reason per open function, no copied quotations.',
            'items':obj({'work_id':TEXT,'reason':TEXT})}
DEFINITIONS={
    'list_documents':('Состав подготовленного комплекта: роли, ошибки, ограничения, адрес начала каждого документа.',obj({})),
    'search':('Гибридный поиск по текстовому и векторному индексам. Результат поиска не считается чтением. Неустановленные роли включаются при фильтрации.',obj({
        'query':TEXT,'role':{'type':['string','null'],'enum':['before','after','common','unknown',None]},
        'document_id':NULL_TEXT,'limit':{'type':'integer','minimum':1,'maximum':20},'work_id':NULL_TEXT})),
    'read_context':('Прочитать адресный пункт с контекстом. Ответ ограничен 18000 символами; next_offset означает непрочитанное продолжение. scope=document тоже постраничный. Начни с offset=0.',obj({
        'fragment_id':TEXT,'scope':{'type':'string','enum':['section','document']},'offset':{'type':'integer','minimum':0,'maximum':20000},
        'work_id':NULL_TEXT,'purpose':TEXT})),
    'ocr_page':('Локальный RapidOCR одной физической PDF-страницы с изображениями. Сохраняет адресуемые OCR-фрагменты и обновляет поиск. Используй fragment_ids в read_context перед цитированием. Цитата проверяется по распознанному тексту, не по изображению; OCR не доказывает полноту и не считается проверкой человеком.',obj({
        'document_id':TEXT,'page':{'type':'integer','minimum':1,'maximum':200}})),
    'update_research_state':('Сохранить ОДИН результат одной функции за вызов (result_updates: 0–1); затем следующую функцию отдельным вызовом. comparison выделяет действие, объект, условия, этап и конкретные изменённые поля. Не копируй цитаты в supporting при hypothesis_id=null. accepted_result_ids уже сохранены даже при ошибке закрытия группы. Исправляй отклонённый result_id; принятые записи не пересылай. checked у задачи требует всех её пунктов.',obj({
        'hypothesis_id':NULL_TEXT,'claim':TEXT,'assessment':{'type':'string','enum':['open','supported','refuted','uncertain']},
        'supporting':EVIDENCE,'contradicting':EVIDENCE,'gaps':STRINGS,'revision_reason':TEXT,'candidate_updates':UPDATES,
        'result_updates':RESULT_UPDATES,'task_updates':TASK_UPDATES,'work_updates':WORK_UPDATES})),
    'get_coverage':('Охват чтения и содержательные задачи. task_id=null: группы заголовков; task_id из списка: состав выбранной группы. offset листает. Группа/заголовок не доказывают владельца.',obj({'offset':{'type':'integer','minimum':0,'maximum':20000},'task_id':NULL_TEXT})),
    'submit_findings':('Передать структурированные результаты. Проверяет существование прочитанных цитат, роли, поля и охват, но не доказывает интерпретацию. Ошибки возвращаются для исправления; успешный вызов завершает исследование.',obj({
        'findings':{'type':'array','items':FINDING},'outcome':{'type':'string','enum':['completed','insufficient_data']},
        'gaps':STRINGS,'reason':TEXT,'saved_result_ids':STRINGS,'unfinished_work':UNFINISHED})),
    'request_clarification':('Остановить исследование для существенного уточнения версий или состава комплекта.',obj({'question':TEXT,'document_ids':STRINGS})),
}
TOOL_SCHEMAS=[{'type':'function','function':{'name':name,'description':description,'parameters':schema,'strict':True}}
              for name,(description,schema) in DEFINITIONS.items()]


def validate_shape(value, schema, path='arguments'):
    """Validate this small schema vocabulary before dispatch, including unexpected fields."""
    kind=schema['type']
    if isinstance(kind,list):
        if value is None and 'null' in kind: return
        kind=next(t for t in kind if t!='null')
    if kind=='object':
        if not isinstance(value,dict) or set(value)!=set(schema['properties']):
            raise ValueError(path+': неполные или неизвестные поля.')
        for key,child in schema['properties'].items(): validate_shape(value[key],child,path+'.'+key)
    elif kind=='array':
        if not isinstance(value,list) or len(value)>schema.get('maxItems',80):
            raise ValueError(path+': нужен список не более '+str(schema.get('maxItems',80))+'.')
        for i,item in enumerate(value): validate_shape(item,schema['items'],path+f'[{i}]')
    elif kind=='string':
        if not isinstance(value,str) or len(value)>12000: raise ValueError(path+': нужна строка до 12000 символов.')
    elif kind=='integer':
        if not isinstance(value,int) or isinstance(value,bool) or not schema.get('minimum',0)<=value<=schema.get('maximum',100):
            raise ValueError(path+': недопустимое число.')
    if 'enum' in schema and value not in schema['enum']: raise ValueError(path+': неизвестное значение.')


class ResearchTools:
    def __init__(self, state, store, index):
        self.state,self.store,self.index=state,store,index

    def execute(self, name, arguments):
        if name not in DEFINITIONS: raise ValueError('Инструмент не разрешён.')
        arguments=dict(arguments)
        if name in {'read_context','get_coverage'}: arguments.setdefault('offset',0)
        if name in {'search','read_context'}:arguments.setdefault('work_id',None)
        if name=='read_context':arguments.setdefault('purpose','')
        if name=='get_coverage': arguments.setdefault('task_id',None)
        if name=='update_research_state':
            for field in ['candidate_updates','result_updates','task_updates','work_updates']:arguments.setdefault(field,[])
        if name=='submit_findings':
            arguments.setdefault('saved_result_ids',[])
            arguments.setdefault('unfinished_work',[])
            arguments['findings']=[{**f,'claim_checks':f.get('claim_checks',[]),'assertion_type':f.get('assertion_type','observation')} for f in arguments.get('findings',[])]
        arguments=deepcopy(arguments)
        findings=([r.get('finding') for r in arguments.get('result_updates',[]) if isinstance(r,dict)]
                  if name=='update_research_state' else arguments.get('findings',[]) if name=='submit_findings' else [])
        for finding in findings:
            if isinstance(finding,dict):finding.setdefault('comparison',None)
        schema=DEFINITIONS[name][1]
        if name=='update_research_state' and self.state.data.get('research_policy',0)<4:
            schema=deepcopy(schema)
            schema['properties']['result_updates']['maxItems']=20
        validate_shape(arguments,schema)
        for finding in findings:
            if finding.get('comparison') is None:finding.pop('comparison')
        work_id=arguments.pop('work_id') if name in {'search','read_context'} else None
        work=self.state.data['function_work'].get(work_id) if work_id else None
        if work_id and (not work or work['status'] in {'completed','insufficient_data'}):
            raise ValueError('Use an existing open function work_id, or null for discovery.')
        if name=='list_documents':
            from ayqyn.documents.ocr import capability
            documents=self.store.list_documents()
            for item in documents:
                paragraphs=self.store.documents[item['id']]['paragraphs']
                item['first_fragment_id']=paragraphs[0]['id'] if paragraphs else None
            return {'documents':documents,'duplicates':self.state.packet.get('duplicates',[]),
                    'limitations':self.state.packet['warnings'],'research_tasks':task_summary(self.state),
                    'ocr':capability()}
        if name=='ocr_page':
            return self.ocr_page(**arguments)
        if name=='search':
            if work:
                remaining=20-len(work['candidate_ids'])
                longest_id=max((len(key) for key in self.store.fragments),default=0)
                if arguments['limit']>remaining or len(str(self.state.data['function_work']))+arguments['limit']*(longest_id+8)>48000:
                    raise ValueError('Assess or explicitly narrow this work candidate_ids before another search, or reduce limit. No search executed; existing candidates retained.')
            if self.state.data.get('ocr_index_pending'):
                result=self.store.search_fragments(**arguments)
                result['limitation']='OCR vector index update failed; all current sources are searched lexically. Read context before citing. Missing matches do not prove absence.'
                result['index_status']='lexical_fallback'
            else:
                result=self.index.search(**arguments)
            if work:
                candidates=list(dict.fromkeys(work['candidate_ids']+[hit['id'] for hit in result['hits']]))
                work['candidate_ids']=candidates
                if work['status']=='needs_search' and candidates:
                    work['status']='needs_read'
                result={**result,'work_id':work_id,
                        'notice':'Candidates attached to the open function, not accepted as matches. Read context and evaluate alternatives.'}
            return result
        if name=='read_context':
            purpose=arguments.pop('purpose')
            if self.state.data.get('research_policy',0)>=5 and arguments['fragment_id'] in self.store.read_ids and not purpose.strip():
                raise ValueError('For a repeated read, state which uncertainty this reading resolves in purpose.')
            result=self.store.read_context_page(**arguments)
            units={key:c['id'] for c in self.state.data['candidates'].values() for key in c['fragment_ids']}
            for block in result['fragments']: block['candidate_id']=units.get(block['id'])
            result['task_ids']=[t['id'] for t in self.state.data['research_tasks'].values() if arguments['fragment_id'] in t['fragment_ids']]
            if self.state.data.get('research_policy',0)>=5:
                result['function_work_notice']='Identify the distinct functions in this context and register/update their work_updates before changing areas. Multiple compact work records may be registered together; one paragraph is not necessarily one function.'
                result['work_id']=work_id
                result['purpose']=purpose
                result['candidate_assessment_required']=bool(work)
            return result
        if name=='update_research_state':
            values=arguments.pop('candidate_updates')
            result_values=arguments.pop('result_updates')
            task_values=arguments.pop('task_updates')
            work_values=arguments.pop('work_updates')
            results=self.state.save_checked_results(self.store,result_values)
            work_result=self.state.update_function_work(self.store,work_values)
            candidates=update_candidates(self.state,self.store,values)
            task_errors=[]
            accepted_tasks=[]
            for value in task_values:
                result=update_tasks(self.state,self.store,[value])
                if result['accepted']:
                    accepted_tasks.extend(result['updated_task_ids']);continue
                task=self.state.data['research_tasks'].get(value['task_id'],{})
                reviewed=set(task.get('reviewed_candidate_ids',[]))|set(value['reviewed_candidate_ids'])
                task_errors.append({'task_id':value['task_id'],'code':'task_incomplete_or_invalid',
                    'missing_candidate_ids':[key for key in task.get('candidate_ids',[]) if key not in reviewed],
                    'unread_candidate_ids':[key for key in reviewed if key in self.state.data['candidates']
                        and not set(self.state.data['candidates'][key]['fragment_ids'])<=self.store.read_ids],
                    'open_questions':value['open_questions'],'errors':result['errors']})
            try:
                hypothesis=self.state.update_hypothesis(self.store,arguments) if arguments['hypothesis_id'] is not None else {'accepted':True}
            except ValueError as exc:
                hypothesis={'accepted':False,'errors':[str(exc)]}
            errors=results.get('rejected_results',results.get('errors',[]))+work_result['work_errors']+task_errors+candidates.get('errors',[])+hypothesis.get('errors',[])
            return {'accepted':not errors,'partial':bool(errors and (results.get('accepted_result_ids') or accepted_tasks or work_result['accepted_work_ids'])),
                    'accepted_result_ids':results.get('accepted_result_ids',[]),'rejected_results':results.get('rejected_results',[]),
                    'accepted_task_ids':accepted_tasks,'task_update_errors':task_errors,
                    **work_result,'function_work':self.state.function_work_summary(self.store),
                    'candidate_updates':candidates,'hypothesis':hypothesis,'errors':errors}
        if name=='get_coverage':
            return {**self.store.coverage_summary(),'budget':self.state.data['budget'],
                    'function_work':self.state.function_work_summary(self.store),
                    'research_tasks':task_summary(self.state,arguments['offset'],task_id=arguments['task_id'])}
        if name=='submit_findings':
            unfinished=arguments.pop('unfinished_work')
            pending={k:w for k,w in self.state.data['function_work'].items() if w['status'] not in {'completed','insufficient_data'}}
            supplied={w['work_id']:w['reason'] for w in unfinished}
            if (set(supplied)!=set(pending) or len(supplied)!=len(unfinished)
                    or any(not reason.strip() or len(reason)>1000 for reason in supplied.values())):
                return {'accepted':False,'errors':['Give one concrete unfinished_work reason per open function, using its work_id. Partial submission is allowed.'],
                        'function_work':self.state.function_work_summary(self.store),'budget':self.state.data['budget']}
            unresolved=[w for w in self.state.data['function_work'].values() if w['status']=='insufficient_data']
            if (pending or unresolved) and arguments['outcome']=='completed':
                return {'accepted':False,'errors':['Open or unresolved function comparisons remain. Use insufficient_data; a saved unresolved result is not a complete investigation.']}
            selected=arguments.pop('saved_result_ids')
            entries=[('new:'+str(n),finding) for n,finding in enumerate(arguments['findings'])]
            for identifier in selected:
                if identifier not in self.state.data['checked_results']:raise ValueError('Unknown saved result: '+identifier)
                entries.append((identifier,self.state.data['checked_results'][identifier]['finding']))
            unique={};duplicates=[];conflicts=[]
            for origin,raw in entries:
                finding={**deepcopy(raw),'claim_checks':raw.get('claim_checks',[]),'assertion_type':raw.get('assertion_type','observation')}
                identity=tuple(' '.join(str(finding.get(k) or '').casefold().split()) for k in ['group','function','owner_before','owner_after'])
                if identity not in unique:unique[identity]=(origin,finding)
                elif unique[identity][1]==finding:duplicates.append({'entry':origin,'same_as':unique[identity][0]})
                else:conflicts.append({'code':'conflicting_result_versions','entry':origin,'conflicts_with':unique[identity][0],
                                      'field':'findings','message':'Revise the saved record explicitly or submit one version. No version was chosen.'})
            if conflicts:return {'accepted':False,'errors':conflicts,'deduplicated':duplicates}
            arguments['findings']=[entry[1] for entry in unique.values()]
            result=self.state.submit(self.store,**arguments)
            if result['accepted']:
                self.state.data['unfinished_work']=deepcopy(unfinished)
                self.state.data['gaps'].extend('Незавершённая функция '+pending[k]['function']+': '+reason for k,reason in supplied.items())
                self.state.data['gaps'].extend('Ограниченный результат '+w['function']+': '+w['resolution'] for w in unresolved)
            return {**result,'deduplicated':duplicates}
        if name=='request_clarification':
            if not arguments['question'].strip(): raise ValueError('Нужен вопрос.')
            if any(i not in self.store.documents for i in arguments['document_ids']):
                raise ValueError('Уточнение ссылается на чужой документ.')
            self.state.data['clarifications'].append(arguments)
            self.state.data.update(status='needs_clarification',stop_reason='Существенная неоднозначность требует ответа пользователя.')
            self.state.data['gaps'].append(arguments['question'])
            return {'accepted':True,'outcome':'needs_clarification','question':arguments['question']}

    def ocr_page(self, document_id, page):
        from ayqyn.documents.ocr import recognize_page
        doc=self.store.documents.get(document_id)
        if not doc or doc.get('format')!='pdf':
            raise ValueError('OCR requires a PDF document_id from the current packet.')
        digest=doc.get('sha256','')
        if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):
            raise ValueError('The PDF original has no valid saved hash.')
        if isinstance(doc.get('page_count'),int) and page>doc['page_count']:
            raise ValueError('Requested OCR page is outside this PDF.')
        original=(self.state.path/'originals'/(digest+'.pdf')).resolve()
        if not original.is_relative_to(self.state.path.resolve()) or not original.is_file():
            raise ValueError('No saved PDF original is available within this research.')
        if original.stat().st_size>10_000_000 or hashlib.sha256(original.read_bytes()).hexdigest()!=digest:
            raise ValueError('The saved PDF original does not match the packet hash or size limit.')
        key=document_id+':ocr:page-'+str(page)
        if key in self.state.data['ocr_pages'] and self.state.data['ocr_pages'][key].get('engine')=='rapidocr':
            return {**deepcopy(self.state.data['ocr_pages'][key]),'cached':True}
        if key not in self.state.data['ocr_pages'] and len(self.state.data['ocr_pages'])>=4:
            return {'status':'limit_reached','error':'Local OCR is limited to four pages per research. Remaining pages are unverified.'}
        budget=self.state.data['budget']
        remaining=budget['max_seconds']-budget['elapsed_seconds']
        if remaining<=0:
            return {'status':'budget_exhausted','error':'No time remains for OCR.'}
        result=recognize_page(original,page,timeout_seconds=min(20,remaining))
        result={**result,'document_id':document_id,'document_name':doc['name'],'sha256':digest,
                'page':page,'ocr_id':key,'source':'ocr','verified':False,'cached':False,
                'limitation':'OCR is an unverified transcription. Read the addressable fragments with read_context before citing; verify against the original image. Native extraction gaps remain.'}
        if result.get('status')=='success':
            from ayqyn.documents.ocr_sources import attach_ocr, register_ocr_inventory
            fragments=attach_ocr(self.store.packet,result)
            if self.state.packet is not self.store.packet:
                attach_ocr(self.state.packet,result)
            self.store.refresh_sources()
            result.update(source_schema=1,fragment_ids=[p['id'] for p in fragments],citation_status='read_context_required')
            register_ocr_inventory(self.state,self.store,fragments)
            self.state.data['ocr_pages'][key]=deepcopy(result)
            if fragments:
                self.state.data['ocr_index_pending']=True
                self.state.save()  # Derived sources survive an interrupted index update.
                try:
                    if not callable(getattr(self.index,'refresh',None)):
                        raise ValueError('Index has no refresh capability.')
                    metadata=self.index.refresh()
                    self.state.data['index']=metadata
                    self.state.data['ocr_index_pending']=False
                    result['index_status']='hybrid'
                except (ValueError,OSError):
                    result['index_status']='lexical_fallback'
                self.state.data['ocr_pages'][key]=deepcopy(result)
                self.state.event('ocr_sources_registered',ocr_id=key,fragment_ids=result['fragment_ids'],index_status=result['index_status'])
            self.state.save()
        return result
