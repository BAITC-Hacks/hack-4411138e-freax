"""Prepared local BM25/cosine retrieval. Source text remains in DocumentStore.

Call HybridIndex(store, path, config, embedder=None).build() before investigation.
The path is a directory containing index.json, atomically replaced after a complete build.
Injected embedders implement (list[str]) -> list[list[float]]; their caches cannot
be reused by the real provider. No credentials or provider error bodies are saved.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import unicodedata

from ayqyn.providers.embeddings import BATCH_SIZE, MAX_INPUT_BYTES, OpenAIEmbedder, embedding_settings, validate_vectors


MAX_DOCUMENTS = 128
MAX_FRAGMENTS = 20_000
MAX_SOURCE_BYTES = 8_000_000
MAX_CHUNKS = 4096
MAX_VECTOR_COMPONENTS = 4_194_304
MAX_CACHE_BYTES = 160_000_000
MAX_BUILD_REQUESTS = 128
MAX_HEADING_DEPTH = 128
CANDIDATE_LIMIT = 80
SCHEMA_VERSION = 1
ROLES = {None, 'before', 'after', 'common', 'unknown'}
LIMITATION = ('Search candidates are not read evidence. Missing or low-ranked results '
              'do not establish absence; use source context and coverage.')


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _tokens(text):
    return re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold())


def _role(document):
    role = document.get('role')
    return role if isinstance(role, str) and role in ROLES else 'unknown'


def _usage():
    return {'attempted_requests': 0, 'successful_requests': 0, 'embedded_texts': 0,
            'provider_requests': 0, 'prompt_tokens': 0, 'total_tokens': 0, 'token_usage_complete': True}


def _heading(fragment, fragments, local_ids):
    # Use explicit parser metadata, never infer ownership from a sentence or colon.
    for key in ('nearest_heading', 'heading', 'section_heading'):
        value = fragment.get(key)
        if isinstance(value, str) and value.strip():
            return value
    path = fragment.get('heading_path')
    if isinstance(path, list):
        for value in reversed(path):
            if isinstance(value, str) and value.strip():
                return value
    def resolve(parent_id):
        return local_ids.get((fragment['document_id'], parent_id), parent_id) if isinstance(parent_id, str) else None

    explicit_heading = resolve(fragment.get('heading_id'))
    parent_id = explicit_heading or resolve(fragment.get('parent_id'))
    seen = {fragment['id']}
    while isinstance(parent_id, str) and parent_id not in seen:
        if len(seen) > MAX_HEADING_DEPTH:
            raise ValueError(f'Heading ancestry exceeds {MAX_HEADING_DEPTH} levels; index was not built.')
        seen.add(parent_id)
        parent = fragments.get(parent_id)
        if not parent or parent.get('document_id') != fragment['document_id']:
            break
        level = parent.get('heading_level')
        if (parent.get('is_heading') is True or parent.get('type') == 'heading' or
                parent.get('block_type') == 'heading' or
                (type(level) is int and 1 <= level <= 9) or parent_id == explicit_heading):
            return parent['text']
        parent_id = resolve(parent.get('parent_id'))
    section = fragment.get('section')
    if isinstance(section, str) and any(char.isalpha() for char in section):
        return section
    return ''


def _split(text, heading):
    prefix = heading + '\n\n' if heading and heading != text else ''
    if len(prefix.encode('utf-8')) > MAX_INPUT_BYTES // 2:
        raise ValueError('Heading exceeds the index limit; no source text was truncated.')
    available = MAX_INPUT_BYTES - len(prefix.encode('utf-8'))
    start = 0
    while start < len(text):
        # UTF-8 byte bounds are conservative token bounds for the OpenAI tokenizer.
        piece = text[start:start + available].encode('utf-8')[:available].decode('utf-8', errors='ignore')
        if start + len(piece) < len(text):
            boundary = max(piece.rfind('\n'), piece.rfind(' '), piece.rfind('\t'))
            if boundary >= len(piece) // 2:
                piece = piece[:boundary + 1]
        end = start + len(piece)
        yield start, end, prefix + piece
        start = end


class HybridIndex:
    def __init__(self, store, path: Path, config: dict, embedder=None):
        self.store, self.path, self.config = store, Path(path), config
        self.cache_path = self.path / 'index.json'
        base, model, dimensions, fingerprint = embedding_settings(config)
        self.embedder = OpenAIEmbedder(config) if embedder is None else embedder
        if not callable(self.embedder):
            raise ValueError('embedder must be callable.')
        self._expected_dimensions = dimensions if embedder is None else None
        self._injected = embedder is not None
        budget = config.get('embedding_max_build_requests', MAX_BUILD_REQUESTS)
        if type(budget) is not int or not 0 <= budget <= MAX_BUILD_REQUESTS:
            raise ValueError(f'embedding_max_build_requests must be 0..{MAX_BUILD_REQUESTS}.')
        self._budget = budget
        self._metadata = {'ready': False, 'status': 'not_built', 'model': model, 'base': base,
                          'model_fingerprint': _hash([fingerprint, self._injected, SCHEMA_VERSION]),
                          'embedding_backend': 'injected' if self._injected else 'provider',
                          'dimensions': dimensions, 'cache_hit': False,
                          'usage': {'build': _usage(), 'query': _usage()},
                          'limits': {'documents': MAX_DOCUMENTS, 'fragments': MAX_FRAGMENTS,
                                     'source_bytes': MAX_SOURCE_BYTES, 'chunks': MAX_CHUNKS,
                                     'input_bytes': MAX_INPUT_BYTES, 'batch_size': BATCH_SIZE,
                                     'build_requests': budget, 'candidate_limit': CANDIDATE_LIMIT,
                                     'heading_depth': MAX_HEADING_DEPTH}}
        self._chunks, self._vectors = [], []

    @property
    def metadata(self):
        return deepcopy(self._metadata)

    def _snapshot(self):
        if len(self.store.documents) > MAX_DOCUMENTS or len(self.store.fragments) > MAX_FRAGMENTS:
            raise ValueError('Document/fragment index limit exceeded; nothing was truncated.')
        documents = {key: {field: doc.get(field) for field in
                           ('id', 'name', 'role', 'sha256', 'version', 'read_status')}
                     for key, doc in self.store.documents.items()}
        if any(not isinstance(key, str) or doc['id'] != key for key, doc in documents.items()):
            raise ValueError('Invalid document identity.')
        local_ids = {(fragment.get('document_id'), fragment.get('local_id', key)): key
                     for key, fragment in self.store.fragments.items()}
        sources = {}
        size = 0
        for key, fragment in self.store.fragments.items():
            if (fragment.get('id') != key or fragment.get('document_id') not in documents or
                    not isinstance(fragment.get('text'), str)):
                raise ValueError('Invalid source fragment identity or text.')
            text = fragment['text']
            size += len(text.encode('utf-8'))
            if size > MAX_SOURCE_BYTES:
                raise ValueError(f'Source exceeds {MAX_SOURCE_BYTES} bytes; nothing was truncated.')
            sources[key] = {field: fragment.get(field) for field in
                            ('id', 'document_id', 'section', 'page', 'printed_page', 'text')}
            sources[key]['heading'] = _heading(fragment, self.store.fragments, local_ids)
        return documents, sources

    def _prepare(self, sources):
        chunks, texts, empty = [], [], []
        for fragment_id, fragment in sources.items():
            if not fragment['text'].strip():
                empty.append(fragment_id)
                continue
            for start, end, text in _split(fragment['text'], fragment['heading']):
                if len(chunks) >= MAX_CHUNKS:
                    raise ValueError(f'Index exceeds {MAX_CHUNKS} chunks; nothing was truncated.')
                chunks.append({'id': fragment_id, 'start': start, 'end': end,
                               'input_hash': _hash(text), 'terms': dict(Counter(_tokens(text)))})
                texts.append(text)
        return chunks, texts, empty

    def _embed(self, texts, phase, dimensions):
        usage = self._metadata['usage'][phase]
        usage['attempted_requests'] += 1
        requests_before = 0 if self._injected else self.embedder.request_count
        try:
            vectors = self.embedder(texts)
            checked = validate_vectors(vectors, len(texts), dimensions)
        finally:
            if not self._injected:
                usage['provider_requests'] += self.embedder.request_count - requests_before
            reported = None if self._injected else self.embedder.last_usage
            if reported is None:
                usage['token_usage_complete'] = False
            else:
                for key in ('prompt_tokens', 'total_tokens'):
                    usage[key] += reported[key]
        usage['successful_requests'] += 1
        usage['embedded_texts'] += len(texts)
        return checked

    def _load(self, identity, chunks):
        if not self.cache_path.exists():
            return None
        try:
            with self.cache_path.open('rb') as handle:
                raw = handle.read(MAX_CACHE_BYTES + 1)
            if len(raw) > MAX_CACHE_BYTES:
                raise ValueError('Index cache exceeds its size limit.')
            cached = json.loads(raw)
            if not isinstance(cached, dict):
                raise ValueError('Invalid cache object.')
            if cached.get('identity') != identity:
                return None
            payload = cached['payload']
            if cached['checksum'] != _hash(payload) or payload['chunks'] != chunks:
                raise ValueError('Index cache checksum/input mismatch.')
            dimensions = payload['dimensions']
            if type(dimensions) is not int or dimensions < (1 if chunks else 0):
                raise ValueError('Invalid cache dimensions.')
            if chunks and self._expected_dimensions is not None and dimensions != self._expected_dimensions:
                raise ValueError('Cached dimensions do not match the model.')
            if len(chunks) * dimensions > MAX_VECTOR_COMPONENTS:
                raise ValueError('Index vector limit exceeded.')
            vectors = validate_vectors(payload['vectors'], len(chunks), dimensions)
            if not isinstance(payload['build_usage'], dict) or set(payload['build_usage']) != set(_usage()):
                raise ValueError('Invalid cache usage metadata.')
            if any(type(value) is not int or value < 0 for key, value in payload['build_usage'].items()
                   if key != 'token_usage_complete') or type(payload['build_usage']['token_usage_complete']) is not bool:
                raise ValueError('Invalid cache usage values.')
            return vectors, dimensions, payload['build_usage']
        except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError):
            raise ValueError('Index cache is invalid or unreadable; remove it and explicitly rebuild. No partial cache was accepted.') from None

    def _persist(self, identity, payload):
        raw = json.dumps({'identity': identity, 'payload': payload, 'checksum': _hash(payload)},
                         ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()
        if len(raw) > MAX_CACHE_BYTES:
            raise ValueError('Index cache exceeds its size limit; no cache was replaced.')
        self.path.mkdir(parents=True, exist_ok=True)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', dir=self.path, prefix=self.cache_path.name + '.',
                                             suffix='.tmp', delete=False) as handle:
                temp = Path(handle.name)
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.cache_path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)

    def build(self):
        self._metadata.update(ready=False, status='building', cache_hit=False)
        try:
            documents, sources = self._snapshot()
            chunks, texts, empty = self._prepare(sources)
            identity = {'schema': SCHEMA_VERSION, 'model_fingerprint': self._metadata['model_fingerprint'],
                        'input_hash': _hash([documents, sources]),
                        'embedding_input_hash': _hash([chunk['input_hash'] for chunk in chunks])}
            required = math.ceil(len(texts) / BATCH_SIZE)
            self._metadata.update(input_hash=identity['input_hash'], fragment_count=len(sources),
                                  document_count=len(documents), chunk_count=len(chunks), empty_fragment_ids=empty,
                                  planned_build_requests=required,
                                  planned_build_token_upper_bound=sum(len(text.encode('utf-8')) for text in texts))
            cached = self._load(identity, chunks)
            if cached is not None:
                vectors, dimensions, build_usage = cached
                self._metadata.update(cache_hit=True, planned_build_requests=0, planned_build_token_upper_bound=0)
            else:
                if required > self._budget:
                    raise ValueError(f'Build requires {required} embedding requests; budget is {self._budget}. No request was sent.')
                dimensions = self._expected_dimensions
                if dimensions and len(chunks) * dimensions > MAX_VECTOR_COMPONENTS:
                    raise ValueError('Index vector limit exceeded before embedding.')
                vectors = []
                for start in range(0, len(texts), BATCH_SIZE):
                    batch = self._embed(texts[start:start + BATCH_SIZE], 'build', dimensions)
                    dimensions = len(batch[0])
                    if len(chunks) * dimensions > MAX_VECTOR_COMPONENTS:
                        raise ValueError('Index vector limit exceeded; index was not accepted.')
                    vectors.extend(batch)
                dimensions = dimensions or 0
                build_usage = deepcopy(self._metadata['usage']['build'])
                self._persist(identity, {'chunks': chunks, 'vectors': vectors, 'dimensions': dimensions,
                                         'build_usage': build_usage})
            self._documents, self._sources = documents, sources
            self._chunks, self._vectors = chunks, vectors
            self._norms = [math.hypot(*vector) for vector in vectors]
            self._metadata.update(ready=True, status='ready', dimensions=dimensions, index_build_usage=build_usage)
            return self.metadata
        except Exception as exc:
            self._metadata.update(ready=False, status='error')
            self._chunks, self._vectors = [], []
            if isinstance(exc, ValueError):
                raise
            raise ValueError('Hybrid index build failed; no partial index was accepted.') from None

    def search(self, query, role=None, document_id=None, limit=8):
        if not isinstance(query, str) or not query.strip() or len(query) > 500:
            raise ValueError('Search query must contain 1..500 characters.')
        if not isinstance(role, (str, type(None))) or role not in ROLES:
            raise ValueError('Unknown version role filter.')
        if document_id is not None and (not isinstance(document_id, str) or document_id not in self.store.documents):
            raise ValueError('Unknown document filter.')
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError('Search limit must be 1..20.')
        if not self._metadata['ready']:
            raise ValueError('Hybrid index is not ready; build() must succeed before search.')
        if self._snapshot() != (self._documents, self._sources):
            self._metadata.update(ready=False, status='stale')
            raise ValueError('Sources changed; rebuild the hybrid index before search.')
        searched = [key for key, doc in self._documents.items()
                    if (document_id is None or key == document_id) and
                    (role is None or _role(doc) in {role, 'common', 'unknown'})]
        eligible = set(searched)
        candidates = [i for i, chunk in enumerate(self._chunks)
                      if self._sources[chunk['id']]['document_id'] in eligible]
        hits = []
        candidate_count = 0
        if candidates:
            query_vector = self._embed([query], 'query', self._metadata['dimensions'])[0]
            norm = math.hypot(*query_vector)
            query_terms = set(_tokens(query))
            df = Counter(term for i in candidates for term in self._chunks[i]['terms'] if term in query_terms)
            lengths = {i: sum(self._chunks[i]['terms'].values()) for i in candidates}
            average = sum(lengths.values()) / len(candidates) or 1
            scores = {}
            for i in candidates:
                chunk = self._chunks[i]
                lexical = 0.0
                for term in query_terms:
                    frequency = chunk['terms'].get(term, 0)
                    if frequency:
                        inverse = math.log(1 + (len(candidates) - df[term] + .5) / (df[term] + .5))
                        lexical += inverse * frequency * 2.2 / (frequency + 1.2 * (.25 + .75 * lengths[i] / average))
                semantic = max(-1.0, min(1.0, math.fsum((a / norm) * (b / self._norms[i])
                                                       for a, b in zip(query_vector, self._vectors[i]))))
                entry = scores.setdefault(chunk['id'], {'lexical_score': 0.0, 'semantic_score': -1.0,
                                                         'lexical_chunk': i, 'semantic_chunk': i})
                if lexical > entry['lexical_score']:
                    entry.update(lexical_score=lexical, lexical_chunk=i)
                if semantic > entry['semantic_score']:
                    entry.update(semantic_score=semantic, semantic_chunk=i)
            candidate_count = len(scores)
            lexical_order = sorted((key for key in scores if scores[key]['lexical_score'] > 0),
                                   key=lambda key: (-scores[key]['lexical_score'], key))[:CANDIDATE_LIMIT]
            semantic_order = sorted(scores, key=lambda key: (-scores[key]['semantic_score'], key))[:CANDIDATE_LIMIT]
            fused = Counter()
            for order in (lexical_order, semantic_order):
                for rank, key in enumerate(order, 1):
                    fused[key] += 1 / (60 + rank)
            for key in sorted(fused, key=lambda key: (-fused[key], -scores[key]['semantic_score'], key))[:limit]:
                fragment = self._sources[key]
                doc = self._documents[fragment['document_id']]
                entry = scores[key]
                chunk = self._chunks[entry['lexical_chunk'] if entry['lexical_score'] > 0 else entry['semantic_chunk']]
                start = chunk['start']
                for match in re.finditer(r'\w+', fragment['text'][chunk['start']:chunk['end']]):
                    if query_terms.intersection(_tokens(match.group())):
                        start += max(0, match.start() - 100)
                        break
                end = min(chunk['end'], start + 450)
                hits.append({'id': key, 'document_id': doc['id'], 'document_name': doc['name'],
                             'role': _role(doc), 'section': fragment['section'],
                             'page': fragment['page'], 'printed_page': fragment['printed_page'],
                             'snippet': fragment['text'][start:end],
                             'source_start': start, 'source_end': end,
                             'lexical_score': entry['lexical_score'], 'semantic_score': entry['semantic_score'],
                             'fusion_score': fused[key], 'score': fused[key]})
        result = {'method': 'hybrid', 'query': query, 'hits': hits, 'matched_count': candidate_count,
                  'candidate_count': candidate_count, 'searched_document_ids': searched,
                  'truncated': candidate_count > limit, 'candidate_limit': CANDIDATE_LIMIT,
                  'fusion': 'reciprocal_rank_60', 'limitation': LIMITATION}
        self.store.actions.append({'tool': 'search', 'arguments': {'query': query, 'role': role,
                                                                  'document_id': document_id, 'limit': limit},
                                   'result': result})
        return result
