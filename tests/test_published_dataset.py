"""Regression checks for the *published* 300-case evidence (no remote models needed)."""
import csv,json,sys,unittest
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import benchmark300 as bench
class PublishedDatasetTests(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    with (ROOT/"results/translations.csv").open(newline="",encoding="utf-8-sig") as f: cls.rows=list(csv.DictReader(f))
    cls.manifest=json.loads((ROOT/"results/manifest.json").read_text(encoding="utf-8"))
    cls.summary=json.loads((ROOT/"results/summary.json").read_text(encoding="utf-8"))
  def test_300_rows(self):self.assertEqual(len(self.rows),300)
  def test_300_distinct_ids(self):self.assertEqual(len({r["id"] for r in self.rows}),300)
  def test_300_successful_outputs(self):
    self.assertEqual(sum(r["status"]=="success" and bool(r["output_text"].strip()) for r in self.rows),300)
  def test_languages_are_exact(self):self.assertEqual(set(r["tgt_lang"] for r in self.rows),set(bench.TARGETS))
  def test_20_per_language(self):self.assertEqual(set(Counter(r["tgt_lang"] for r in self.rows).values()),{20})
  def test_source_data_matches_corpus(self):
    source={p["id"]:p["text"] for p in bench.load_prompts()}
    self.assertTrue(all(r["source_text"]==source[r["sentence_id"]] for r in self.rows))
  def test_job_matrix_matches(self):
    expected={j["id"] for j in bench.schedule(bench.load_prompts())}
    self.assertEqual({r["id"] for r in self.rows},expected)
  def test_manifest_counts(self):
    self.assertEqual((self.manifest["planned"],self.manifest["observed"],self.manifest["success"],self.manifest["error"]),(300,300,300,0))
  def test_numeric_heuristic_v2_consistent(self):
    self.assertTrue(all(
      str(bench.check_numbers(r["source_text"],r["output_text"])[0])==r["numbers_expected"]
      and (str(bench.check_numbers(r["source_text"],r["output_text"])[1]) if int(r["numbers_expected"]) else "")==r["numbers_preserved"]
      for r in self.rows))
  def test_model_installation_inventory(self):
    entries=json.loads((ROOT/"model_installation.json").read_text(encoding="utf-8"))
    self.assertEqual(set(e["language"] for e in entries),set(bench.TARGETS))
  def test_research_is_explicitly_text_only(self):self.assertIs(self.manifest["text_only"],True)
