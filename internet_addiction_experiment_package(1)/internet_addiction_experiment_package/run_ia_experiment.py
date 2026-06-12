#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run LLM experiments for the internet-addiction / problematic digital-use project.

Supports qwen, deepseek, minimax, and generic openai-compatible endpoints.
Uses batched sampling: one API call can return several independent numeric samples.
"""
from __future__ import annotations
import argparse, json, os, re, time, uuid, hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests
import pandas as pd
from tqdm import tqdm

REQUEST_TIMEOUT=180

def utc_now(): return datetime.now(timezone.utc).isoformat()
def stable_hash(obj): return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:12]

def load_jsonl(path: Path):
    out=[]
    with path.open('r',encoding='utf-8') as f:
        for i,line in enumerate(f,1):
            line=line.strip()
            if line: out.append(json.loads(line))
    return out

def append_jsonl(rec,path:Path):
    with path.open('a',encoding='utf-8') as f: f.write(json.dumps(rec,ensure_ascii=False)+'\n')

def extract_json(text):
    if text is None: return None
    text=str(text).strip()
    try: return json.loads(text)
    except Exception: pass
    m=re.search(r"```json\s*(.*?)\s*```", text, re.S|re.I)
    if m:
        try: return json.loads(m.group(1).strip())
        except Exception: pass
    m=re.search(r"\{.*\}", text, re.S)
    if m:
        try: return json.loads(m.group(0))
        except Exception: pass
    return None

def required_keys(record):
    user=record.get('user',{})
    if isinstance(user,str): raise ValueError('user must be object with required_output.json_keys')
    keys=user.get('required_output',{}).get('json_keys',{})
    if not keys: raise ValueError(f"missing json_keys in {record.get('prompt_id')}")
    return keys

def make_batched_user_prompt(record, n_samples, batch_id):
    keys=list(required_keys(record).keys())
    original = record['user'] if isinstance(record.get('user'),str) else json.dumps(record.get('user'),ensure_ascii=False,indent=2)
    wrapper={
        'task':'Return multiple independent Monte-Carlo numeric prediction samples for the same condition.',
        'batch_id':batch_id,
        'number_of_samples':n_samples,
        'strict_output_format':{'samples':[{'sample_id':1, **{k:'number' for k in keys}}]},
        'rules':[
            f'Return exactly {n_samples} samples.',
            'Return one valid JSON object only with top-level key samples.',
            'Each sample must contain sample_id and all required numeric fields.',
            'All task output fields must be numbers only.',
            'Do not use words such as low, medium, high, moderate, severe, typical, or elevated.',
            'No explanations, no markdown, no extra keys.'
        ],
        'original_prediction_prompt': original
    }
    return json.dumps(wrapper, ensure_ascii=False, indent=2)

def normalize_samples(parsed):
    if isinstance(parsed,dict):
        if 'samples' in parsed and isinstance(parsed['samples'],list): return parsed['samples']
        for k in ['response','input','output']:
            if k in parsed and isinstance(parsed[k],dict) and 'samples' in parsed[k]: return parsed[k]['samples']
    if isinstance(parsed,list): return parsed
    return None

def validate_sample(sample, keys):
    if not isinstance(sample,dict): return False
    for k in keys:
        if k not in sample: return False
        v=sample[k]
        if not isinstance(v,(int,float)) or isinstance(v,bool): return False
    return True

def provider_defaults(provider):
    provider=provider.lower()
    if provider=='qwen': return os.getenv('DASHSCOPE_API_KEY'), os.getenv('QWEN_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1')
    if provider=='deepseek': return os.getenv('DEEPSEEK_API_KEY'), os.getenv('DEEPSEEK_BASE_URL','https://api.deepseek.com/v1')
    if provider=='minimax': return os.getenv('MINIMAX_API_KEY'), os.getenv('MINIMAX_BASE_URL')
    if provider=='openai_compatible': return os.getenv('OPENAI_COMPATIBLE_API_KEY'), os.getenv('OPENAI_COMPATIBLE_BASE_URL')
    raise ValueError(f'unknown provider {provider}')

def call_openai_compatible(api_key, base_url, model, system, user, temperature, no_response_format=False):
    if not api_key: raise ValueError('missing API key')
    if not base_url: raise ValueError('missing base_url')
    payload={'model':model,'temperature':temperature,'messages':[{'role':'system','content':system},{'role':'user','content':user}]}
    if not no_response_format:
        payload['response_format']={'type':'json_object'}
    headers={'Authorization':f'Bearer {api_key}','Content-Type':'application/json'}
    r=requests.post(base_url.rstrip('/')+'/chat/completions',headers=headers,json=payload,timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    data=r.json()
    return data['choices'][0]['message']['content'], data.get('usage',{})

def existing_counts(csv_path):
    if not csv_path.exists(): return {}
    try:
        df=pd.read_csv(csv_path)
        if df.empty: return {}
        return df.groupby('prompt_id').size().to_dict()
    except Exception:
        return {}

def run(args):
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    prompts=load_jsonl(Path(args.input))
    api_key=args.api_key; base_url=args.base_url
    if not api_key or (args.provider in ['qwen','deepseek','minimax','openai_compatible'] and not base_url):
        dkey,durl=provider_defaults(args.provider)
        api_key=api_key or dkey; base_url=base_url or durl
    sample_csv=out/'sample_level_outputs.csv'
    raw_path=out/'raw_calls.jsonl'; invalid_path=out/'invalid_calls.jsonl'
    counts=existing_counts(sample_csv) if args.resume else {}
    run_id=args.run_id or f"IA_{args.provider}_{args.model}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    if args.dry_run:
        print(f'Loaded prompts: {len(prompts)}')
        print(f'Provider={args.provider}, model={args.model}, target={args.target_samples}, samples/call={args.samples_per_call}')
        for r in prompts[:10]: print(r.get('prompt_id'), r.get('condition_id'), r.get('profile_id'), r.get('task_id'))
        return
    fieldnames=None
    for rec in tqdm(prompts, desc='prompts'):
        pid=rec['prompt_id']; already=int(counts.get(pid,0)); need=max(0,args.target_samples-already)
        if need<=0: continue
        batch_id=0
        while need>0:
            n=min(args.samples_per_call, need); batch_id+=1
            call_id=str(uuid.uuid4())
            system=rec.get('system','') + '\nReturn numeric JSON only.'
            user=make_batched_user_prompt(rec,n,batch_id)
            ok=False; raw=None; parsed=None; samples=None; usage={}; err=None
            for attempt in range(args.max_retries+1):
                try:
                    raw, usage=call_openai_compatible(api_key,base_url,args.model,system,user,args.temperature,args.no_response_format)
                    parsed=extract_json(raw); samples=normalize_samples(parsed)
                    keys=required_keys(rec)
                    if samples and sum(validate_sample(s,keys) for s in samples)>=n:
                        ok=True; break
                    err='validation failed'
                except Exception as e:
                    err=repr(e); time.sleep(args.sleep_seconds*(attempt+1))
            raw_rec={'run_id':run_id,'call_id':call_id,'timestamp_utc':utc_now(),'provider':args.provider,'model':args.model,'prompt_id':pid,'batch_id':batch_id,'requested_samples':n,'ok':ok,'error':err,'usage':usage,'raw_output':raw}
            append_jsonl(raw_rec, raw_path)
            if not ok:
                append_jsonl(raw_rec, invalid_path); need-=n; continue
            keys=required_keys(rec); rows=[]
            valid_samples=[s for s in samples if validate_sample(s,keys)][:n]
            for j,s in enumerate(valid_samples,1):
                repeat_id=already+j
                row={
                    'run_id':run_id,'call_id':call_id,'batch_id':batch_id,'provider':args.provider,'model':args.model,'temperature':args.temperature,
                    'prompt_id':pid,'repeat_id':repeat_id,'sample_in_call':j,'timestamp_utc':utc_now(),
                    'experiment_type':rec.get('experiment_type'),'condition_id':rec.get('condition_id'),'condition_name':rec.get('condition_name'),
                    'label_cue':rec.get('label_cue'),'score_cue':rec.get('score_cue'),'symptom_cue':rec.get('symptom_cue'),
                    'profile_id':rec.get('profile_id'),'profile_short':rec.get('profile_short'),'ia_like_profile':rec.get('ia_like_profile'),
                    'participant_uid':rec.get('participant_uid'),'feature_condition':rec.get('feature_condition'),
                    'task_id':rec.get('task_id'),'task_name':rec.get('task_name'),
                    'prompt_hash':stable_hash(rec),'input_tokens':usage.get('prompt_tokens') or usage.get('input_tokens'),
                    'output_tokens':usage.get('completion_tokens') or usage.get('output_tokens'),
                }
                for k in keys: row[k]=s[k]
                rows.append(row)
            df=pd.DataFrame(rows)
            header=not sample_csv.exists()
            df.to_csv(sample_csv,mode='a',index=False,header=header,encoding='utf-8-sig')
            already+=len(rows); need-=len(rows); time.sleep(args.sleep_seconds)
    # summary
    if sample_csv.exists():
        df=pd.read_csv(sample_csv)
        cols=[c for c in ['experiment_type','condition_id','profile_id','task_id','feature_condition'] if c in df.columns]
        if cols:
            df.groupby(cols).size().reset_index(name='n').to_csv(out/'completion_summary.csv',index=False)
    print('Done. Outputs in', out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True)
    ap.add_argument('--provider',required=True,choices=['qwen','deepseek','minimax','openai_compatible'])
    ap.add_argument('--model',required=True)
    ap.add_argument('--api-key',default=None)
    ap.add_argument('--base-url',default=None)
    ap.add_argument('--output-dir',required=True)
    ap.add_argument('--target-samples',type=int,default=50)
    ap.add_argument('--samples-per-call',type=int,default=5)
    ap.add_argument('--temperature',type=float,default=0.7)
    ap.add_argument('--max-retries',type=int,default=2)
    ap.add_argument('--sleep-seconds',type=float,default=0.3)
    ap.add_argument('--run-id',default=None)
    ap.add_argument('--resume',action='store_true')
    ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--no-response-format',action='store_true')
    args=ap.parse_args(); run(args)
if __name__=='__main__': main()
