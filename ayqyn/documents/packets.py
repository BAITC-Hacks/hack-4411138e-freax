"""Document bundles with explicit provenance and conservative version roles."""
import base64
import binascii
import hashlib
import re
from pathlib import Path

from ayqyn.documents.analyzer import parse_docx

ROLES = {'before', 'after', 'common', 'unknown'}


def classify(document):
    text = '\n'.join(p['text'] for p in document['paragraphs'][:12])
    markers = []
    for role, pattern in [('before', r'до\s+изменени[йя]|старая\s+редакция'),
                          ('after', r'после\s+изменений|новая\s+редакция'),
                          ('common', r'общий\s+действующий\s+документ|применяется\s+к\s+обеим\s+редакциям')]:
        match = re.search(pattern, text, re.I)
        if match:
            markers.append((role, match.group()))
    version = re.search(r'редакци[яи]\s*[:№]?\s*(\d+)', text, re.I)
    organization = re.search(r'(?:организация|общество)\s*:\s*([^\n]+)', text, re.I)
    case = re.search(r'\b(C\d{3})_(?:before|after)_\w+', text)
    role = markers[0][0] if len(markers) == 1 else 'unknown'
    return {'inferred_role': role, 'role': role,
            'role_reason': ('Маркер в тексте: ' + markers[0][1]) if len(markers) == 1 else
                           ('Противоречивые маркеры редакции.' if markers else 'Роль не установлена по содержимому.'),
            'version': version.group(1) if version else None,
            'organization': organization.group(1).strip() if organization else None,
            'bundle_marker': case.group(1) if case else None,
            'dates': re.findall(r'\b\d{2}\.\d{2}\.\d{4}\b', text),
            'synthetic': bool(re.search(r'synthetic|синтетическ|учебный\s+пример', text, re.I))}


def read_packet(values, mode='auto', overrides=None):
    if mode not in {'auto','manual'}:
        raise ValueError('Неизвестный режим распределения документов.')
    if not isinstance(values,list) or not 1 <= len(values) <= 20:
        raise ValueError('Загрузите от 1 до 20 документов одного комплекта.')
    if overrides is not None and not isinstance(overrides,dict):
        raise ValueError('Некорректные уточнения ролей документов.')
    documents, duplicates, warnings, by_hash = [], [], [], {}
    total = 0
    for number, value in enumerate(values, 1):
        if not isinstance(value,dict) or not isinstance(value.get('name'),str) or not isinstance(value.get('data'),str):
            raise ValueError('Некорректный файл в комплекте.')
        name = value['name'][:250]
        document = {'id':f'unread-{number}', 'name':name, 'sha256':None, 'format':Path(name).suffix.lower().lstrip('.'),
                    'read_status':'error','paragraphs':[], 'role':'unknown', 'inferred_role':'unknown',
                    'role_reason':'Документ не прочитан.', 'warnings':[]}
        try:
            if len(value['data']) > 14_000_000:
                raise ValueError('Файл превышает 10 МБ.')
            try:
                raw = base64.b64decode(value['data'],validate=True)
            except (ValueError,binascii.Error):
                raise ValueError('Повреждена загрузка файла.') from None
            total += len(raw)
            if total > 40_000_000:
                raise ValueError('Комплект превышает 40 МБ.')
            if len(raw) > 10_000_000:
                raise ValueError('Файл превышает 10 МБ.')
            digest = hashlib.sha256(raw).hexdigest()
            document.update(id='d-'+digest,sha256=digest)
            manual_role = value.get('role','unknown') if mode=='manual' else 'unknown'
            assigned = (overrides or {}).get(digest, manual_role)
            if assigned not in ROLES:
                raise ValueError('Неизвестная роль документа.')
            if digest in by_hash:
                primary = by_hash[digest]
                if assigned in {'before','after','common'} and primary['role'] in {'before','after','common'} and assigned != primary['role']:
                    primary.update(role='common',role_reason='Одинаковый файл назначен пользователем обеим сторонам.')
                    warnings.append(f'«{name}»: одинаковый файл применён к обеим сторонам; отдельным источником не считается.')
                duplicates.append({'name':name,'duplicate_of':primary['id'],'sha256':digest,'read_status':'duplicate'})
                continue
            by_hash[digest]=document
            if document['format']=='docx':
                parsed = parse_docx(raw,name)
            elif document['format']=='pdf':
                from ayqyn.documents.pdf import parse_pdf
                parsed = parse_pdf(raw,name)
            else:
                raise ValueError('Формат пока не поддерживается. Доступны текстовый PDF и DOCX; Excel и OCR не реализованы.')
            document.update(parsed)
            document.update(classify(document),read_status='read')
            if document.get('unread_pages'):
                document.update(read_status='partial',error='Не извлечён текст страниц: '+', '.join(map(str,document['unread_pages'])))
            if mode=='manual' or digest in (overrides or {}):
                if assigned!='unknown' and document['inferred_role'] not in {'unknown','common',assigned}:
                    document['warnings'].append('Распределение пользователя противоречит маркеру редакции в тексте.')
                document.update(role=assigned,role_reason='Роль указана пользователем. '+document['role_reason'])
            for p in document['paragraphs']:
                p.update(local_id=p['id'],id=document['id']+':'+p['id'],document_id=document['id'],document_name=name,
                         format=document['format'],page=p.get('page'),printed_page=p.get('printed_page'))
                for field in ['parent_id','previous_id','next_id','table_id','row_id']:
                    if isinstance(p.get(field),str): p[field]=document['id']+':'+p[field]
                for field in ['row_fragment_ids','header_row_ids','header_fragment_ids','first_row_fragment_ids']:
                    if isinstance(p.get(field),list): p[field]=[document['id']+':'+value for value in p[field]]
        except (ValueError,ImportError) as exc:
            document['error']=str(exc)
        documents.append(document)
    markers={d.get('bundle_marker') for d in documents if d.get('bundle_marker')}
    organizations={d.get('organization') for d in documents if d.get('organization')}
    mixed=len(markers)>1 or len(organizations)>1
    if mixed:
        warnings.append('В содержимом обнаружены разные комплекты или организации. Разделите их на отдельные анализы.')
    unknown=[d for d in documents if d['read_status']=='read' and d['role']=='unknown']
    errors=[d for d in documents if d['read_status']!='read']
    if unknown:
        warnings.append('Уточните роли документов с неустановленной редакцией; даты сами по себе не доказывают применимость.')
    if errors:
        warnings.append('Часть файлов не прочитана. Вывод об отсутствии назначения функции по неполному комплекту недопустим.')
    for d in documents:
        warnings.extend(f'«{d["name"]}»: {w}' for w in d['warnings'])
    packet={'documents':documents,'duplicates':duplicates,'warnings':warnings,'mixed':mixed,
            'complete_read':not errors, 'ready':not mixed and not unknown and not errors,
            'input_count':len(values),'unique_count':len(documents),'mode':mode}
    packet['before']=aggregate(documents,'before')
    packet['after']=aggregate(documents,'after')
    if not all(any(d['role']==side and d['read_status']=='read' for d in documents) for side in ['before','after']):
        packet['ready']=False
        warnings.append('Для сравнения нужны прочитанные документы обеих редакций; одного общего документа недостаточно.')
    return packet


def aggregate(documents, side):
    chosen=sorted((d for d in documents if d['read_status']=='read' and d['role'] in {side,'common'}),key=lambda d:d['id'])
    return {'name':'Комплект '+('до изменений' if side=='before' else 'после изменений'),
            'sha256':hashlib.sha256('|'.join(d['sha256'] for d in chosen).encode()).hexdigest(),
            'paragraphs':[p for d in chosen for p in d['paragraphs']],
            'documents':[{k:d.get(k) for k in ['id','name','sha256','format','version','role','role_reason','synthetic','page_count']} for d in chosen]}
