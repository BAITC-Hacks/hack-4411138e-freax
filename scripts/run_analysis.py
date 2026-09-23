"""Run the unchanged baseline once and retain request/response evidence."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ayqyn.documents.analyzer import parse_docx
from ayqyn.providers.llm import compare_with_model
from ayqyn.storage.runs import new_run_path


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--model', default=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
    parser.add_argument('--functions', action='store_true')
    parser.add_argument('--sections', nargs='+')
    args = parser.parse_args()
    before = parse_docx(args.before.read_bytes(), args.before.name)
    after = parse_docx(args.after.read_bytes(), args.after.name)
    path = new_run_path()
    if args.functions:
        from ayqyn.analysis.functions import analyze_functions
        result = analyze_functions(before,after,{'model':args.model},run_root=path,only_sections=args.sections)
        print(json.dumps({'run_path':str(path),'status':result['status'],'accepted':len(result['findings']),
                          'rejected':result['rejected_count'],'failed_sections':result['failed_sections']},ensure_ascii=False))
        return 0 if result['status']=='completed' else 1
    try:
        findings, rejected, usage = compare_with_model(before, after, {'model': args.model}, run_dir=path)
    except ValueError as exc:
        print(str(exc))
        if path.exists(): print('Run evidence:', path)
        return 1
    print(json.dumps({'run_path': str(path), 'accepted': len(findings), 'rejected': rejected, 'usage': usage}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
