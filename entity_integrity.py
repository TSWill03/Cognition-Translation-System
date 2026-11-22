"""Experimental integrity layer. Candidate checks are diagnostics, not semantic guarantees."""
from __future__ import annotations
import re
from collections import Counter
from benchmark300 import numbers

NORMALIZE=str.maketrans({"“":'"',"”":'"',"‘":"'","’":"'","\u00a0":" ","\u202f":" "})
# These common nouns/modal words are ambiguous even if title-cased.
AMBIGUOUS={"hope","rose","may","will","grace","ash","silver","dawn","reed","iris","aster","riven"}
SURROGATES={"en":{"male":"Gabriel","female":"Clara","place":"Lisbon","unknown":"Alex"},
            "pt":{"male":"Gabriel","female":"Clara","place":"Lisboa","unknown":"Alex"}}

def normalize(text):
 return text.translate(NORMALIZE)

def count(text,term,ignore_case=False):
 return len(re.findall(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text, re.I if ignore_case else 0))

def infer_context(context,src):
 """Controlled cues in previous context, not a trained NER model."""
 pattern=(r'(man|woman|city) named ([A-Z][\w-]*(?: [A-Z][\w-]*)*) is\b' if src=='en'
          else r'(homem chamado|mulher chamada|cidade chamada) ([A-Z][\w-]*(?: [A-Z][\w-]*)*) é\b')
 roles={'man':'male','woman':'female','city':'place','homem chamado':'male','mulher chamada':'female','cidade chamada':'place'}
 return {name:roles[role] for role,name in re.findall(pattern,context)}

def safe_entries(row, use_context=False, include_terms=False):
 # Do not silently treat common words as names. Require manual decision for ambiguous aliases.
 roles=infer_context(row['context'],row['source']) if use_context else row['roles']
 entries={k:(k,v) for k,v in roles.items() if k.casefold() not in AMBIGUOUS}
 if include_terms:
  entries.update({k:(v,'term') for k,v in row['glossary'].items() if k!=v})
 return entries

def protect(text, entries, src, style):
 """Return transformed text, restoration map and expected placeholder counts.

 Never replace a partial word. Never use an alias already present in the source.
 Semantic surrogates are allowed ONLY for explicitly supplied roles.
 Terms use markers; the exact desired translation is restored.
 """
 if not entries:return text,{}
 mapping={}
 patterns=sorted(entries,key=len,reverse=True)
 pattern=re.compile(r'(?<!\w)(?:'+'|'.join(map(re.escape,patterns))+r')(?!\w)')
 selected={}
 def sub(m):
  key=m.group(0)
  if key not in selected:
   target,role=entries[key]
   if style=='semantic' and role in SURROGATES[src]:
    token=SURROGATES[src][role]
    if count(text,token,True) or token in mapping:token=None
   else:token=None
   if not token:
    n=len(mapping)+1
    token=f'ZXQ{7400+n}QXZ'
    while token in text or token in mapping:
     n+=1;token=f'ZXQ{7400+n}QXZ'
   selected[key]=token
   mapping[token]=[target,0,role]
  token=selected[key];mapping[token][1]+=1
  return token
 return pattern.sub(sub,text),mapping

def restore(text,mapping,src,target):
 # A city surrogate may be translated into its other-language form.
 # Permit only known exact alternatives, and demand exact counts.
 for token,(value,n,role) in mapping.items():
  aliases=[token]
  if role=='place' and token in ('Lisbon','Lisboa'):
   aliases=['Lisbon','Lisboa']
  pat=re.compile(r'(?<!\w)(?:'+'|'.join(map(re.escape,aliases))+r')(?!\w)')
  if len(pat.findall(text))!=n:return None
  text=pat.sub(lambda _:value,text)
 return text if not re.search(r'ZXQ\d+QXZ',text) else None

def diagnostics(row,out):
 expected=row['expected']
 missing=sum(max(0,n-count(out,k)) for k,n in expected.items())
 extra=sum(max(0,count(out,k)-expected.get(k,0)) for k in row['all_names'])
 terms=sum(max(0,n-count(out,k,True)) for k,n in row['expected_terms'].items())
 n=Counter(numbers(row['text']));m=Counter(numbers(out))
 return dict(entities_expected=sum(expected.values()),entities_preserved=sum(expected.values())-missing,
             entity_extra=extra,terms_expected=sum(row['expected_terms'].values()),
             terms_preserved=sum(row['expected_terms'].values())-terms,
             numbers_expected=sum(n.values()),numbers_preserved=sum((n&m).values()),
             layout_ok=out.count('\n\n')==row['text'].count('\n\n'),
             marker_leak=bool(re.search(r'ZXQ\d+QXZ',out)))

def integrity_score(row,out,entries):
 # Used for selection, NOT the benchmark's expected labels or references.
 # Only unambiguous source matches from the configured glossary.
 expected=sum(max(0,count(row['text'],k)-count(out,v,role=='term')) for k,(v,role) in entries.items())
 numeric=sum((Counter(numbers(row['text']))-Counter(numbers(out))).values())
 layout=int(out.count('\n\n')!=row['text'].count('\n\n'))
 return (int(not out.strip() or bool(re.search(r'ZXQ\d+QXZ',out))),expected,numeric,layout)

class TranslationMemory:
 """Exact match only, including context, direction, engine and policy version."""
 def __init__(self):self._data={}
 def key(self, row, engine_id, policy):
  return (row['source'],row['target'],row['text'],row['context'],engine_id,policy)
 def put(self,row,engine_id,policy,text,*,approved=False):
  if not approved: raise ValueError("Unapproved translation memory entry")
  self._data[self.key(row,engine_id,policy)]=text
 def get(self,row,engine_id,policy):
  return self._data.get(self.key(row,engine_id,policy))
