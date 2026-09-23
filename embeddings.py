"""Bounded embeddings through the application's shared, authenticated transport."""
import hashlib
import json
import math
import os
from urllib.parse import urlparse

import llm


MAX_INPUT_BYTES = 6000
BATCH_SIZE = 32
MAX_DIMENSIONS = 4096


def embedding_settings(config):
    model = config.get('embedding_model', 'text-embedding-3-small')
    if not isinstance(model, str) or not model.strip() or len(model) > 256:
        raise ValueError('A valid embedding_model is required.')
    model = model.strip()
    base = str(config.get('base') or os.getenv('OPENAI_BASE_URL') or
               'https://api.openai.com/v1').rstrip('/')
    parsed = urlparse(base)
    local = parsed.hostname in {'localhost', '127.0.0.1', '::1'}
    if (not parsed.hostname or
            (parsed.scheme != 'https' and not (local and parsed.scheme == 'http')) or
            parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError('Invalid embeddings API base URL.')
    default_dimensions = 512 if model.startswith('text-embedding-3-') else None
    dimensions = config.get('embedding_dimensions', default_dimensions)
    if dimensions is not None and (type(dimensions) is not int or
                                   not 1 <= dimensions <= MAX_DIMENSIONS):
        raise ValueError(f'embedding_dimensions must be 1..{MAX_DIMENSIONS} or None.')
    identity = {'base': base, 'model': model, 'dimensions': dimensions}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return base, model, dimensions, fingerprint


def validate_vectors(vectors, count, dimensions=None):
    """Reject incomplete, ragged, nonfinite and zero vectors before accepting a batch."""
    if not isinstance(vectors, list) or len(vectors) != count:
        raise ValueError('Embedding response count does not match the input count.')
    checked = []
    for vector in vectors:
        if not isinstance(vector, list) or not 1 <= len(vector) <= MAX_DIMENSIONS:
            raise ValueError('Invalid embedding vector dimensions.')
        if dimensions is None:
            dimensions = len(vector)
        if len(vector) != dimensions:
            raise ValueError('Embedding dimensions changed or do not match the requested dimensions.')
        if any(type(value) not in (int, float) for value in vector):
            raise ValueError('Embedding components must be finite numbers.')
        try:
            values = [float(value) for value in vector]
            norm = math.hypot(*values)
        except (OverflowError, ValueError):
            raise ValueError('Embedding components must be finite numbers.') from None
        if not all(math.isfinite(value) for value in values) or not math.isfinite(norm) or norm == 0:
            raise ValueError('Embedding vectors must have a finite, nonzero norm.')
        checked.append(values)
    return checked


class OpenAIEmbedder:
    def __init__(self, config):
        self.config = config
        self.base, self.model, self.dimensions, self.fingerprint = embedding_settings(config)
        self.last_usage = None
        self.request_count = 0

    def __call__(self, texts):
        self.last_usage = None
        if not isinstance(texts, list) or not 1 <= len(texts) <= BATCH_SIZE:
            raise ValueError(f'Embedding batches must contain 1..{BATCH_SIZE} texts.')
        if any(not isinstance(text, str) or not text or
               len(text.encode('utf-8')) > MAX_INPUT_BYTES for text in texts):
            raise ValueError(f'Each embedding input must be nonempty and at most {MAX_INPUT_BYTES} UTF-8 bytes.')
        timeout = self.config.get('_embedding_timeout_seconds', 60)
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise ValueError('Embedding deadline exhausted or timeout invalid (must be >0 and <=120 seconds).')
        body = {'model': self.model, 'input': texts, 'encoding_format': 'float'}
        if self.dimensions is not None:
            body['dimensions'] = self.dimensions
        # Pin identity to the index; only credentials and the deadline remain dynamic.
        self.request_count += 1
        response = llm.request_json_api({**self.config, 'base': self.base}, '/embeddings', body,
                                        timeout_seconds=timeout, max_bytes=16_000_000)
        if not isinstance(response, dict):
            raise ValueError('Invalid embeddings API response.')
        usage = response.get('usage')
        if isinstance(usage, dict) and all(type(usage.get(key)) is int and usage[key] >= 0
                                           for key in ('prompt_tokens', 'total_tokens')):
            self.last_usage = {key: usage[key] for key in ('prompt_tokens', 'total_tokens')}
        if response.get('model', self.model) != self.model:
            raise ValueError('Embeddings API returned a different model.')
        data = response.get('data')
        if not isinstance(data, list) or len(data) != len(texts):
            raise ValueError('Embedding response count does not match the input count.')
        ordered = [None] * len(texts)
        for item in data:
            if (not isinstance(item, dict) or type(item.get('index')) is not int or
                    not 0 <= item['index'] < len(texts) or ordered[item['index']] is not None):
                raise ValueError('Embedding response has invalid or duplicate input indexes.')
            ordered[item['index']] = item.get('embedding')
        return validate_vectors(ordered, len(texts), self.dimensions)
