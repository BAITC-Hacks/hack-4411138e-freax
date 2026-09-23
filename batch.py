"""A bounded document packet with explicit, reviewable version inference."""
import hashlib
import re

MAX_DOCUMENTS = 20
REVISION = re.compile(r'(?:редакци[яи]|ред\.?|revision|version|верси[яи]|v)\s*[_ .№-]*\s*(\d{1,3})(?!\d)', re.I)
YEAR = re.compile(r'(?<!\d)(20\d{2})(?!\d)')


def classify_documents(documents, selections):
    """Infer only explicit filename labels or two distinct versions of one family.

    Dates in body text can refer to unrelated orders, so they are not a chronology
    signal. Multiple intermediate revisions require an analyst's explicit choice.
    """
    groups = {}
    for index, (doc, selection) in enumerate(zip(documents, selections), 1):
        doc['id'] = f'd{index}'
        doc['side'] = None
        doc['classification'] = 'unresolved'
        side = selection.get('side', 'auto')
        if side not in ('auto', 'before', 'after'):
            raise ValueError('Недопустимая редакция документа.')
        name = doc['name'].rsplit('.', 1)[0].casefold().replace('_', ' ')
        if side != 'auto':
            doc.update(side=side, classification='manual')
        else:
            before = bool(re.search(r'\b(before|до|дейін|бұрын)\b', name))
            after = bool(re.search(r'\b(after|после|кейін)\b', name))
            if before != after:
                doc.update(side='before' if before else 'after', classification='filename')
        revision = REVISION.search(name)
        year = YEAR.search(name)
        marker = revision or year
        if marker:
            family = re.sub(r'[^\w]+', ' ', name[:marker.start()] + name[marker.end():]).strip()
            if family:
                groups.setdefault((family, 'revision' if revision else 'year'), []).append((int(marker.group(1)), doc))
    for items in groups.values():
        versions = sorted({version for version, _ in items})
        if len(versions) != 2:
            continue
        for version, doc in items:
            if doc['side'] is None:
                doc.update(side='before' if version == versions[0] else 'after', classification='version', revision=version)
    return documents


def combine_documents(documents, side):
    selected = [doc for doc in documents if doc['side'] == side]
    paragraphs = []
    for doc in selected:
        for paragraph in doc['paragraphs']:
            # IDs are unique across files, even if filenames repeat.
            paragraph['original_id'] = paragraph['id']
            paragraph['id'] = doc['id'] + ':' + paragraph['id']
            paragraph['document_id'] = doc['id']
            paragraph['document_name'] = doc['name']
            paragraphs.append(paragraph)
    return {'name': ' · '.join(doc['name'] for doc in selected), 'paragraphs': paragraphs,
            'sha256': hashlib.sha256('|'.join(doc['sha256'] for doc in selected).encode()).hexdigest()}
