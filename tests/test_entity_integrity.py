import unittest
from entity_corpus import corpus
from benchmark_span_context import protect_spans, select_spans
from types import SimpleNamespace
from entity_integrity import normalize, protect, restore, infer_context, safe_entries, diagnostics, TranslationMemory

class IntegrityTest(unittest.TestCase):
 def test_corpus(self):
  rows=corpus();self.assertEqual(len(rows),300);self.assertEqual(len({r['id'] for r in rows}),300)
  self.assertEqual(sum(r['source']=='pt' for r in rows),150)
 def test_normalize(self):self.assertEqual(normalize('“A”\n\nB'),'\"A\"\n\nB')
 def test_exact_boundary_and_repeat(self):
  text,m=protect('Lith, Lith and Lithos.',{'Lith':('Lith','male')},'en','marker')
  self.assertEqual(restore(text,m,'en','pt'),'Lith, Lith and Lithos.')
  self.assertIsNone(restore(text.replace(next(iter(m)),'',1),m,'en','pt'))
 def test_collision(self):
  out,m=protect('Gabriel and Lith',{'Lith':('Lith','male')},'en','semantic')
  self.assertNotEqual(next(iter(m)),'Gabriel')
 def test_context(self):
  self.assertEqual(infer_context('The man named Lith is a traveler. The city named Derios is their home.','en'),{'Lith':'male','Derios':'place'})
  r=next(r for r in corpus() if r['group']==5 and r['source']=='en')
  self.assertNotIn('Hope',safe_entries(r,True))
 def test_memory(self):
  m=TranslationMemory();r=corpus()[0]
  with self.assertRaises(ValueError):m.put(r,'engine','policy','x')
  m.put(r,'engine','policy','ok',approved=True)
  self.assertEqual(m.get(r,'engine','policy'),'ok')
  self.assertIsNone(m.get(dict(r,context='changed'),'engine','policy'))
 def test_reference_contract(self):
  for r in corpus():
   d=diagnostics(r,r['reference'])
   self.assertEqual(d['entities_expected'],d['entities_preserved'],r['id'])
   self.assertEqual(d['terms_expected'],d['terms_preserved'],r['id'])

 def test_span_disambiguation(self):
  text="Hope is not lost. Hope entered."
  doc=[SimpleNamespace(idx=0,text="Hope",pos_="NOUN"),SimpleNamespace(idx=18,text="Hope",pos_="PROPN")]
  spans=select_spans(text,doc,{"Hope":"male"},{})
  self.assertEqual(spans,[(18,22,"Hope","male")])
  value,mapping=protect_spans(text,spans,"en")
  self.assertTrue(value.startswith("Hope is not lost. "))
  self.assertEqual(restore(value,mapping,"en","pt"),text)
 def test_strict_numbers(self):
  text="There are 3 bottles, not 30."
  spans=select_spans(text,[],{}, {},True)
  self.assertEqual([s[2] for s in spans],["3","30"])
  value,mapping=protect_spans(text,spans,"en")
  self.assertEqual(restore(value,mapping,"en","pt"),text)
 def test_overlap_rejected(self):
  with self.assertRaises(ValueError):protect_spans("abc",[(0,2,"ab","term"),(1,3,"bc","term")],"en")

 def test_guard_value_and_quotes(self):
  from benchmark_guard_replay import guard_reasons
  r=dict(text='May gave 3 bottles, not 30.',glossary={})
  self.assertIn('lost_numeric_literal',guard_reasons(r,'three bottles, not 30','three bottles, not 3:00'))
