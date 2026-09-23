"""Seven read/research tools. Only submit_findings can complete an investigation."""
from research_state import GROUPS


def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


TEXT={'type':'string'}
NULL_TEXT={'type':['string','null']}
STRINGS={'type':'array','items':TEXT}
EVIDENCE={'type':'array','items':obj({'fragment_id':TEXT,'quote':TEXT})}
FINDING=obj({'group':{'type':'string','enum':list(GROUPS)},
             'category':{'type':'string','enum':sorted(set.union(*GROUPS.values())),
                         'description':'; '.join(group+': '+', '.join(sorted(values)) for group,values in GROUPS.items())},
             'function':TEXT,'owner_before':NULL_TEXT,'owner_after':NULL_TEXT,
             'before_evidence':EVIDENCE,'after_evidence':EVIDENCE,'explanation':TEXT,'limitations':STRINGS})
DEFINITIONS={
    'list_documents':('Состав подготовленного комплекта: роли, ошибки, ограничения, адрес начала каждого документа.',obj({})),
    'search':('Гибридный поиск по текстовому и векторному индексам. Результат поиска не считается чтением. Неустановленные роли включаются при фильтрации.',obj({
        'query':TEXT,'role':{'type':['string','null'],'enum':['before','after','common','unknown',None]},
        'document_id':NULL_TEXT,'limit':{'type':'integer','minimum':1,'maximum':20}})),
    'read_context':('Прочитать исходный пункт с заголовками/продолжениями, соседями и связанной строкой таблицы. scope=document читает весь документ для полного охвата коротких комплектов.',obj({
        'fragment_id':TEXT,'scope':{'type':'string','enum':['section','document']}})),
    'update_research_state':('Записать или пересмотреть гипотезу, сохранив предыдущие версии. Оценка supported/refuted требует прочитанных источников; исходную непроверенную гипотезу можно записать без них.',obj({
        'hypothesis_id':TEXT,'claim':TEXT,'assessment':{'type':'string','enum':['open','supported','refuted','uncertain']},
        'supporting':EVIDENCE,'contradicting':EVIDENCE,'gaps':STRINGS,'revision_reason':TEXT})),
    'get_coverage':('Фактическое чтение, непрочитанные документы/разделы, ошибки извлечения, области поисков и оставшийся бюджет.',obj({})),
    'submit_findings':('Передать структурированные результаты. Проверяет существование прочитанных цитат, роли, поля и охват, но не доказывает интерпретацию. Ошибки возвращаются для исправления; успешный вызов завершает исследование.',obj({
        'findings':{'type':'array','items':FINDING},'outcome':{'type':'string','enum':['completed','insufficient_data']},
        'gaps':STRINGS,'reason':TEXT})),
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
        if not isinstance(value,list) or len(value)>80: raise ValueError(path+': нужен ограниченный список.')
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
        validate_shape(arguments,DEFINITIONS[name][1])
        if name=='list_documents':
            documents=self.store.list_documents()
            for item in documents:
                paragraphs=self.store.documents[item['id']]['paragraphs']
                item['first_fragment_id']=paragraphs[0]['id'] if paragraphs else None
            return {'documents':documents,'duplicates':self.state.packet.get('duplicates',[]),
                    'limitations':self.state.packet['warnings']}
        if name=='search':
            return self.index.search(**arguments)
        if name=='read_context':
            return self.store.read_context(**arguments)
        if name=='update_research_state':
            return self.state.update_hypothesis(self.store,arguments)
        if name=='get_coverage':
            return {**self.store.get_coverage(),'budget':self.state.data['budget'],
                    'searches':[e for e in self.state.data['journal'] if e.get('tool')=='search']}
        if name=='submit_findings':
            return self.state.submit(self.store,**arguments)
        if name=='request_clarification':
            if not arguments['question'].strip(): raise ValueError('Нужен вопрос.')
            if any(i not in self.store.documents for i in arguments['document_ids']):
                raise ValueError('Уточнение ссылается на чужой документ.')
            self.state.data['clarifications'].append(arguments)
            self.state.data.update(status='needs_clarification',stop_reason='Существенная неоднозначность требует ответа пользователя.')
            self.state.data['gaps'].append(arguments['question'])
            return {'accepted':True,'outcome':'needs_clarification','question':arguments['question']}
