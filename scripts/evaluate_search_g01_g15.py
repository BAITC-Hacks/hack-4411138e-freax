"""Fixed retrieval diagnostic; gold labels are read only after ranking.

No investigator is started. Live query embeddings require --live and a configured
OPENAI_API_KEY. Existing document vectors must pass HybridIndex cache validation.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ayqyn.documents.store import DocumentStore
from ayqyn.retrieval.hybrid import HybridIndex, _tokens
from ayqyn.providers.embeddings import OpenAIEmbedder


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bm25(index, query, role):
    # Same chunk scoring, max per fragment, positive-score filter and tie order
    # as HybridIndex.search. Live runs assert equality against its internal order.
    candidates = [i for i, c in enumerate(index._chunks)
                  if role is None or index._documents[index._sources[c['id']]['document_id']]['role']
                  in {role, 'common', 'unknown'}]
    terms = set(_tokens(query))
    df = Counter(t for i in candidates for t in index._chunks[i]['terms'] if t in terms)
    lengths = {i: sum(index._chunks[i]['terms'].values()) for i in candidates}
    average = sum(lengths.values()) / len(candidates) or 1
    scores = {}
    for i in candidates:
        c = index._chunks[i]
        score = 0.0
        for t in terms:
            f = c['terms'].get(t, 0)
            if f:
                inv = math.log(1 + (len(candidates) - df[t] + .5) / (df[t] + .5))
                score += inv * f * 2.2 / (f + 1.2 * (.25 + .75 * lengths[i] / average))
        scores[c['id']] = max(scores.get(c['id'], 0), score)
    return sorted((k for k in scores if scores[k] > 0), key=lambda k: (-scores[k], k))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, default=ROOT/'output/research/r-c2b51c77cfe64a09a59153bb65a94c5c')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'output/search-g01-g15')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    queries_path = ROOT/'docs/research/search-g01-g15-queries.json'
    labels_path = ROOT/'docs/research/search-g01-g15-labels.json'
    packet = read(args.run/'packet.json')
    store = DocumentStore(packet)
    index = HybridIndex(store, args.run/'index', {'embedding_max_build_requests': 0})
    index.build()  # Cache only: never silently rebuild or change the model.
    assert index.metadata['cache_hit']
    queries = read(queries_path)
    assert len(queries) == 30 and len({q['id'] for q in queries}) == 30
    assert all(0 < len(q['query']) <= 500 and not any(c.isdigit() for c in q['query']) for q in queries)
    if args.live:
        provider = OpenAIEmbedder({})
        vectors_path = args.output/'query-vectors.json'
        identity = {'queries_sha256': digest(queries_path), 'model_fingerprint': index.metadata['model_fingerprint']}
        if vectors_path.exists():
            saved = read(vectors_path)
            assert saved['identity'] == identity
            vectors = saved['vectors']
        else:
            vectors = provider([q['query'] for q in queries])
            vectors_path.write_text(json.dumps({'identity': identity, 'vectors': vectors,
                                               'usage': provider.last_usage}), encoding='utf-8')
        by_query = {q['query']: v for q, v in zip(queries, vectors)}
        index.embedder = lambda texts: [by_query[t] for t in texts]
        index._injected = True  # Replay real vectors; no mocks and no cache write.
    rankings = []
    for q in queries:
        for role in [None, 'before', 'after']:
            orders = {'bm25': bm25(index, q['query'], role)}
            if args.live:
                captured = {}
                def trace(frame, event, arg):
                    if frame.f_code is HybridIndex.search.__code__ and event == 'return':
                        captured.update({k: frame.f_locals[k] for k in ['lexical_order', 'semantic_order']})
                    return trace
                sys.settrace(trace)
                try:
                    hits = index.search(q['query'], role=role, limit=20)['hits']
                finally:
                    sys.settrace(None)
                assert orders['bm25'][:80] == captured['lexical_order']
                orders.update(dense=captured['semantic_order'], hybrid=[h['id'] for h in hits])
            rankings.append({'query_id': q['id'], 'filter': role, 'orders': orders})
    # Only the evaluator below reads targets. They never enter index.search.
    labels = read(labels_path)
    docs = {d['role']: d for d in packet['documents']}
    def fid(role, n):
        return docs[role]['id'] + ':p' + str(n)
    scored = []
    for r in rankings:
        label = labels[r['query_id'][:3]]
        for role in ['before', 'after'] if r['filter'] is None else [r['filter']]:
            targets = [fid(role, n) for n in label[role]['sources']]
            ranks = {mode: min([order.index(t)+1 for t in targets if t in order], default=None)
                     for mode, order in r['orders'].items()}
            scored.append({'query_id': r['query_id'], 'filter': r['filter'], 'target_role': role, 'ranks': ranks})
    contexts = []
    for gid, label in labels.items():
        for role in ['before', 'after']:
            l = label[role]
            seed = fid(role, l['sources'][0])
            full = store.read_context(seed)
            pages, offset = [], 0
            while True:
                page = store.read_context_page(seed, offset=offset)
                pages.append(page)
                if page['next_offset'] is None:
                    break
                offset = page['next_offset']
            returned = {f['id'] for p in pages for f in p['fragments']}
            assert returned == {f['id'] for f in full['fragments']}
            required = {kind: [fid(role, n) for n in l[kind]] for kind in ['owner', 'continuations', 'additional']}
            missing = {kind: [x for x in ids if x not in returned] for kind, ids in required.items()}
            # Check missing evidence is addressable separately, not auto-returned.
            explicit = {}
            for ids in missing.values():
                for target in ids:
                    p = store.read_context_page(target)
                    explicit[target] = target in {f['id'] for f in p['fragments']}
            contexts.append({'gold_id': gid, 'role': role, 'seed': seed,
                             'page_count': len(pages), 'returned_ids': sorted(returned),
                             'missing': missing, 'explicit_read_available': explicit})
    summary = []
    for variant in ['original', 'paraphrase']:
        for filtered in [False, True]:
            rows = [s for s in scored if s['query_id'].endswith(variant) and (s['filter'] is not None) == filtered]
            for mode in ['bm25', 'dense', 'hybrid']:
                summary.append({'variant': variant, 'role_filter': filtered, 'mode': mode,
                                'n': len(rows), **{f'hit@{k}': sum(s['ranks'].get(mode) is not None and s['ranks'][mode] <= k for s in rows)
                                                  if mode in rows[0]['ranks'] else None for k in [5, 10]}})
    result = {'status': 'complete' if args.live else 'partial_missing_query_embeddings',
              'run': str(args.run), 'code_sha256': {f: digest(ROOT/f) for f in ['ayqyn/retrieval/hybrid.py', 'ayqyn/providers/embeddings.py', 'ayqyn/documents/store.py', 'ayqyn/agent/tools.py']},
              'queries_sha256': digest(queries_path), 'labels_sha256': digest(labels_path),
              'packet_sha256': digest(args.run/'packet.json'), 'index_sha256': digest(args.run/'index/index.json'),
              'index_metadata': index.metadata, 'summary': summary, 'scores': scored,
              'contexts': contexts, 'rankings': rankings}
    result['fusion_displacements'] = [dict(s, cutoff=k, component=mode)
        for s in scored for k in [5, 10] for mode in ['bm25', 'dense']
        if 'hybrid' in s['ranks'] and s['ranks'].get(mode) is not None
        and s['ranks'][mode] <= k
        and (s['ranks']['hybrid'] is None or s['ranks']['hybrid'] > k)] if args.live else None
    (args.output/'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'summary': summary,
                      'context_missing': [{k: c[k] for k in ['gold_id', 'role', 'missing']} for c in contexts if any(c['missing'].values())]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
