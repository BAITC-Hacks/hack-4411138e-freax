"""Measure saved request payloads without another paid model call."""
import argparse
import json
from collections import Counter
from pathlib import Path


def size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(',', ':')))


def profile(path):
    turns = []
    for request in sorted(path.glob('turn-*/request.json')):
        data = json.loads(request.read_text(encoding='utf-8'))
        labels = {}
        groups = Counter()
        results = []
        for message in data['messages']:
            for call in message.get('tool_calls', []):
                labels[call['id']] = call['function']['name']
            name = labels.get(message.get('tool_call_id'), message['role'])
            groups[name] += size(message)
            if message['role'] != 'tool':
                continue
            result = json.loads(message['content'])
            fields = {key: size(value) for key, value in result.items()}
            fragments = result.get('fragments', [])
            results.append({'tool': name, 'chars': size(result), 'fields': fields,
                            'source_text_chars': sum(len(p['text']) for p in fragments),
                            'fragment_metadata_chars': sum(size({k: v for k, v in p.items() if k != 'text'}) for p in fragments)})
        raw = request.with_name('response.raw.json')
        response = json.loads(raw.read_text(encoding='utf-8')) if raw.exists() else {}
        turns.append({'turn': request.parent.name, 'request_chars': size(data),
                      'by_message_type': dict(groups), 'tools_schema_chars': size(data.get('tools', [])),
                      'usage': response.get('usage'), 'tool_results': results})
    return {'run': path.name, 'unit': 'serialized Unicode characters, not token estimates',
            'cumulative_request_chars': sum(t['request_chars'] for t in turns), 'turns': turns}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('runs', type=Path, nargs='+')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = [profile(path) for path in args.runs]
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    for run in result:
        print(run['run'], 'total request chars:', run['cumulative_request_chars'])
        for turn in run['turns']:
            print(turn['turn'], turn['request_chars'], turn['by_message_type'])
        for result in run['turns'][-1]['tool_results']:
            print('result', result)
