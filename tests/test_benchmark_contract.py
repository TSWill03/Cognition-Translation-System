"""Contract and regression checks. Unit tests never count toward 300 measured translations."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import benchmark300 as bench
class CorpusTests(unittest.TestCase):
    def test_exact_20_prompts(self): self.assertEqual(len(bench.load_prompts()),20)
    def test_original_source_nonempty(self): self.assertTrue(all(x["text"] for x in bench.load_prompts()))
    def test_ids_unique(self): self.assertEqual(len({p["id"] for p in bench.load_prompts()}),20)
    def test_targets_exact_15(self): self.assertEqual(len(bench.TARGETS),15)
    def test_language_names_complete(self): self.assertEqual(set(bench.TARGETS),set(bench.NAMES))
    def test_expected_300(self): self.assertEqual(len(bench.schedule(bench.load_prompts())),300)
    def test_job_ids_unique(self):
        jobs=bench.schedule(bench.load_prompts())
        self.assertEqual(len(jobs),len({j["id"] for j in jobs}))
    def test_all_20_each_language(self):
        jobs=bench.schedule(bench.load_prompts())
        self.assertTrue(all(sum(x["language"]==code for x in jobs)==20 for code in bench.TARGETS))
    def test_domains_present(self): self.assertGreaterEqual(len({p["domain"] for p in bench.load_prompts()}),10)
    def test_low_resource_candidates(self): self.assertGreaterEqual(len(bench.CANDIDATE_LOWER_RESOURCE),7)
    def test_source_corpus_unique_text(self):
        prompts=bench.load_prompts()
        self.assertEqual(len(prompts),len({p["text"] for p in prompts}))
    def test_no_whitespace_only(self): self.assertTrue(all(p["text"].strip() for p in bench.load_prompts()))
    def test_no_empty_targets(self): self.assertTrue(all(bench.NAMES.values()))
    def test_missing_prompt_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"bad.json"
            path.write_text(json.dumps([{"id":"one","text":"Hi"}]),encoding="utf-8")
            with self.assertRaises(ValueError):bench.load_prompts(path)
    def test_empty_prompt_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"bad.json"
            sample=bench.load_prompts();sample[-1]["text"]=" "
            path.write_text(json.dumps(sample),encoding="utf-8")
            with self.assertRaises(ValueError):bench.load_prompts(path)
    def test_duplicate_prompt_raises(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"bad.json"
            sample=bench.load_prompts();sample[-1]["id"]=sample[0]["id"]
            path.write_text(json.dumps(sample),encoding="utf-8")
            with self.assertRaises(ValueError):bench.load_prompts(path)
class NumericDiagnosticTests(unittest.TestCase):
    def test_integer(self): self.assertEqual(bench.numbers("Test with 84 samples"),["84"])
    def test_decimal(self): self.assertEqual(bench.numbers("72.5 percent"),["72.5"])
    def test_locale_decimal(self): self.assertEqual(bench.numbers("72,5%"),["72.5"])
    def test_positive_preservation(self): self.assertEqual(bench.check_numbers("84 samples","84 amostras"),(1,1))
    def test_negative_preservation(self): self.assertEqual(bench.check_numbers("84 samples","83 amostras"),(1,0))
    def test_multiple_digits(self): self.assertEqual(bench.check_numbers("15 kWh for 24 hours","15 kWh por 24 horas"),(2,1))
    def test_missing_second(self): self.assertEqual(bench.check_numbers("15 kWh for 24 hours","15 kWh"),(2,0))
    def test_repeated(self): self.assertEqual(bench.check_numbers("84 and 84","84"),(2,0))
    def test_no_numbers(self): self.assertEqual(bench.check_numbers("Some words","Palavras"),(0,1))
    def test_localized_fraction(self): self.assertEqual(bench.check_numbers("72.5","72,5"),(1,1))
    def test_source_without_numbers(self): self.assertEqual(bench.check_numbers("Simple.","Simples."),(0,1))
class EngineTests(unittest.TestCase):
    def test_fake_engine_protocol(self):
        class Fake:
            def translate(self,text): return text[::-1]
        self.assertEqual(bench.run_engine(Fake(),"abc"),"cba")
    def test_explicit_error_not_translated(self):
        self.assertIn("status",bench.HEADERS)
        self.assertIn("error",bench.HEADERS)
    def test_source_included_in_public_results(self):
        self.assertIn("source_text",bench.HEADERS)
    def test_output_included_in_public_results(self):
        self.assertIn("output_text",bench.HEADERS)
    def test_no_human_quality_claim_field(self):
        self.assertNotIn("quality_score",bench.HEADERS)
    def test_target_classification_only_candidates(self):
        self.assertNotIn("fr",bench.CANDIDATE_LOWER_RESOURCE)
    def test_sample_matrix_order(self):
        j=bench.schedule(bench.load_prompts(),["pt","ja"])
        self.assertEqual(j[0]["id"],"CTS-pt-S01")
        self.assertEqual(j[20]["id"],"CTS-ja-S01")
if __name__=="__main__":unittest.main()
