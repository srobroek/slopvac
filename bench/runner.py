#!/usr/bin/env python3
"""Fixed online structured-prose benchmark; all configuration is repository data."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, tempfile, time
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parent
RUBRIC=ROOT/'rubric.json'; TEMPLATE=ROOT/'prompt_template.txt'; SHOTS=ROOT/'shots.json'; CASES=ROOT/'cases.json'; ARMS=ROOT/'arms.json'
ALLOWED={'confirm','preserve','reject','abstain'}
FORBIDDEN={'label','role','category','family','genre','holdout'}
AUTH=re.compile(r'\b(?:AI|artificial intelligence|model-generated|machine-generated|human-written|authorship|written by a (?:person|human|model))\b',re.I)
def metric(name:str,value:Any)->None: print(f'METRIC {name}={value:.6f}' if isinstance(value,float) else f'METRIC {name}={value}')
def load(path:Path)->dict[str,Any]:
 with path.open(encoding='utf-8') as f: value=json.load(f)
 if not isinstance(value,dict): raise ValueError(f'{path.name}: expected object')
 return value
def validate_assets():
 manifest=load(ROOT/'manifest.json')
 for name,expected in manifest.get('sha256',{}).items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected: raise ValueError(f'asset changed: {name}')
 rubric,sd,cd,ad=load(RUBRIC),load(SHOTS),load(CASES),load(ARMS); shots,cases,arms=sd.get('shots'),cd.get('cases'),ad.get('arms')
 if set(rubric.get('verdicts',[]))!=ALLOWED or not all(isinstance(x,list) for x in (shots,cases,arms)): raise ValueError('assets are malformed')
 if len({x.get('id') for x in cases})!=len(cases) or any(not isinstance(x.get('text'),str) for x in cases): raise ValueError('case IDs/text must be present and unique')
 families={}
 for c in cases: families.setdefault(str(c.get('family')),[]).append(c)
 if any(sum(bool(x.get('holdout')) for x in g)!=1 for g in families.values()): raise ValueError('each near-neighbour family must have exactly one holdout')
 for s in shots:
  if s.get('verdict') not in ALLOWED or not isinstance(s.get('quote'),str) or s['quote'] not in s.get('text','') or AUTH.search(json.dumps(s)): raise ValueError(f'invalid shot: {s.get("id")}')
 if not arms or any(not x.get('id') or not x.get('model') for x in arms): raise ValueError('model arm manifest is malformed')
 return rubric,shots,cases,ad
def project_cases(cases):
 projected=[{'id':str(c['id']),'text':str(c['text'])} for c in cases]
 if any(set(c)!={'id','text'} for c in projected): raise AssertionError('model projection contains private metadata')
 return projected
def render(rubric,shots,cases):
 p=TEMPLATE.read_text(encoding='utf-8').replace('{{RUBRIC_JSON}}',json.dumps(rubric,sort_keys=True,separators=(',',':'))).replace('{{SHOTS_JSON}}',json.dumps(shots,sort_keys=True,separators=(',',':'))).replace('{{CASES_JSON}}',json.dumps(project_cases(cases),sort_keys=True,separators=(',',':')))
 if '{{' in p or '}}' in p: raise ValueError('prompt template has unresolved placeholders')
 payload=json.dumps(project_cases(cases),sort_keys=True)
 if any(re.search(rf'"{k}"\s*:',payload) for k in FORBIDDEN) or re.search(r'"(?:defect|control)"',payload): raise AssertionError('forbidden metadata or answer mapping leaked into eval payload')
 return p
def find_results(v):
 if isinstance(v,dict) and isinstance(v.get('results'),list):return v['results'],v
 return None,None
def _assistant_key(m):
 for key in ('message_id','event_id','item_id','id'):
  value=m.get(key)
  if isinstance(value,(str,int,float)) and not isinstance(value,bool):return key,value
 return None
def _ams(v):
 out=[]; seen_objects=set(); seen_keys=set()
 def visit(value):
  if isinstance(value,dict):
   message=value.get('message')
   if isinstance(message,dict) and message.get('role')=='assistant':add(message)
   if value.get('role')=='assistant':add(value)
   for child in value.values():visit(child)
  elif isinstance(value,list):
   for child in value:visit(child)
 def add(message):
  key=_assistant_key(message)
  if id(message) in seen_objects or (key is not None and key in seen_keys):return
  seen_objects.add(id(message))
  if key is not None:seen_keys.add(key)
  out.append(message)
 visit(v)
 return out
def usage(v):
 total={}
 for m in _ams(v):
  u=m.get('usage');
  if not isinstance(u,dict):continue
  for k in ('input_tokens','output_tokens','total_tokens'):
   if isinstance(u.get(k),int) and not isinstance(u[k],bool):total[k]=total.get(k,0)+u[k]
  c=u.get('cost')
  if isinstance(c,dict) and isinstance(c.get('total'),(int,float)) and not isinstance(c['total'],bool):total['cost']=float(total.get('cost',0))+float(c['total'])
 return total
def _text(m):
 c=m.get('content','')
 if isinstance(c,str):return c
 if isinstance(c,list):return ''.join(x['text'] for x in c if isinstance(x,dict) and isinstance(x.get('text'),str))
 return ''
def assistant_payloads(v):
 ms=_ams(v)
 if not ms:return []
 text=re.sub(r'```(?:json)?\s*','',_text(ms[-1]),flags=re.I).replace('```',''); d=json.JSONDecoder(); found=[]; pos=0
 while True:
  match=re.search(r'[\[{]',text[pos:])
  if match is None:break
  start=pos+match.start()
  try:x,end=d.raw_decode(text[start:])
  except json.JSONDecodeError:pos=start+1;continue
  pos=start+end
  if isinstance(x,dict) and isinstance(x.get('results'),list):found.append(x)
 return found[-1:] if found else []
def _validate_rows(cases,rows):
 expected=[str(c.get('id')) for c in cases]
 if not isinstance(rows,list):return 'results is not a list'
 if len(rows)!=len(expected):return f'expected {len(expected)} results, got {len(rows)}'
 actual=[]
 for row in rows:
  if not isinstance(row,dict):return 'result row is not object'
  case_id=row.get('case_id')
  if not isinstance(case_id,str):return 'result row missing case_id'
  actual.append(case_id)
 if actual!=expected:return 'result case_ids are not in expected order'
 return None
def invoke(model,prompt,timeout=300,cases=None):
 if shutil.which('omp') is None:return None,{},'provider_error: omp not found'
 with tempfile.TemporaryDirectory(prefix='slopvac-online-') as run_dir:
  cmd=['omp','-p','slopvac-online-','--mode','json','--model',model,'--thinking','low','--max-time',str(timeout),'--no-extensions','--no-skills','--no-tools','--no-slop','--no-memory']; start=time.monotonic()
  try:proc=subprocess.run(cmd,input=prompt,text=True,capture_output=True,timeout=timeout,check=False,env={**os.environ,'OMP_RUN_DIR':run_dir})
  except subprocess.TimeoutExpired:return None,{'latency_ms':(time.monotonic()-start)*1000},'provider_error: timeout'
  events=[]
  for line in proc.stdout.splitlines():
   try:events.append(json.loads(line))
   except json.JSONDecodeError:pass
  stats={'latency_ms':(time.monotonic()-start)*1000};stats.update(usage(events)); payloads=assistant_payloads(events)
  if proc.returncode!=0:return None,stats,f'provider_error: omp exit {proc.returncode}'
  if not payloads:return None,stats,'undecodable: no assistant JSON'
  rows,_=find_results(payloads[-1])
  if not isinstance(rows,list):return None,stats,'schema_invalid: missing results'
  if cases is not None:
   problem=_validate_rows(cases,rows)
   if problem:return None,stats,f'schema_invalid: {problem}'
  elif any(not isinstance(x,dict) for x in rows):return None,stats,'schema_invalid: result row is not object'
  return rows,stats,''
def score(cases,results):
 problem=_validate_rows(cases,results)
 if problem:return {'failures':0,'false_positives':0,'false_confirms':0,'misses':0,'correct':0,'abstains':0,'missing':len(cases),'schema_invalid':problem,'quality_score':0.0}
 by={x.get('case_id'):x for x in (results or []) if isinstance(x,dict)}; out={'failures':0,'false_positives':0,'false_confirms':0,'misses':0,'correct':0,'abstains':0,'missing':0}
 for c in cases:
  r=by.get(c.get('id'))
  if r is None:out['missing']+=1;continue
  if r.get('verdict') not in ALLOWED or not isinstance(r.get('quote'),str) or not r['quote'] or r['quote'] not in c.get('text','') or AUTH.search(json.dumps(r)):out['failures']+=1;continue
  expected='reject' if c.get('label')=='defect' else 'preserve'
  if r['verdict']=='abstain':out['abstains']+=1
  if r['verdict']==expected:out['correct']+=1
  elif c.get('label')=='control' and r['verdict']=='reject':out['false_positives']+=1
  elif c.get('label')=='defect' and r['verdict']=='preserve':out['false_confirms']+=1
  else:out['misses']+=1
 n=max(1,len(cases)); penalty=100*(3*out['failures']+4*out['false_positives']+5*out['false_confirms']+4*out['misses']+4*out['missing'])/n;out['quality_score']=max(0.,100.-penalty);return out
def main(argv=None):
 ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');a=ap.parse_args(argv)
 try:r,s,c,ad=validate_assets(); ec=[x for x in c if not x.get('holdout')]; arms=ad['arms'][:1] if a.smoke else ad['arms'];ec=ec[:1] if a.smoke else ec;p=render(r,s,ec)
 except (OSError,ValueError,AssertionError,json.JSONDecodeError) as e:print(f'autoresearch: asset validation failure: {e}',file=os.sys.stderr);return 2
 metric('case-count',len(ec));metric('holdout-count',sum(bool(x.get('holdout')) for x in c));metric('prompt-sha256',hashlib.sha256(p.encode()).hexdigest())
 for arm in arms:
  scores=[]
  for i in range(1 if a.smoke else int(ad.get('fixed',{}).get('repeats',2))):
   rows,stats,error=invoke(str(arm['model']),p,cases=ec);metric(f"arm-{arm['id']}-repeat-{i+1}-outcome",'ok' if not error else error.split(':',1)[0]);
   for k,v in stats.items():metric(f"arm-{arm['id']}-repeat-{i+1}-{k}",v)
   if error:print(f"METRIC arm-{arm['id']}-error={json.dumps(error)}");continue
   sc=score(ec,rows);scores.append(float(sc['quality_score']));metric(f"arm-{arm['id']}-repeat-{i+1}-quality_score",sc['quality_score'])
  metric(f"arm-{arm['id']}-quality_score",min(scores) if scores else 'unmeasured')
 return 0
if __name__=='__main__':raise SystemExit(main())
