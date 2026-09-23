"""Technical retrieval contracts with controlled vectors, not a semantic evaluation."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from ayqyn.documents.store import DocumentStore
from ayqyn.documents.analyzer import parse_docx
from ayqyn.providers.embeddings import BATCH_SIZE, MAX_INPUT_BYTES
from ayqyn.retrieval.hybrid import HybridIndex, _hash
from test_analyzer import docx, para


def store_for(rows):
    documents = {}
    for document_id, role, fragment_id, text, metadata in rows:
        doc = documents.setdefault(document_id, {'id': document_id, 'name': document_id + '.docx',
                                                 'role': role, 'format': 'docx', 'read_status': 'read',
                                                 'paragraphs': [], 'warnings': [], 'sha256': document_id})
        doc['paragraphs'].append({'id': fragment_id, 'document_id': document_id, 'section': '1',
                                  'text': text, 'page': None, **metadata})
    return DocumentStore({'documents': list(documents.values()), 'complete_read': True, 'mixed': False})


class ControlledEmbedder:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}
        self.calls = []

    def __call__(self, texts):
        self.calls.append(list(texts))
        return [self.mapping.get(text, [1.0, 0.0, 0.0]) for text in texts]


class HybridTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'hybrid' / 'index.json'
        self.store = store_for([('after', 'after', 'a1', 'Maintains incident records.', {}),
                                ('after', 'after', 'a2', 'Orders office supplies.', {})])

    def index(self, store=None, embedder=None, config=None, path=None):
        return HybridIndex(store or self.store, path or self.path.parent, config or {},
                           ControlledEmbedder() if embedder is None else embedder)

    def test_build_and_search_preserve_actual_read_ids_and_source_evidence(self):
        self.store.read_section('a1')
        before = deepcopy(self.store.packet)
        read_ids = self.store.read_ids.copy()
        coverage = self.store.get_coverage()['documents']
        index = self.index()
        self.assertFalse(index.metadata['ready'])
        with self.assertRaisesRegex(ValueError, 'build'):
            index.search('incident')
        index.build()
        hit = index.search('incident')['hits'][0]
        self.assertEqual(self.store.read_ids, read_ids)
        self.assertEqual(self.store.packet, before)
        self.assertEqual(self.store.get_coverage()['documents'], coverage)
        self.assertTrue(self.store.check_evidence(hit['id'], hit['snippet'])['exists'])
        fresh = store_for([('a', 'after', 'f', 'incident', {})])
        fresh_index = self.index(store=fresh, path=Path(self.temp.name) / 'fresh.json')
        fresh_index.build()
        fresh_index.search('incident')
        self.assertEqual(fresh.read_ids, set())

    def test_controlled_paraphrase_and_lexical_fusion(self):
        query = 'logs network failures'
        embedder = ControlledEmbedder({'Maintains incident records.': [1, 0, 0],
                                       'Orders office supplies.': [0, 1, 0], query: [1, 0, 0]})
        index = self.index(embedder=embedder)
        index.build()
        result = index.search(query, limit=1)
        hit = result['hits'][0]
        self.assertEqual(result['method'], 'hybrid')
        self.assertEqual(hit['id'], 'a1')
        self.assertEqual(hit['lexical_score'], 0)
        self.assertAlmostEqual(hit['semantic_score'], 1)
        self.assertGreater(hit['fusion_score'], 0)
        self.assertEqual(hit['score'], hit['fusion_score'])
        self.assertEqual(embedder.calls[-1], [query])
        self.assertEqual(len(embedder.calls), 2)
        lexical = index.search('supplies')['hits'][0]
        self.assertEqual(lexical['id'], 'a2')
        self.assertGreater(lexical['lexical_score'], 0)

    def test_filters_precede_ranking_and_keep_common_unknown_and_missing_roles(self):
        rows = [('b', 'before', f'b{i}', 'target', {}) for i in range(90)]
        rows += [('a', 'after', 'a1', 'target', {}), ('c', 'common', 'c1', 'target', {}),
                 ('u', 'unknown', 'u1', 'target', {}), ('m', None, 'm1', 'target', {}),
                 ('v', 'unresolved', 'v1', 'target', {})]
        store = store_for(rows)
        index = self.index(store=store)
        index.build()
        result = index.search('target', role='after')
        self.assertEqual({hit['id'] for hit in result['hits']}, {'a1', 'c1', 'u1', 'm1', 'v1'})
        self.assertEqual(set(result['searched_document_ids']), {'a', 'c', 'u', 'm', 'v'})
        self.assertEqual(result['candidate_count'], 5)
        self.assertEqual([hit['id'] for hit in index.search('target', document_id='u')['hits']], ['u1'])
        self.assertEqual(index.search('target', role='after', document_id='b')['hits'], [])
        # Excluded documents cannot change even the lexical score of an allowed hit.
        subset = self.index(store=store_for(rows[-5:]), path=Path(self.temp.name) / 'subset.json')
        subset.build()
        self.assertEqual(result['hits'], subset.search('target', role='after')['hits'])

    def test_chunking_keeps_unicode_tail_and_deduplicates_fragment_ids(self):
        original = ('\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \U0001f680\n' * 950) + ' unique_tail_marker'
        store = store_for([('a', 'after', 'long', original, {'heading': 'Reliable heading'})])
        embedder = ControlledEmbedder()
        index = self.index(store=store, embedder=embedder)
        index.build()
        texts = [text for batch in embedder.calls for text in batch]
        self.assertGreater(len(texts), 1)
        self.assertTrue(all(text.startswith('Reliable heading\n\n') for text in texts))
        self.assertTrue(all(len(text.encode('utf-8')) <= MAX_INPUT_BYTES for text in texts))
        payload = json.loads(self.path.read_text())['payload']
        chunks = payload['chunks']
        self.assertEqual(''.join(original[chunk['start']:chunk['end']] for chunk in chunks), original)
        self.assertEqual(chunks[0]['start'], 0)
        self.assertEqual(chunks[-1]['end'], len(original))
        result = index.search('unique_tail_marker')
        self.assertEqual([hit['id'] for hit in result['hits']], ['long'])
        self.assertGreater(result['hits'][0]['lexical_score'], 0)
        hit = result['hits'][0]
        self.assertEqual(hit['snippet'], original[hit['source_start']:hit['source_end']])
        self.assertIn('unique_tail_marker', hit['snippet'])
        self.assertEqual(store.fragments['long']['text'], original)
        self.assertNotIn('text', chunks[0])

    def test_heading_metadata_nearest_parent_and_document_boundaries(self):
        store = store_for([('a', 'after', 'h', 'Audit owners', {'type': 'heading'}),
                           ('a', 'after', 'p', 'intermediate', {'parent_id': 'h'}),
                           ('a', 'after', 'f', 'checks accounts', {'parent_id': 'p'}),
                           ('a', 'after', 's', 'checks reports', {'heading_path': ['Root', 'Nearest']}),
                           ('b', 'after', 'x', 'checks exports', {'parent_id': 'h'}),
                           ('b', 'after', 'y', 'checks deliveries', {'section': 'Explicit section title'})])
        embedder = ControlledEmbedder()
        self.index(store=store, embedder=embedder).build()
        texts = embedder.calls[0]
        self.assertIn('Audit owners\n\nchecks accounts', texts)
        self.assertIn('Nearest\n\nchecks reports', texts)
        self.assertIn('checks exports', texts)
        self.assertIn('Explicit section title\n\nchecks deliveries', texts)

    def test_real_docx_heading_metadata_with_local_parent_ids(self):
        body = para('1. Audit owners', '<w:pPr><w:outlineLvl w:val="0"/></w:pPr>')
        body += para('1.1. Audit checks', '<w:pPr><w:outlineLvl w:val="1"/></w:pPr>')
        body += para('1.1.1. Reviews records')
        document = parse_docx(docx(body), 'audit.docx')
        document.update(id='audit', role='after', read_status='read', warnings=[])
        for fragment in document['paragraphs']:
            fragment.update(local_id=fragment['id'], id='audit:' + fragment['id'], document_id='audit')
        store = DocumentStore({'documents': [document], 'complete_read': True, 'mixed': False})
        embedder = ControlledEmbedder()
        self.index(store=store, embedder=embedder).build()
        self.assertIn('1.1. Audit checks\n\n1.1.1. Reviews records', embedder.calls[0])
        self.assertEqual(store.read_ids, set())

    def test_cache_reuse_keeps_no_keys_and_does_not_embed_documents_again(self):
        embedder = ControlledEmbedder()
        first = self.index(embedder=embedder, config={'key': 'secret-one'})
        first.build()
        first_usage = first.metadata['usage']['build']
        self.assertEqual(first_usage['successful_requests'], 1)
        self.assertEqual(first_usage['embedded_texts'], 2)
        self.assertFalse(first_usage['token_usage_complete'])
        self.assertEqual(first_usage['provider_requests'], 0)
        self.assertNotIn('secret-one', self.path.read_text())
        again = self.index(embedder=embedder, config={'key': 'secret-two', 'embedding_max_build_requests': 0})
        again.build()
        self.assertTrue(again.metadata['cache_hit'])
        self.assertEqual(again.metadata['planned_build_requests'], 0)
        self.assertEqual(again.metadata['planned_build_token_upper_bound'], 0)
        self.assertEqual(again.metadata['usage']['build']['attempted_requests'], 0)
        self.assertEqual(again.metadata['index_build_usage'], first_usage)
        self.assertEqual(len(embedder.calls), 1)
        self.assertEqual(first.search('incident')['hits'], again.search('incident')['hits'])

    def test_cache_identity_tracks_text_heading_role_model_base_and_dimensions(self):
        changes = [('text', 'Changed source'), ('heading', 'New heading'), ('role', 'before'),
                   ('embedding_model', 'other'), ('base', 'https://other.example/v1'), ('embedding_dimensions', 256)]
        for field, value in changes:
            with self.subTest(field=field):
                path = Path(self.temp.name) / (field + '.json')
                store = deepcopy(self.store)
                first = self.index(store=store, path=path)
                first.build()
                config = {}
                if field == 'role':
                    store.documents['after']['role'] = value
                elif field in {'text', 'heading'}:
                    store.fragments['a1'][field] = value
                else:
                    config[field] = value
                embedder = ControlledEmbedder()
                second = self.index(store=store, path=path, config=config, embedder=embedder)
                second.build()
                self.assertFalse(second.metadata['cache_hit'])
                self.assertEqual(len(embedder.calls), 1)

    def test_corrupt_cache_is_rejected_without_calls_or_partial_readiness(self):
        self.index().build()
        original = self.path.read_text()
        for mutation in ('checksum', 'count', 'dimensions', 'nonfinite', 'usage'):
            with self.subTest(mutation=mutation):
                cached = json.loads(original)
                payload = cached['payload']
                if mutation == 'checksum':
                    payload['vectors'][0][0] += 1
                elif mutation == 'count':
                    payload['vectors'].pop()
                elif mutation == 'dimensions':
                    payload['dimensions'] = 4
                elif mutation == 'nonfinite':
                    payload['vectors'][0][0] = float('nan')
                else:
                    payload['build_usage']['prompt_tokens'] = 'secret'
                if mutation not in {'checksum', 'nonfinite'}:
                    cached['checksum'] = _hash(payload)
                self.path.write_text(json.dumps(cached))
                embedder = ControlledEmbedder()
                index = self.index(embedder=embedder)
                with self.assertRaisesRegex(ValueError, 'No partial cache'):
                    index.build()
                self.assertFalse(index.metadata['ready'])
                self.assertEqual(embedder.calls, [])
                with self.assertRaises(ValueError):
                    index.search('incident')

    def test_injected_cache_cannot_be_used_by_real_provider(self):
        self.index().build()
        index = HybridIndex(self.store, self.path.parent, {'embedding_max_build_requests': 0})
        with patch('ayqyn.providers.embeddings.llm.request_json_api') as request, self.assertRaisesRegex(ValueError, 'budget'):
            index.build()
        request.assert_not_called()

    def test_build_budget_checked_before_any_call_and_batches_bounded(self):
        store = store_for([('a', 'after', f'f{i}', f'source {i}', {}) for i in range(BATCH_SIZE + 1)])
        embedder = ControlledEmbedder()
        index = self.index(store=store, embedder=embedder, config={'embedding_max_build_requests': 1})
        with self.assertRaisesRegex(ValueError, 'requires 2'):
            index.build()
        self.assertEqual(embedder.calls, [])
        index = self.index(store=store, embedder=embedder, config={'embedding_max_build_requests': 2})
        index.build()
        self.assertEqual([len(call) for call in embedder.calls], [BATCH_SIZE, 1])
        self.assertEqual(index.metadata['usage']['build']['attempted_requests'], 2)
        self.assertEqual(index.metadata['planned_build_token_upper_bound'],
                         sum(len(text.encode('utf-8')) for batch in embedder.calls for text in batch))

    def test_failed_later_batch_preserves_previous_cache_and_reports_attempts(self):
        self.index().build()
        prior_cache = self.path.read_bytes()
        store = store_for([('a', 'after', f'f{i}', 'source', {}) for i in range(BATCH_SIZE + 1)])
        embedder = Mock(side_effect=[[[1, 0]] * BATCH_SIZE, ValueError('Embeddings unavailable')])
        index = self.index(store=store, embedder=embedder)
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            index.build()
        self.assertFalse(index.metadata['ready'])
        self.assertEqual(index.metadata['usage']['build']['attempted_requests'], 2)
        self.assertEqual(index.metadata['usage']['build']['successful_requests'], 1)
        self.assertEqual(self.path.read_bytes(), prior_cache)
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])

    def test_atomic_replace_failure_preserves_old_cache(self):
        self.index().build()
        prior_cache = self.path.read_bytes()
        self.store.fragments['a1']['text'] = 'changed'
        index = self.index()
        with patch('ayqyn.retrieval.hybrid.os.replace', side_effect=OSError('disk failure')), self.assertRaises(ValueError):
            index.build()
        self.assertEqual(self.path.read_bytes(), prior_cache)
        self.assertFalse(index.metadata['ready'])
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])

    def test_embedding_failure_never_falls_back_to_lexical(self):
        for vectors in ([], [[1, 0]], [[1, 0], [1]], [[float('nan'), 0]] * 2):
            with self.subTest(vectors=vectors):
                index = self.index(embedder=Mock(return_value=vectors))
                with self.assertRaises(ValueError):
                    index.build()
                self.assertFalse(index.metadata['ready'])
                self.assertFalse(self.path.exists())
        embedder = Mock(side_effect=[[[1, 0]] * 2, [[1, 0, 0]]])
        index = self.index(embedder=embedder)
        index.build()
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            index.search('incident')
        self.assertEqual(self.store.read_ids, set())

    def test_source_changes_require_rebuild_but_reads_do_not(self):
        index = self.index()
        index.build()
        self.store.read_section('a1')
        index.search('incident')
        self.store.fragments['a1']['text'] = 'new text'
        with self.assertRaisesRegex(ValueError, 'Sources changed'):
            index.search('incident')
        self.assertFalse(index.metadata['ready'])

    def test_empty_index_and_empty_filter_need_no_query_embeddings(self):
        store = store_for([('a', 'after', 'empty', '  \n', {})])
        embedder = ControlledEmbedder()
        index = self.index(store=store, embedder=embedder)
        index.build()
        self.assertEqual(index.metadata['empty_fragment_ids'], ['empty'])
        self.assertEqual(index.search('query')['hits'], [])
        cached = self.index(store=store, embedder=embedder)
        cached.build()
        self.assertTrue(cached.metadata['cache_hit'])
        self.assertEqual(embedder.calls, [])

    def test_explicit_index_and_search_limits(self):
        for constant, value in (('MAX_SOURCE_BYTES', 5), ('MAX_CHUNKS', 1), ('MAX_FRAGMENTS', 1), ('MAX_DOCUMENTS', 0)):
            with self.subTest(constant=constant), patch('ayqyn.retrieval.hybrid.' + constant, value):
                embedder = ControlledEmbedder()
                with self.assertRaises(ValueError):
                    self.index(embedder=embedder).build()
                self.assertEqual(embedder.calls, [])
        index = self.index()
        index.build()
        for arguments in ({'query': ''}, {'query': 'x' * 501}, {'query': 'x', 'limit': True},
                          {'query': 'x', 'limit': 21}, {'query': 'x', 'role': 'invalid'},
                          {'query': 'x', 'role': []}, {'query': 'x', 'document_id': []},
                          {'query': 'x', 'document_id': 'absent'}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                index.search(**arguments)

    def test_provider_token_usage_and_deadline_reported_separately_by_phase(self):
        config = {'embedding_dimensions': 2, '_embedding_timeout_seconds': 1.25}
        index = HybridIndex(self.store, self.path.parent, config)
        def provider(_config, _endpoint, body, **_kwargs):
            return {'model': 'text-embedding-3-small',
                    'data': [{'index': i, 'embedding': [1, 0]} for i in range(len(body['input']))],
                    'usage': {'prompt_tokens': 10, 'total_tokens': 10}}
        with patch('ayqyn.providers.embeddings.llm.request_json_api', side_effect=provider) as request:
            index.build()
            config['_embedding_timeout_seconds'] = .1
            index.search('incident')
            self.assertEqual(request.call_args.kwargs['timeout_seconds'], .1)
        for phase in ('build', 'query'):
            usage = index.metadata['usage'][phase]
            self.assertEqual(usage['attempted_requests'], 1)
            self.assertEqual(usage['successful_requests'], 1)
            self.assertEqual(usage['provider_requests'], 1)
            self.assertEqual(usage['total_tokens'], 10)
            self.assertTrue(usage['token_usage_complete'])

    def test_failed_provider_batch_accounts_reported_tokens_and_expired_deadline_sends_nothing(self):
        index = HybridIndex(self.store, self.path.parent, {'embedding_dimensions': 2})
        with patch('ayqyn.providers.embeddings.llm.request_json_api', return_value={
                'data': [], 'usage': {'prompt_tokens': 13, 'total_tokens': 13}}):
            with self.assertRaises(ValueError):
                index.build()
        usage = index.metadata['usage']['build']
        self.assertEqual(usage['provider_requests'], 1)
        self.assertEqual(usage['successful_requests'], 0)
        self.assertEqual(usage['total_tokens'], 13)
        self.assertFalse(self.path.exists())
        expired = HybridIndex(self.store, self.path.parent, {'_embedding_timeout_seconds': 0})
        with patch('ayqyn.providers.embeddings.llm.request_json_api') as request, self.assertRaises(ValueError):
            expired.build()
        request.assert_not_called()
        self.assertEqual(expired.metadata['usage']['build']['provider_requests'], 0)


if __name__ == '__main__':
    unittest.main()
