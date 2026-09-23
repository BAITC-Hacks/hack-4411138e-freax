"""Addressable OCR transcriptions; recognition never implies human verification."""
from copy import deepcopy
import hashlib
import json
import math

OCR_NOTICE = 'Источник OCR: цитата сверена с распознанным текстом, не с изображением. Нужна проверка сотрудником; чтение OCR не доказывает полноту документа.'


def fragments_from_ocr(doc, record):
    if record.get('status') != 'success' or not record.get('lines'):
        return []
    if record.get('document_id') != doc['id'] or record.get('sha256') != doc['sha256']:
        raise ValueError('OCR source identity does not match the document.')
    page = record['page']
    size = record.get('render_size')
    if (type(page) is not int or not 1 <= page <= 200
            or (type(doc.get('page_count')) is int and page > doc['page_count'])
            or record.get('coordinate_space') != 'render_pixels_top_left'
            or not isinstance(size, list) or len(size) != 2
            or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in size)):
        raise ValueError('OCR needs a valid page and rendered-image coordinates.')
    lines = record['lines']
    if len(lines) > 200 or sum(len(line.get('text', '')) for line in lines) > 12000:
        raise ValueError('OCR source size limit exceeded.')
    digest = hashlib.sha256(json.dumps([record.get('engine'), page, size, lines],
                                    ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()
    fragments = []
    for number, line in enumerate(lines, 1):
        text, box, score = line.get('text'), line.get('box'), line.get('confidence')
        if (not isinstance(text, str) or not isinstance(box, list) or len(box) != 4
                or any(not isinstance(p, list) or len(p) != 2 or any(type(v) not in (int, float)
                       or not math.isfinite(v) for v in p) for p in box)
                or type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError('Invalid OCR line provenance.')
        if not text.strip():
            continue
        local = f'ocr:p{page}:{digest[:16]}:l{number}'
        fragments.append({'id':doc['id']+':'+local, 'local_id':local, 'document_id':doc['id'],
            'document_name':doc['name'], 'role':doc['role'], 'format':'pdf', 'text':text,
            'section':f'PDF page {page} · OCR', 'page':page, 'printed_page':None,
            'parent_id':None, 'block_type':'ocr_line', 'source':'ocr', 'ocr_id':record['ocr_id'],
            'source_sha256':doc['sha256'], 'transcription_sha256':digest, 'engine':record.get('engine'),
            'box':deepcopy(box), 'coordinate_space':record['coordinate_space'], 'render_size':size,
            'page_size_points':record.get('page_size_points'), 'confidence':score,
            'low_confidence':score < .8, 'truncated':bool(record.get('truncated')),
            'verified':False, 'review_status':'unreviewed'})
    return fragments


def attach_ocr(packet, record):
    doc = next((d for d in packet['documents'] if d['id'] == record.get('document_id')), None)
    if doc is None:
        raise ValueError('Unknown OCR document.')
    fragments = fragments_from_ocr(doc, record)
    existing = {p['id']:p for p in doc['paragraphs']}
    for fragment in fragments:
        if fragment['id'] in existing and existing[fragment['id']] != fragment:
            raise ValueError('An OCR source ID cannot overwrite another transcription.')
    doc['paragraphs'].extend(p for p in fragments if p['id'] not in existing)
    if fragments:
        if OCR_NOTICE not in doc.setdefault('warnings', []): doc['warnings'].append(OCR_NOTICE)
        if OCR_NOTICE not in packet.setdefault('warnings', []): packet['warnings'].append(OCR_NOTICE)
    # Preserve native extraction errors, unread_pages, readiness and aggregates.
    return fragments


def register_ocr_inventory(state, store, fragments):
    if not fragments or any(fragments[0]['id'] in c['fragment_ids'] for c in state.data['candidates'].values()):
        return
    first = fragments[0]
    cid = 'c'+str(max((int(k[1:]) for k in state.data['candidates']), default=0)+1)
    tid = 't'+str(max((int(k[1:]) for k in state.data['research_tasks']), default=0)+1)
    ids = [p['id'] for p in fragments]
    state.data['candidates'][cid] = {'id':cid,'document_id':first['document_id'],'role':first['role'],
        'section':first['section'],'fragment_ids':ids,'parent_ids':[],'preview':first['text'][:240],
        'context_preview':'OCR; verify against page image.','status':'pending','text_match_ids':[],
        'text_match_count':0,'comparison_hints':[],'context_changed':False}
    state.data['research_tasks'][tid] = {'id':tid,'document_id':first['document_id'],'role':first['role'],
        'title':first['section'],'section':first['section'],'anchor_id':first['id'],'candidate_ids':[cid],
        'fragment_ids':ids,'status':'not_checked','reviewed_candidate_ids':[],'open_questions':[],
        'next_step':'Read OCR context and assess the source; recognition is not verification.',
        'summary':'','text_changed_units':1,'context_changed_units':0,'priority':1,'comparison_hints':[]}
