"""Two-process span experiment: isolate spaCy preprocessing from CUDA initialization."""
import argparse, json, time, gc
from pathlib import Path
from entity_integrity import normalize, restore, infer_context
from benchmark_span_context import protect_spans,select_spans
from benchmark_entity_integrity import record,save,batch_translate
from cts_text import TextEngine

def prepare(root, models, out):
 import spacy
 data=json.loads((root/'results.json').read_text(encoding='utf-8'))
 bundle={}
 for src,name in [('en','en_core_web_sm'),('pt','pt_core_news_sm')]:
  nlp=spacy.load(models/name/(name+'-3.8.0'))
  cases=[r for r in data['cases'] if r['source']==src]
  t=time.perf_counter();texts=[normalize(r['text']) for r in cases]
  docs=list(nlp.pipe(texts,batch_size=32));pre=time.perf_counter()-t
  print(src,'POS preprocessing',round(pre,3),flush=True)
  for mode in ('J_span_context','K_strict_digits'):
   t=time.perf_counter()
   inputs=[]
   for row,text,doc in zip(cases,texts,docs):
    spans=select_spans(text,doc,infer_context(row['context'],src),row['glossary'],mode=='K_strict_digits')
    val,mapping=protect_spans(text,spans,src)
    inputs.append(dict(id=row['id'],input=val,mapping=mapping))
   bundle[src+'|'+mode]=dict(pre_seconds=pre+time.perf_counter()-t,inputs=inputs)
  del nlp,docs;gc.collect()
 out.write_text(json.dumps(bundle,ensure_ascii=False),encoding='utf-8')

def evaluate(root,prepared):
 data=json.loads((root/'results.json').read_text(encoding='utf-8'));bundle=json.loads(prepared.read_text(encoding='utf-8'))
 cases={r['id']:r for r in data['cases']}
 modes={'J_span_context':'Context-derived glossary + POS span disambiguation + semantic/term placeholders',
        'K_strict_digits':'J and strict digit-format policy'}
 data['profiles'].update(modes)
 data['results']=[r for r in data['results'] if r['profile'] not in modes]
 base={r['case_id']:r['output'] for r in data['results'] if r['profile']=='B_normalize'}
 for src,tgt in [('en','pt'),('pt','en')]:
  e=TextEngine(src,tgt,profile='cuda',batch_tokens=1024)
  for mode in modes:
   b=bundle[src+'|'+mode];rows=b['inputs'];t=time.perf_counter()
   outs=batch_translate(e,[r['input'] for r in rows]);values=[]
   for r,o in zip(rows,outs):
    value=restore(o,r['mapping'],src,tgt)
    values.append((value if value is not None else base[r['id']],value is None))
   sec=b['pre_seconds']+time.perf_counter()-t
   data['results'] += [record(cases[r['id']],mode,v,round(sec/len(rows),6),placeholder_fallback=f) for r,(v,f) in zip(rows,values)]
   print(src,mode,len(rows),round(sec,3),'fallback',sum(f for _,f in values),flush=True)
  save(root,data);del e;gc.collect()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','evaluate']);p.add_argument('--root',type=Path,required=True);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--models',type=Path);a=p.parse_args()
 if a.stage=='prepare':prepare(a.root,a.models,a.prepared)
 else:evaluate(a.root,a.prepared)
