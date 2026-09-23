import math
import unittest
from unittest.mock import patch

from embeddings import BATCH_SIZE, MAX_INPUT_BYTES, OpenAIEmbedder, embedding_settings, validate_vectors


def response(vectors, model='text-embedding-3-small'):
    return {'model': model, 'data': [{'index': i, 'embedding': vector} for i, vector in enumerate(vectors)],
            'usage': {'prompt_tokens': 7, 'total_tokens': 7}}


class EmbeddingTests(unittest.TestCase):
    def test_shared_transport_default_dimensions_and_dynamic_deadline(self):
        config = {'key': 'never-persist', '_embedding_timeout_seconds': 3.5}
        embedder = OpenAIEmbedder(config)
        with patch('embeddings.llm.request_json_api', return_value=response([[1.0] * 512])) as request:
            self.assertEqual(len(embedder(['sample'])[0]), 512)
            args, kwargs = request.call_args
            self.assertEqual(args[1], '/embeddings')
            self.assertEqual(args[2], {'model': 'text-embedding-3-small', 'input': ['sample'],
                                      'encoding_format': 'float', 'dimensions': 512})
            self.assertEqual(kwargs['timeout_seconds'], 3.5)
            self.assertEqual(kwargs['max_bytes'], 16_000_000)
            config['_embedding_timeout_seconds'] = .25
            embedder(['sample'])
            self.assertEqual(request.call_args.kwargs['timeout_seconds'], .25)
        self.assertEqual(embedder.last_usage, {'prompt_tokens': 7, 'total_tokens': 7})

    def test_legacy_model_omits_unsupported_dimensions_and_orders_response_indexes(self):
        embedder = OpenAIEmbedder({'embedding_model': 'text-embedding-ada-002'})
        payload = response([[1, 0], [0, 1]], embedder.model)
        payload['data'].reverse()
        with patch('embeddings.llm.request_json_api', return_value=payload) as request:
            self.assertEqual(embedder(['first', 'second']), [[1, 0], [0, 1]])
            self.assertNotIn('dimensions', request.call_args.args[2])

    def test_provider_identity_pinned_while_credentials_remain_dynamic(self):
        config = {'base': 'https://one.example/v1', 'embedding_model': 'custom', 'key': 'first'}
        embedder = OpenAIEmbedder(config)
        config.update(base='https://two.example/v1', embedding_model='other', key='second')
        with patch('embeddings.llm.request_json_api', return_value=response([[1]], 'custom')) as request:
            embedder(['sample'])
            self.assertEqual(request.call_args.args[0]['base'], 'https://one.example/v1')
            self.assertEqual(request.call_args.args[0]['key'], 'second')
            self.assertEqual(request.call_args.args[2]['model'], 'custom')

    def test_input_and_deadline_bounds_fail_before_provider_call(self):
        with patch('embeddings.llm.request_json_api') as request:
            for texts in ([], [''], ['x'] * (BATCH_SIZE + 1), ['x' * (MAX_INPUT_BYTES + 1)], [None]):
                with self.subTest(texts=str(texts)[:30]), self.assertRaises(ValueError):
                    OpenAIEmbedder({})(texts)
            for timeout in (0, -1, True, 121, math.nan, math.inf, '1'):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    OpenAIEmbedder({'_embedding_timeout_seconds': timeout})(['sample'])
            request.assert_not_called()

    def test_response_rejects_count_indexes_model_and_dimensions(self):
        payloads = [None, {}, response([]), response([[1]], 'wrong'),
                    response([[1, 0]]), response([[0] * 512]),
                    {'data': [{'index': -1, 'embedding': [1] * 512}]},
                    {'data': [{'index': True, 'embedding': [1] * 512}]}]
        for payload in payloads:
            with self.subTest(payload=str(payload)[:70]), patch('embeddings.llm.request_json_api', return_value=payload):
                with self.assertRaises(ValueError):
                    OpenAIEmbedder({})(['sample'])
        payload = response([[1] * 512, [1] * 512])
        payload['data'][1]['index'] = 0
        with patch('embeddings.llm.request_json_api', return_value=payload), self.assertRaises(ValueError):
            OpenAIEmbedder({})(['first', 'second'])

    def test_vector_validation_accepts_only_complete_finite_nonzero_batches(self):
        for vectors in (None, [], [[0, 0]], [[math.nan, 1]], [[math.inf]], [[True]],
                        [['1']], [[10 ** 1000]], [[1], [1, 2]], [[1e308, 1e308, 1e308, 1e308]]):
            with self.subTest(vectors=str(vectors)[:70]), self.assertRaises(ValueError):
                validate_vectors(vectors, 2 if vectors == [[1], [1, 2]] else 1)
        self.assertEqual(validate_vectors([[1e-300, 0]], 1, 2), [[1e-300, 0]])

    def test_identity_uses_base_model_dimensions_but_not_key_or_chat_model(self):
        first = embedding_settings({'base': 'https://one.example/v1', 'key': 'one'})[-1]
        self.assertEqual(first, embedding_settings({'base': 'https://one.example/v1/', 'key': 'two', 'model': 'chat'})[-1])
        for config in ({'base': 'https://two.example/v1'}, {'embedding_model': 'other'}, {'embedding_dimensions': 256}):
            self.assertNotEqual(first, embedding_settings(config)[-1])
        for config in ({'base': 'https://secret@example.com/v1'}, {'base': 'https://example.com/?key=secret'},
                       {'base': 'http://remote.example/v1'}, {'embedding_dimensions': True},
                       {'embedding_dimensions': 5000}, {'embedding_model': ''}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                embedding_settings(config)


if __name__ == '__main__':
    unittest.main()
