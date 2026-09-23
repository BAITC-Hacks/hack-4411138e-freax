"""Addressable source fragments and observable read coverage for an investigator."""
from copy import deepcopy
import json
import re
from function_analysis import normalized


MAX_CONTEXT_RESPONSE_CHARS = 1_000_000


class ContextLimitError(ValueError):
    """An entire context response exceeded its limit; no fragments were read."""

    def __init__(self, required_chars, response_limit_chars):
        self.required_chars = required_chars
        self.response_limit_chars = response_limit_chars
        super().__init__(f"Context response requires {required_chars} characters; "
                         f"response limit is {response_limit_chars}. No fragments were returned or marked read.")


class DocumentStore:
    def __init__(self, packet, *, max_response_chars=MAX_CONTEXT_RESPONSE_CHARS):
        if not isinstance(max_response_chars, int) or isinstance(max_response_chars, bool) or max_response_chars < 1:
            raise ValueError('Context response limit must be a positive integer.')
        self.packet=packet
        self.documents={d['id']:d for d in packet['documents']}
        self.fragments={p['id']:p for d in packet['documents'] for p in d['paragraphs']}
        self.read_ids=set()
        self.actions=[]
        self.max_response_chars=max_response_chars
        self._parents={}
        self._children={}
        self._sections={}
        self._fragment_sections={}
        for doc in self.documents.values():
            self._index_context(doc)

    def _index_context(self, doc):
        paragraphs=doc['paragraphs']
        local_ids={p.get('local_id', p['id']):p['id'] for p in paragraphs}
        seen=set()
        numbered=[]
        groups={}
        previous=None
        uncertain_pages=set(doc.get('layout_warning_pages', []))
        for p in paragraphs:
            uncertain=p.get('page') in uncertain_pages
            if 'parent_id' in p:
                parent=p['parent_id']
                parent=local_ids.get(parent, parent)
                parent=parent if parent in seen else None
            else:
                # Legacy/PDF inputs have no Word structure. Only explicit,
                # current numbered ancestry is known; never scan for colons.
                label=p.get('section', '')
                number=label if not uncertain and re.fullmatch(r'\d+(?:\.\d+)*', label) else None
                if number:
                    while numbered and not (number == numbered[-1][0] or number.startswith(numbered[-1][0]+'.')):
                        numbered.pop()
                    parent=numbered[-1][1] if numbered else None
                    if not numbered or number != numbered[-1][0]:
                        numbered.append((number, p['id']))
                else:
                    numbered=[]
                    parent=None
            self._parents[p['id']]=parent
            if parent:
                self._children.setdefault(parent, []).append(p['id'])
            seen.add(p['id'])
            if p.get('table_id') is not None:
                key=('row', p['table_id'], p.get('row_index'))
            elif (previous is not None and previous.get('table_id') is None
                  and not uncertain and previous.get('page') not in uncertain_pages
                  and p.get('section', '') == previous.get('section', '')
                  and p.get('block_type') not in {'heading', 'clause'}):
                key=self._fragment_sections[previous['id']]
            else:
                key=p['id']
            if key not in groups:
                groups[key]={'id':p['id'], 'document_id':doc['id'],
                             'section':p.get('section', ''), 'fragment_ids':[]}
            groups[key]['fragment_ids'].append(p['id'])
            self._fragment_sections[p['id']]=key
            previous=p
        self._sections[doc['id']]=groups

    def list_documents(self):
        return [{k:d.get(k) for k in ['id','name','format','role','role_reason','version','organization',
                                      'read_status','error','warnings','sha256','synthetic','page_count']}
                for d in self.documents.values()]

    def search_fragments(self, query, role=None, document_id=None, limit=8):
        if not isinstance(query,str) or not query.strip() or len(query)>500:
            raise ValueError('Нужен поисковый запрос длиной до 500 символов.')
        if role not in {None,'before','after','common','unknown'}:
            raise ValueError('Неизвестный фильтр редакции.')
        if document_id is not None and document_id not in self.documents:
            raise ValueError('Документ не найден.')
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=20:
            raise ValueError('Лимит поиска: от 1 до 20.')
        query=normalized(query).casefold()
        tokens=set(re.findall(r'\w+',query))
        hits=[]
        searched=[]
        for doc in self.documents.values():
            # Unknown versions are never silently excluded by a version filter.
            if role and doc['role'] not in {role,'common','unknown'}: continue
            if document_id and doc['id']!=document_id: continue
            searched.append(doc['id'])
            for p in doc['paragraphs']:
                text=normalized(p['text']).casefold()
                score=10*int(query in text)+len(tokens & set(re.findall(r'\w+',text)))
                if score:
                    hits.append({'id':p['id'],'document_id':doc['id'],'document_name':doc['name'],
                                 'role':doc['role'],'section':p['section'],'page':p.get('page'),
                                 'snippet':p['text'][:450],'score':score})
        hits.sort(key=lambda h:(-h['score'],h['id']))
        result={'method':'lexical','query':query,'hits':hits[:limit],'matched_count':len(hits),
                'searched_document_ids':searched,'truncated':len(hits)>limit,
                'limitation':'Поисковые совпадения не считаются прочитанными. Семантический поиск ещё не подключён; отсутствие совпадения не доказывает потерю.'}
        self.actions.append({'tool':'search_fragments','arguments':{'query':query,'role':role,'document_id':document_id,'limit':limit},
                             'result':deepcopy(result)})
        return result

    def read_section(self, fragment_id):
        """Compatibility entry point; logged as one read_section action."""
        return self._read_context(fragment_id, 'section', 'read_section')

    def read_context(self, fragment_id, scope='section'):
        """Return a complete section with context, or the full current document.

        All fragment-ID result lists describe whole returned fragments in source
        order. read_ids is per response; self.read_ids is cumulative. A section
        includes its continuations and descendants, structural ancestors, one
        neighbor on either side, and table row/header/first-row context. Parent
        and neighbor roles are distinct and do not establish legal ownership.
        The complete JSON response (ensure_ascii=False) is limited by
        max_response_chars. Oversize raises ContextLimitError atomically; it
        logs the error and changes no read coverage. There is no top-k or text
        slicing. Document scope is limited to the seed fragment's document.
        """
        return self._read_context(fragment_id, scope, 'read_context')

    def _read_context(self, fragment_id, scope, tool):
        if not isinstance(scope, str) or scope not in {'section', 'document'}:
            raise ValueError('Context scope must be section or document.')
        fragment=self.fragments.get(fragment_id)
        if not fragment:
            raise ValueError('Фрагмент не найден.')
        doc=self.documents[fragment['document_id']]
        paragraphs=doc['paragraphs']
        section=self._sections[doc['id']][self._fragment_sections[fragment_id]]
        section_ids=set(section['fragment_ids'])
        pending=list(section_ids)
        while pending:
            for child in self._children.get(pending.pop(), []):
                if child not in section_ids:
                    section_ids.add(child)
                    pending.append(child)
        parent_ids=set()
        for current in section_ids:
            parent=self._parents[current]
            while parent and parent not in section_ids and parent not in parent_ids:
                parent_ids.add(parent)
                parent=self._parents[parent]
        positions=[index for index,p in enumerate(paragraphs) if p['id'] in section_ids]
        neighbor_ids={paragraphs[index]['id'] for index in (positions[0]-1, positions[-1]+1)
                      if 0<=index<len(paragraphs)} - section_ids
        rows={(p['table_id'], p.get('row_index')) for p in paragraphs
              if p['id'] in section_ids and p.get('table_id') is not None}
        tables={table for table, _ in rows}
        row_ids={p['id'] for p in paragraphs if (p.get('table_id'),p.get('row_index')) in rows}
        header_ids={p['id'] for p in paragraphs if p.get('table_id') in tables and p.get('is_header') is True}
        first_ids={p['id'] for p in paragraphs if p.get('table_id') in tables and p.get('row_index') == 0}
        returned_ids=section_ids | parent_ids | neighbor_ids | row_ids | header_ids | first_ids
        if scope == 'document':
            returned_ids={p['id'] for p in paragraphs}
        def ordered(ids):
            return [p['id'] for p in paragraphs if p['id'] in ids]
        result={'document_id':doc['id'],'document_name':doc['name'],'role':doc['role'],
                'scope':scope, 'section_id':section['id'],
                'fragments':[p for p in paragraphs if p['id'] in returned_ids],
                'section_fragment_ids':ordered(section_ids), 'parent_fragment_ids':ordered(parent_ids),
                'neighbor_fragment_ids':ordered(neighbor_ids), 'table_row_fragment_ids':ordered(row_ids),
                'table_header_fragment_ids':ordered(header_ids), 'table_first_row_fragment_ids':ordered(first_ids),
                'warnings':doc.get('warnings',[]), 'layout_warnings':doc.get('layout_warnings',[]),
                'layout_warning_pages':doc.get('layout_warning_pages',[]),
                'read_status':doc.get('read_status'), 'error':doc.get('error'),
                'unread_pages':doc.get('unread_pages',[]),
                'limitation':'Заголовки даны как контекст; ближайший заголовок сам по себе не доказывает владельца.'}
        arguments={'fragment_id':fragment_id}
        if tool == 'read_context':
            arguments['scope']=scope
        return self._return_read(tool, arguments, result)

    def _return_read(self, tool, arguments, result):
        ids=[p['id'] for p in result['fragments']]
        result.update(fragment_ids=ids, read_ids=list(ids), truncated=False,
                      response_limit_chars=self.max_response_chars)
        size=len(json.dumps(result, ensure_ascii=False))
        if size>self.max_response_chars:
            error=ContextLimitError(size, self.max_response_chars)
            self.actions.append({'tool':tool, 'arguments':arguments,
                                 'error':{'code':'response_limit_exceeded', 'message':str(error),
                                          'required_chars':size, 'response_limit_chars':self.max_response_chars}})
            raise error
        result=deepcopy(result)
        self.actions.append({'tool':tool, 'arguments':arguments, 'result':deepcopy(result)})
        self.read_ids.update(ids)
        return result

    def read_page(self, document_id, page):
        doc=self.documents.get(document_id)
        if not doc or doc['format']!='pdf': raise ValueError('Нужен идентификатор прочитанного PDF.')
        if not isinstance(page,int) or isinstance(page,bool) or not 1<=page<=doc.get('page_count',0):
            raise ValueError('Страница PDF не найдена.')
        fragments=[p for p in doc['paragraphs'] if p.get('page')==page]
        result={'document_id':document_id,'page':page,'printed_page':None,'fragments':fragments,
                'limitation':'Извлечённый текст страницы, не визуальная проверка геометрии. Сложная вёрстка требует отдельной проверки.'}
        return self._return_read('read_page', {'document_id':document_id,'page':page}, result)

    def check_evidence(self, fragment_id, quote):
        p=self.fragments.get(fragment_id)
        valid=bool(p and isinstance(quote,str) and quote.strip() and normalized(quote) in normalized(p['text']))
        return {'exists':valid,'was_read':fragment_id in self.read_ids,
                'document_id':p['document_id'] if p else None,
                'limitation':'Проверено существование цитаты, а не обоснованность вывода.'}

    def get_coverage(self):
        """Report returned text and recorded searches, never inferred inspection.

        Section IDs are the first fragment addresses of disjoint contiguous
        section runs or XML table rows. They can be passed to read_context to
        expand unread coverage. Section counts cover those exact groups; a
        context read can additionally include descendants and neighbors.
        Extraction errors/unread pages remain visible even after all available
        text is returned. Search scopes are snapshots of actual action results.
        """
        documents=[]
        for d in self.documents.values():
            ids={p['id'] for p in d['paragraphs']}
            sections=[]
            for section in self._sections[d['id']].values():
                unread=[key for key in section['fragment_ids'] if key not in self.read_ids]
                sections.append({**section, 'unread_fragment_ids':unread,
                                 'read_fragments':len(section['fragment_ids'])-len(unread),
                                 'fully_read':not unread})
            documents.append({'id':d['id'],'name':d['name'],'role':d['role'],'read_status':d['read_status'],
                              'indexed_fragments':len(ids),'read_fragments':len(ids & self.read_ids),
                              'fully_read':bool(ids) and ids<=self.read_ids,
                              'unread_fragment_ids':[p['id'] for p in d['paragraphs'] if p['id'] not in self.read_ids],
                              'sections':sections, 'unread_section_ids':[s['id'] for s in sections if not s['fully_read']],
                              'error':d.get('error'), 'warnings':d.get('warnings',[]),
                              'layout_warnings':d.get('layout_warnings',[]),
                              'layout_warning_pages':d.get('layout_warning_pages',[]),
                              'unread_pages':d.get('unread_pages',[])})
        after=[d for d in documents if d['role'] in {'after','common','unknown'}]
        searches=[]
        for index,action in enumerate(self.actions, 1):
            result=action.get('result',{})
            if 'searched_document_ids' in result:
                searches.append({'action_index':index, 'tool':action['tool'], 'arguments':action['arguments'],
                                 'method':result.get('method'), 'query':result.get('query'),
                                 'searched_document_ids':result['searched_document_ids'],
                                 'returned_fragment_ids':[hit['id'] for hit in result.get('hits',[])],
                                 'matched_count':result.get('matched_count'), 'truncated':result.get('truncated')})
        return deepcopy({'documents':documents,'after_fully_read':bool(after) and all(d['fully_read'] for d in after)
                and self.packet['complete_read'] and not self.packet['mixed'] and all(d['role']!='unknown' for d in after),
                'unread_document_ids':[d['id'] for d in documents if not d['fully_read'] or d['read_status']!='read'],
                'unread_section_ids':[key for d in documents for key in d['unread_section_ids']],
                'errors':[{'document_id':d['id'],'read_status':d['read_status'],'error':d['error']}
                          for d in documents if d['error'] or d['read_status']!='read'],
                'warnings':self.packet.get('warnings',[]),
                'layout_warnings':[{'document_id':d['id'], 'warnings':d['warnings'],
                                    'layout_warnings':d['layout_warnings'], 'pages':d['layout_warning_pages']}
                                   for d in documents if d['layout_warnings'] or d['layout_warning_pages']],
                'search_scopes':searches,
                'read_errors':[action for action in self.actions if 'error' in action],
                'action_count':len(self.actions),'limitation':'Охват только загруженного комплекта, не всей организации. Чтение означает возврат текста инструментом, не доказательство понимания моделью.'})
