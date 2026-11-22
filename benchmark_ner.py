"""Actual spaCy NER baseline and protected translation. Models installed explicitly, no downloads."""
import argparse, collections, gc, json, time
from pathlib import Path
import spacy
from entity_integrity import normalize, protect, restore, AMBIGUOUS, count
from benchmark_entity_integrity import batch_translate, record, save
from cts_text import TextEngine

MODE='I_ner'
def run(root,model_dir):
 data=json.loads((root/'results.json').read_text(encoding='utf-8'))
 assert sum(r['profile']=='A_raw' for r in data['results'])==300
 data['profiles'][MODE]='spaCy CPU NER + marker protection (no gold glossary)'
 data['results']=[r for r in data['results'] if r['profile']!=MODE]
 data['warmups']=[r for r in data['warmups'] if r.get('profile')!=MODE]
 for src,name in [('en','en_core_web_sm'),('pt','pt_core_news_sm')]:
  path=model_dir/name/(name+'-3.8.0')
  nlp=spacy.load(path,disable=['parser','tagger','lemmatizer','attribute_ruler','morphologizer'])
  rows=[r for r in data['cases'] if r['source']==src]
  start=time.perf_counter()
  docs=list(nlp.pipe([r['text'] for r in rows],batch_size=32))
  elapsed=time.perf_counter()-start
  e=TextEngine(src,rows[0]['target'],profile='cuda',batch_tokens=1024)
  inputs=[];maps=[];detections=[]
  t=time.perf_counter()
  for r,doc in zip(rows,docs):
   found=collections.Counter(ent.text for ent in doc.ents if ent.label_ in ('PERSON','PER','LOC','GPE','ORG'))
   detections.append(dict(found))
   entries={k:(k,'unknown') for k in found if k.casefold() not in AMBIGUOUS and len(k)>1}
   text,m=protect(normalize(r['text']),entries,src,'marker')
   inputs.append(text);maps.append(m)
  outs=batch_translate(e,inputs)
  base={r['case_id']:r['output'] for r in data['results'] if r['profile']=='B_normalize'}
  results=[]
  for r,o,m,found in zip(rows,outs,maps,detections):
   restored=restore(o,m,src,r['target'])
   expected=collections.Counter(r['expected']);actual=collections.Counter(found)
   results.append((restored if restored is not None else base[r['id']],restored is None,dict(tp=sum((expected&actual).values()),detected=sum(actual.values()),expected=sum(expected.values()),spans=found)))
  total=time.perf_counter()-t+elapsed
  data['warmups'].append(dict(profile=MODE,source=src,model=name,version=nlp.meta['version'],ner_seconds=round(elapsed,3)))
  data['results'] += [record(r,MODE,o,round(total/len(rows),6),placeholder_fallback=f,ner=d) for r,(o,f,d) in zip(rows,results)]
  print(src,MODE,'rows',len(rows),'seconds',round(total,3),'recall',sum(d['tp'] for _,_,d in results),sum(d['expected'] for _,_,d in results),'precision',sum(d['tp'] for _,_,d in results),sum(d['detected'] for _,_,d in results),flush=True)
  save(root,data);del e,nlp,docs;gc.collect()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--models',type=Path,required=True);a=p.parse_args();run(a.root,a.models)
