"""Offline contract tests: use fakes, never count them as model benchmark results."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import benchmark_bidirectional as bd


class FakeTranslator:
    def translate(self, text):
        return f"translated:{text}"


class FakeBackend:
    version = "fake"
    packages = [{"from": "en", "to": "pt", "version": "fake"}, {"from": "pt", "to": "en", "version": "fake"}]

    def get_translator(self, src, tgt):
        return FakeTranslator()


class BidirectionalTests(unittest.TestCase):
    def test_portuguese_independent_corpus(self):
        data = bd.load_source_corpus(ROOT / "prompts_reverse.json", "pt")
        self.assertEqual(len(data), 20)
        self.assertEqual(len({x["id"] for x in data}), 20)

    def test_missing_language_rejected(self):
        with self.assertRaises(ValueError):
            bd.load_source_corpus(ROOT / "prompts_reverse.json", "es")

    def test_runs_both_directions_independently(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            code = bd.run(outdir=folder, targets=["pt"], mode="independent", limit=2, backend=FakeBackend())
            self.assertEqual(code, 0)
            with (folder / "translations.csv").open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 4)
            self.assertEqual([r["direction"] for r in rows], ["A_to_B", "A_to_B", "B_to_A", "B_to_A"])
            self.assertEqual([r["source_kind"] for r in rows][-2:], ["original_pt_candidate"] * 2)
            self.assertNotIn("translated:", rows[2]["source_text"])
            self.assertEqual(json.loads((folder / "manifest.json").read_text())["success"], 4)

    def test_roundtrip_marks_generated_source(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            self.assertEqual(bd.run(outdir=folder, targets=["pt"], mode="roundtrip", limit=1, backend=FakeBackend()), 0)
            with (folder / "translations.csv").open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[1]["source_kind"], "machine_generated_forward")
            self.assertEqual(rows[1]["source_text"], rows[0]["output_text"])

    def test_bad_arguments_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            for targets, limit in [(["pt", "pt"], None), (["xx"], None), (["pt"], 0)]:
                with self.assertRaises(ValueError):
                    bd.run(outdir=Path(temp), targets=targets, mode="independent", limit=limit, backend=FakeBackend())

    def test_output_failures_are_not_counted_as_success(self):
        class BrokenBackend(FakeBackend):
            def get_translator(self, src, tgt):
                if src == "pt":
                    raise LookupError("missing pt->en")
                return FakeTranslator()

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            self.assertEqual(bd.run(outdir=folder, targets=["pt"], mode="roundtrip", limit=2, backend=BrokenBackend()), 2)
            manifest = json.loads((folder / "manifest.json").read_text())
            self.assertEqual((manifest["success"], manifest["errors"]), (2, 2))


if __name__ == "__main__":
    unittest.main()
