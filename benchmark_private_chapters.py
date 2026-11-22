"""Optional private chapter comparison. Never include input/output text in Git."""
import argparse, json, re, time
from pathlib import Path
from cts_text import TextEngine
from entity_integrity import normalize, protect, restore, count, diagnostics

DEFAULT_NAMES=['Lith','Solus','Selia','Derios','Elina','Raaz','Tista','Rena','Orpal']
def run(public,private,local,aggregate,names):
 data=json.loads((public/'results.json').read_text(encoding='utf-8'))
 prior=json.loads(private.read_text(encoding='utf-8'))
 cases=[r for r in prior['cases'] if r.get('kind')=='private-chapter' and r['source']=='en' and r['target']=='pt']
 assert cases,'No private chapter cases'
 local.mkdir(parents=True,exist_ok=True)
 data['profiles'].update({'P_raw':'Private chapter direct CTS CUDA','P_normalize':'Private chapter punctuation normalization','P_glossary':'Private chapter exact-name markers'})
 e=TextEngine('en','pt',profile='cuda',batch_tokens=1024)
 summary=[]
 for source in cases:
  row=dict(id='private-'+source['id'],source='en',target='pt',kind='private-chapter',text=source['text'],reference=None,
     expected={n:count(source['text'],n) for n in names if count(source['text'],n)},expected_terms={},all_names=names,entities=names)
  data['cases'].append(row);outputs={}
  for mode in ('P_raw','P_normalize','P_glossary'):
   t=time.perf_counter();text=row['text'] if mode=='P_raw' else normalize(row['text']);mapping={}
   if mode=='P_glossary':text,mapping=protect(text,{n:(n,'unknown') for n in names},'en','marker')
   value=e.translate(text);fixed=restore(value,mapping,'en','pt');fallback=fixed is None
   if fallback:fixed=outputs['P_normalize']
   sec=time.perf_counter()-t;outputs[mode]=fixed
   result=dict(case_id=row['id'],profile=mode,status="success" if fixed.strip() else "error",output=fixed,seconds=round(sec,4),char_f2=None,**diagnostics(row,fixed),placeholder_fallback=fallback)
   data['results'].append(result)
   summary.append(dict(case=source['id'],characters=len(row['text']),mode=mode,seconds=result['seconds'],entities_expected=result['entities_expected'],entities_preserved=result['entities_preserved'],numbers_expected=result['numbers_expected'],numbers_preserved=result['numbers_preserved'],layout_ok=result['layout_ok'],fallback=fallback))
   print('private aggregate',summary[-1],flush=True)
 # Never copy a private input or actual translated text into public artifacts.
 (local/'results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 result={'scope':'Three user-owned private EN->PT chapters, exact matches to an explicitly configured partial glossary; original and outputs deliberately withheld. Single warmed run; no human review.', 'cases':summary}
 aggregate.write_text(json.dumps(result,indent=2),encoding='utf-8')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--local',type=Path,required=True);p.add_argument('--aggregate',type=Path,required=True);p.add_argument('--names',nargs='+',default=DEFAULT_NAMES);a=p.parse_args();run(a.public,a.private,a.local,a.aggregate,a.names)
