"""Context glossary + span-specific POS/NER disambiguation; optional strict numeric formatting."""
import argparse, gc, json, re, time
from pathlib import Path
from entity_integrity import normalize, restore, infer_context, AMBIGUOUS, SURROGATES, count, integrity_score
from benchmark_entity_integrity import batch_translate, record, save
from cts_text import TextEngine

MODE='J_span_context'
NUMERIC=re.compile(r'(?<!\w)\d+(?:[.,]\d+)?(?!\w)')

def protect_spans(text, spans, src):
 """Replace only selected occurrences; repeat names get one reversible surrogate."""
 mapping={};tokens={};parts=[];end=0
 for start,stop,value,role in sorted(spans):
  if start<end or start<0 or stop>len(text) or stop<=start:raise ValueError('overlapping or invalid spans')
  key=(value,role)
  if key not in tokens:
   token=SURROGATES[src].get(role)
   if not token or count(text,token,True) or token in mapping:
    n=len(mapping)+1;token=f'ZXQ{8500+n}QXZ'
    while token in text or token in mapping:
     n+=1;token=f'ZXQ{8500+n}QXZ'
   tokens[key]=token;mapping[token]=[value,0,role]
  token=tokens[key];mapping[token][1]+=1
  parts.extend((text[end:start],token));end=stop
 parts.append(text[end:])
 return ''.join(parts),mapping

def select_spans(text,doc,roles,term_map,strict_numbers=False):
 spans=[]
 for name,role in roles.items():
  for m in re.finditer(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text):
   if name.casefold() in AMBIGUOUS:
    # Require source-local evidence, rather than replacing all mentions of a common word.
    tokens=[t for t in doc if t.idx>=m.start() and t.idx+len(t.text)<=m.end()]
    if not tokens or not all(t.pos_=='PROPN' for t in tokens):continue
   spans.append((m.start(),m.end(),name,role))
 for source,target in term_map.items():
  if source==target:continue
  for m in re.finditer(r'(?<!\w)'+re.escape(source)+r'(?!\w)',text,re.I):
   if not any(m.start()<b and m.end()>a for a,b,*_ in spans):
    spans.append((m.start(),m.end(),target,'term'))
 if strict_numbers:
  for m in NUMERIC.finditer(text):
   if not any(m.start()<b and m.end()>a for a,b,*_ in spans):
    val=m.group(0)
    # locale decimal separator only, not ambiguous thousands.
    spans.append((m.start(),m.end(),val,'number'))
 return spans

def run(root,models):
 import spacy
 data=json.loads((root/'results.json').read_text(encoding='utf-8'))
 data['profiles'][MODE]='Context-derived glossary + POS span disambiguation + semantic / term placeholders'
 data['profiles']['K_strict_digits']='J plus explicit digit preservation (opt-in formatting policy)'
 data['results']=[r for r in data['results'] if r['profile'] not in (MODE,'K_strict_digits')]
 for src,name in [('en','en_core_web_sm'),('pt','pt_core_news_sm')]:
  nlp=spacy.load(models/name/(name+'-3.8.0'))
  cases=[r for r in data['cases'] if r['source']==src];t=time.perf_counter()
  texts=[normalize(r['text']) for r in cases];docs=list(nlp.pipe(texts,batch_size=32));pre=time.perf_counter()-t
  e=TextEngine(src,cases[0]['target'],profile='cuda',batch_tokens=1024)
  for mode in (MODE,'K_strict_digits'):
   t=time.perf_counter();inputs=[];maps=[]
   for row,text,doc in zip(cases,texts,docs):
    roles=infer_context(row['context'],src)
    spans=select_spans(text,doc,roles,row['glossary'],mode=='K_strict_digits')
    val,mapping=protect_spans(text,spans,src);inputs.append(val);maps.append(mapping)
   outs=batch_translate(e,inputs)
   base={r['case_id']:r['output'] for r in data['results'] if r['profile']=='B_normalize'}
   vals=[]
   for row,o,m in zip(cases,outs,maps):
    restored=restore(o,m,src,row['target']);fallback=restored is None
    vals.append((restored if restored is not None else base[row['id']],fallback))
   elapsed=time.perf_counter()-t+pre
   data['results'] += [record(r,mode,o,round(elapsed/len(cases),6),placeholder_fallback=f) for r,(o,f) in zip(cases,vals)]
   print(src,mode,'rows',len(cases),'sec',round(elapsed,3),'fallback',sum(f for _,f in vals),flush=True)
  save(root,data);del e,nlp,docs;gc.collect()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--models',type=Path,required=True);a=p.parse_args();run(a.root,a.models)
