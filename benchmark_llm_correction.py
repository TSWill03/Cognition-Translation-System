"""Selective local LLM correction pilot; synthetic cases only, no external API."""
import argparse, json, time, hashlib, urllib.request
from pathlib import Path
from benchmark_entity_integrity import record, save
from entity_integrity import safe_entries, integrity_score, count

BASE='http://127.0.0.1:11434'
MODEL='qwen3:4b'
def call(path,payload=None,timeout=90):
 data=json.dumps(payload).encode() if payload is not None else None
 req=urllib.request.Request(BASE+path,data=data,headers={'Content-Type':'application/json'})
 # Do not use system proxies for local data.
 return json.load(urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=timeout))
def run(root,limit=12):
 data=json.loads((root/'results.json').read_text(encoding='utf-8'))
 rows={r['case_id']:r for r in data['results'] if r['profile']=='H_guarded'}
 assert len(rows)==300,"Need complete base experiment"
 tags=call('/api/tags')
 model=next((m for m in tags['models'] if m['name']==MODEL),None)
 if not model:raise RuntimeError("Local model not installed")
 picked=[]
 for src in ('en','pt'):
  # Exact regression plus diverse domains with missing protected terms, ambiguity or numeric alarms.
  candidates=[r for r in data['cases'] if r['source']==src and r['id'] in rows]
  chosen=[r for r in candidates if r['group']==0 and r['domain']=='dialogue']
  seen={'dialogue'}
  def rank(r):
   out=rows[r['id']]['output']
   entries=safe_entries(r,True,True)
   score=integrity_score(r,out,entries)
   ambiguous=any(k not in entries and count(r['text'],k) for k in r['all_names'])
   return (sum(score),int(ambiguous),r['split']=='name-holdout')
  for r in sorted(candidates,key=rank,reverse=True):
   if r['domain'] not in seen:
    chosen.append(r);seen.add(r['domain'])
   if len(chosen)>=limit//2:break
  picked+=chosen
 data['profiles']['G_llm_candidate']='Local Qwen3:4b contextual post-editor (selected subset)'
 data['profiles']['G_llm_guarded']='Post-editor candidate accepted only if configured integrity checks do not worsen (selected subset)'
 # Remove earlier runs of same modes from a public result set before reproducible rerun.
 data['results']=[r for r in data['results'] if r['profile'] not in ('G_llm_candidate','G_llm_guarded')]
 data['warmups']=[r for r in data['warmups'] if r.get('profile')!='G_llm_candidate']
 data['warmups'].append(dict(profile='G_llm_candidate',model=MODEL,digest=model['digest'],pilot_cases=[r['id'] for r in picked],
     endpoint='local loopback',options={'temperature':0,'num_ctx':2048,'num_predict':256,'think':False}))
 try:
  for r in picked:
   original=rows[r['id']]['output']
   language='Brazilian Portuguese' if r['target']=='pt' else 'English'
   # Only source, prior context, dictionary and candidate; reference never passed.
   prompt=("You are a literary translator and copyeditor. Return ONLY JSON with key translation. "
        f"Correct the draft into natural {language}, preserving meaning, negation, numbers, paragraphs, names, speaker identity and action order. "
        "Use the previous context to disambiguate names from ordinary words. Do not add explanations or new facts. "
        "Use glossary for intended meanings, not when a word is ordinary grammar.\n"
        +json.dumps({'source':r['text'],'previous_context':r['context'],'glossary':r['glossary'],'draft':original},ensure_ascii=False))
   t=time.perf_counter();err=None
   try:
    response=call('/api/chat',{'model':MODEL,'messages':[{'role':'user','content':prompt}],
       'stream':False,'think':False,'keep_alive':'2m',
       'format':{'type':'object','properties':{'translation':{'type':'string'}},'required':['translation']},
       'options':{'temperature':0,'seed':42,'num_ctx':2048,'num_predict':256}})
    output=json.loads(response['message']['content'])['translation']
    if not isinstance(output,str) or not output.strip():raise ValueError('empty')
   except Exception as ex:output='';err=type(ex).__name__
   elapsed=time.perf_counter()-t
   entries=safe_entries(r,True,True)
   accept=bool(output) and integrity_score(r,output,entries)<=integrity_score(r,original,entries)
   data['results'].append(record(r,'G_llm_candidate',output,round(elapsed,4),error=err))
   data['results'].append(record(r,'G_llm_guarded',output if accept else original,round(elapsed+rows[r['id']]['seconds'],4),accepted=accept))
   save(root,data)
   print(r['id'],'seconds',round(elapsed,3),'accepted',accept,'error',err,flush=True)
 finally:
  try:call('/api/generate',{'model':MODEL,'keep_alive':0})
  except Exception:pass
 print('LLM pilot complete; human quality not approved',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--limit',type=int,default=12);a=p.parse_args();run(a.root,a.limit)
