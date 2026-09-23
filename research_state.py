"""Durable research state. Evidence validation is not semantic verification."""
import copy
import json
import os
from pathlib import Path
from run_record import utc_now

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

    def save(self):
        self.data['updated_at']=utc_now()
        atomic_json(self.path/'state.json',self.data,self.secrets)

    def event(self, kind, **fields):
        self.data['journal'].append({'sequence':len(self.data['journal'])+1,'time':utc_now(),'kind':kind,**copy.deepcopy(fields)})

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
        return {'accepted':True,'hypothesis':stored,'notice':'Это оценка агента, не подтверждение человеком.'}

    def submit(self, store, findings, outcome, gaps, reason):
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
        for number,f in enumerate(findings,1):
            issues=[]
            if not isinstance(f,dict) or set(f)!=required:
                errors.append({'finding':number,'errors':['Неполные/неизвестные поля вывода.']}); continue
            if f['group'] not in GROUPS or f['category'] not in GROUPS.get(f['group'],set()):
                issues.append('Категория не соответствует группе результата. Для группы '+str(f['group'])+
                              ' допустимы: '+', '.join(sorted(GROUPS.get(f['group'],set())))+'.')
            for field in ['function','explanation']:
                if not isinstance(f[field],str) or not f[field].strip() or len(f[field])>6000:
                    issues.append('Нужны конкретная функция/объект и объяснение.')
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
                        issues.append('Название владельца должно дословно входить в цитируемое доказательство: '+side)
            left,right=f['before_evidence'],f['after_evidence']
            if not (left or right): issues.append('Нужен хотя бы один источник.')
            if f['category'] in {'preserved','reworded','changed','renamed','split','merged'} and not (left and right):
                issues.append('Для сопоставленного изменения нужны обе редакции.')
            if f['category'] in {'duplication','conflict','contradiction'}:
                if not isinstance(right,list) or len({e.get('fragment_id') for e in right if isinstance(e,dict)})<2:
                    issues.append('Нужны два различных источника обязанностей в новой редакции.')
            if f['category']=='potential_loss':
                if not left: issues.append('Нужна прежняя обязанность.')
                if not coverage['after_fully_read'] or gaps or any(h['gaps'] for h in self.data['hypotheses'].values() if h['assessment']!='refuted'):
                    issues.append('Нельзя выводить потенциальную потерю при непрочитанном after или нерешённых пробелах.')
            if uncertain and f['category'] not in {'insufficient_data','unmatched','unresolved'}:
                issues.append('Комплект имеет ошибки или неопределённые роли; допустим только ограниченный итог о недостатке данных.')
            if issues: errors.append({'finding':number,'errors':issues})
        hypothesis_gaps=any(h['gaps'] for h in self.data['hypotheses'].values() if h['assessment']!='refuted')
        if outcome=='completed' and (uncertain or not coverage['after_fully_read'] or gaps or hypothesis_gaps):
            errors.append({'finding':None,'errors':['Полная проверка не завершена: используйте insufficient_data и назовите пробелы.']})
        self.data['validation_errors']=errors
        if errors: return {'accepted':False,'errors':errors,'instruction':'Исправьте данные или завершите с недостаточностью; ссылки не доказывают интерпретацию.'}
        self.data['findings']=[{**copy.deepcopy(f),'id':f'finding-{n}','evidence_validation':'exact_quotes_verified',
                                'human_review':{'status':'unreviewed','comment':''}} for n,f in enumerate(findings,1)]
        self.data.update(status=outcome,stop_reason=reason,gaps=gaps,coverage=coverage)
        return {'accepted':True,'count':len(findings),'outcome':outcome,
                'notice':'Источники существуют. Правильность интерпретации требует отдельной проверки.'}


def validate_strings(value, name, minimum=0):
    if not isinstance(value,list) or not minimum<=len(value)<=20 or not all(isinstance(v,str) and 0<len(v)<=3000 for v in value):
        raise ValueError(f'{name}: нужен список содержательных строк (до 20).')
