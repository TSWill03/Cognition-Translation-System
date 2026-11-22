"""Real CUDA ablation, synthetic only. Results are directly consumable by review_server."""
import argparse, collections, gc, hashlib, importlib.metadata, json, platform, statistics, time
from pathlib import Path
from cts_text import TextEngine, translate_document
from entity_corpus import corpus
from entity_integrity import normalize, safe_entries, protect, restore, diagnostics, integrity_score
from benchmark_profiles import char_f2

PROFILES={
 'A_raw':'CTS CUDA1024 baseline',
 'B_normalize':'Normalize punctuation',
 'C_marker':'Normalize + explicit glossary marker',
 'D_semantic':'Normalize + semantic placeholders',
 'E_context':'Previous context cues + semantic placeholders',
 'F_glossary':'Context cues + semantic names + term glossary',
 'H_guarded':'Integrity-ranked candidates B/C/D/E/F; no reference access',
}
def batch_translate(e,texts):
 # Batch entire case paragraphs as independent aligned chunks. No concatenation or pivot.
 groups=[x.split('\n\n') for x in texts]
 flat=[x for g in groups for x in g]
 vals=e.translate_many(flat)
 assert len(flat)==len(vals)
 output=[];offset=0
 for g in groups:
  output.append('\n\n'.join(v.strip() for v in vals[offset:offset+len(g)]))
  offset+=len(g)
 return output

def record(row,profile,out,seconds,**meta):
 return dict(case_id=row['id'],profile=profile,status="success" if out.strip() else "error",output=out,
        seconds=seconds,char_f2=char_f2(out,row['reference']),**diagnostics(row,out),**meta)

def run(out):
 rows=corpus();out.mkdir(parents=True,exist_ok=True)
 data=dict(cases=rows,profiles=PROFILES,results=[],warmups=[],method="Original synthetic corpus, warmed batched inference, single run. Per-case time is amortized batch time; H includes prior candidate costs. No human rating. No private book text.")
 for src,tgt in [('en','pt'),('pt','en')]:
  cases=[r for r in rows if r['source']==src]
  t=time.perf_counter();e=TextEngine(src,tgt,profile='cuda',batch_tokens=1024,beam_size=4)
  identity=dict(e.identity)
  # strip local filesystem model path in public manifest; include actual weights hash
  pkg=e.underlying.pkg
  identity['model']={'package':pkg.package_path.name,'version':str(pkg.package_version),
                    'weights_sha256':hashlib.sha256((pkg.package_path/'model'/'model.bin').read_bytes()).hexdigest()}
  data['warmups'].append(dict(pair=src+'-'+tgt,seconds=round(time.perf_counter()-t,3),identity=identity))
  candidates={};costs={}
  for mode in list(PROFILES)[:-1]:
   start=time.perf_counter();inputs=[];maps=[]
   for row in cases:
    text=row['text'] if mode=='A_raw' else normalize(row['text'])
    if mode in ('C_marker','D_semantic','E_context','F_glossary'):
     entries=safe_entries(row,use_context=mode in ('E_context','F_glossary'),include_terms=mode=='F_glossary')
     text,mapping=protect(text,entries,src,'marker' if mode=='C_marker' else 'semantic')
    else:mapping={}
    inputs.append(text);maps.append(mapping)
   vals=batch_translate(e,inputs)
   temp=[];failed=[]
   for i,(row,value,mapping) in enumerate(zip(cases,vals,maps)):
    restored=restore(value,mapping,src,tgt)
    fallback=restored is None
    # Fail closed. Preserve baseline rather than expose corrupt placeholder.
    if fallback:restored=candidates['B_normalize'][i]['output']
    temp.append((restored,fallback))
   elapsed=time.perf_counter()-start
   costs[mode]=elapsed
   candidates[mode]=[record(r,mode,o,round(elapsed/len(cases),6),placeholder_fallback=f)
                       for r,(o,f) in zip(cases,temp)]
   data['results']+=candidates[mode]
   print(src,mode,len(cases),round(elapsed,3),'fallback',sum(f for _,f in temp),flush=True)
  start=time.perf_counter()
  selected=[]
  for i,row in enumerate(cases):
   entries=safe_entries(row,True,True)
   pool=[candidates[m][i] for m in ('B_normalize','F_glossary','E_context','D_semantic','C_marker')]
   best=min(pool,key=lambda x:integrity_score(row,x['output'],entries))
   selected.append((best,integrity_score(row,best['output'],entries)))
  elapsed=time.perf_counter()-start
  # H is deliberately conservative and expensive: compute all candidate variants.
  hcost=elapsed+sum(costs[m] for m in ('B_normalize','C_marker','D_semantic','E_context','F_glossary'))
  data['results'] += [record(r,'H_guarded',b['output'],round(hcost/len(cases),6),chosen=b['profile'],integrity=list(score)) for r,(b,score) in zip(cases,selected)]
  print(src,'H_guarded',len(cases),round(hcost,3),flush=True)
  save(out,data)
  del e;gc.collect()
 return data

def save(out,data):
 p=out/'results.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)
 summary=[];cases={r['id']:r for r in data['cases']}
 for mode in data['profiles']:
  for direction in ('en','pt'):
   rows=[r for r in data['results'] if r['profile']==mode and cases[r['case_id']]['source']==direction]
   if not rows:continue
   ok=[r for r in rows if r['status']=='success']
   expected=sum(r['entities_expected'] for r in ok);kept=sum(r['entities_preserved'] for r in ok)
   te=sum(r['terms_expected'] for r in ok);tk=sum(r['terms_preserved'] for r in ok)
   ne=sum(r['numbers_expected'] for r in ok);nk=sum(r['numbers_preserved'] for r in ok)
   summary.append(dict(profile=mode,source=direction,n=len(rows),ok=len(ok),entities=f'{kept}/{expected}',entity_pct=round(100*kept/max(1,expected),2),extra=sum(r['entity_extra'] for r in ok),terms=f'{tk}/{te}',numbers=f'{nk}/{ne}',layout_ok=sum(r['layout_ok'] for r in ok),f2=round(statistics.mean(r['char_f2'] for r in ok),2) if ok else None,seconds=round(sum(r['seconds'] for r in rows),3),fallback=sum(r.get('placeholder_fallback',False) for r in rows)))
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 (out/'manifest.json').write_text(json.dumps(dict(cases=len(data['cases']),observed=len(data['results']),success=sum(r['status']=='success' for r in data['results']),method=data['method'],python=platform.python_version(),runtime=importlib.metadata.version('ctranslate2'),warmups=data['warmups'],results_sha256=hashlib.sha256(p.read_bytes()).hexdigest()),indent=2),encoding='utf-8')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.out)
