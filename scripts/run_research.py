"""Prepare a bundle once, then run one model-directed investigator."""
import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from packets import read_packet
from research_agent import prepare_research,restore_research,run_research,public_result
from research_state import atomic_json


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser()
    parser.add_argument('--auto',type=Path,nargs='+')
    parser.add_argument('--before',type=Path,nargs='+')
    parser.add_argument('--after',type=Path,nargs='+')
    parser.add_argument('--case')
    parser.add_argument('--resume',type=Path)
    parser.add_argument('--model',default=os.getenv('OPENAI_MODEL','gpt-5.4'))
    parser.add_argument('--embedding-model',default='text-embedding-3-small')
    parser.add_argument('--reasoning-effort',choices=['none','low','medium','high'])
    parser.add_argument('--task',default='Исследуй изменения структуры и функций в комплекте. Найди подтверждённые изменения и кандидаты рисков, проверяя источники и ограничения. Сохранённые функции можно опустить.')
    parser.add_argument('--max-calls',type=int,default=24)
    parser.add_argument('--max-seconds',type=int,default=240)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    config={'model':args.model,'embedding_model':args.embedding_model}
    if args.reasoning_effort: config['reasoning_effort']=args.reasoning_effort
    if args.resume:
        if any([args.auto,args.before,args.after,args.case]): parser.error('Возобновление не принимает новые источники.')
        path=args.resume.resolve()
        if not path.is_relative_to((ROOT/'output'/'research').resolve()): parser.error('Исследование должно находиться в output/research.')
        state,store,index=restore_research(path,config)
    else:
        if args.case:
            if any([args.auto,args.before,args.after]) or not re.fullmatch(r'C\d{3}',args.case): parser.error('Некорректный выбор комплекта.')
            paths=[(p,None) for p in sorted((ROOT/'osnovanie_dataset_v1'/'inputs'/args.case).rglob('*.pdf'))]
            mode='auto'
        elif args.auto:
            if args.before or args.after: parser.error('Выберите автоматический либо ручной режим.')
            paths=[(p,None) for p in args.auto];mode='auto'
        else:
            paths=[(p,'before') for p in args.before or []]+[(p,'after') for p in args.after or []];mode='manual'
        if not paths: parser.error('Укажите комплект PDF/DOCX.')
        values=[{'name':p.name,'data':base64.b64encode(p.read_bytes()).decode(),**({'role':role} if role else {})} for p,role in paths]
        packet=read_packet(values,mode)
        state,store,index=prepare_research(packet,args.task,config,
            budget={'max_tool_calls':args.max_calls,'max_model_calls':args.max_calls,'max_seconds':args.max_seconds},originals=values)
    if index and not args.prepare_only: run_research(state,store,index,config)
    result=public_result(state)
    atomic_json(state.path/'result.json',result,state.secrets)
    print(json.dumps({'path':str(state.path),'status':result['status'],'findings':len(result['findings']),
                      'hypotheses':len(result['hypotheses']),'budget':result['budget'],'stop_reason':result['stop_reason']},ensure_ascii=False))
    return 0 if result['status'] in {'completed','ready','insufficient_data','needs_clarification'} else 1


if __name__=='__main__':
    raise SystemExit(main())
