"""Replay stricter post-edit gates on recorded outputs. No new inference, no reference used for selection."""
from collections import Counter
import argparse, json, re, time
from pathlib import Path
from benchmark300 import numbers
from benchmark_entity_integrity import record, save
from entity_integrity import normalize, count, TranslationMemory

def guard_reasons(row,base,candidate):
 reasons=[]
 if not candidate.strip():return ['empty']
 source=Counter(numbers(row['text']));before=Counter(numbers(base));after=Counter(numbers(candidate))
 if after-source:reasons.append('introduced_numeric_literal')
 if any(min(source[k],after[k])<min(source[k],before[k]) for k in source):reasons.append('lost_numeric_literal')
 if normalize(candidate).count('"')<min(normalize(row['text']).count('"'),normalize(base).count('"')):reasons.append('lost_dialogue_quotes')
 if candidate.count('\n\n')!=base.count('\n\n'):reasons.append('paragraph_structure')
 if re.search(r"\b[A-Za-z]+:\s*[A-Za-z]\b",candidate) and not re.search(r"\b[A-Za-z]+:\s*[A-Za-z]\b",base):reasons.append('broken_word_punctuation')
 for name in row['glossary']:
  target=row['glossary'][name]
  if count(row['text'],name) and count(candidate,target)<min(count(base,target),count(row['text'],name)):
   reasons.append('lost_existing_glossary_term');break
 return reasons

def replay(root):
 data=json.loads((root/'results.json').read_text(encoding='utf-8'))
 cases={r['id']:r for r in data['cases']}
 base={r['case_id']:r for r in data['results'] if r['profile']=='H_guarded'}
 candidates=[r for r in data['results'] if r['profile']=='G_llm_candidate']
 data['profiles']['G2_replay']='Offline stricter gating of the same 12 recorded LLM outputs (no new inference)'
 data['results']=[r for r in data['results'] if r['profile']!='G2_replay']
 for r in candidates:
  row=cases[r['case_id']];orig=base[r['case_id']]
  t=time.perf_counter();reasons=guard_reasons(row,orig['output'],r['output']);elapsed=time.perf_counter()-t
  data['results'].append(record(row,'G2_replay',orig['output'] if reasons else r['output'],round(orig['seconds']+r['seconds']+elapsed,6),accepted=not reasons,guard_reasons=reasons))
 # Exact-hit replay: authored reference is a SIMULATED reviewer-approved fixture,
 # never a quality result or the input to any model/guard.
 mem=TranslationMemory();rows=data['cases'][:30]
 for row in rows:mem.put(row,'fixture-engine','fixture-policy',row['reference'],approved=True)
 t=time.perf_counter()
 hits=sum(mem.get(row,'fixture-engine','fixture-policy')==row['reference'] for row in rows for _ in range(100))
 duration=time.perf_counter()-t
 misses=sum(mem.get(dict(row,context='changed'),'fixture-engine','fixture-policy') is None for row in rows)
 mem_result=dict(approved_fixtures=30,lookups=3000,exact_hits=hits,changed_context_misses=misses,seconds=round(duration,6),scope='in-memory simulated approval; not measured translation quality or persisted user memory')
 (root/'memory_replay.json').write_text(json.dumps(mem_result,indent=2),encoding='utf-8')
 save(root,data)
 print('G2 accepted',sum(r.get('accepted',False) for r in data['results'] if r['profile']=='G2_replay'),'of',len(candidates),flush=True);print(mem_result,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();replay(a.root)
