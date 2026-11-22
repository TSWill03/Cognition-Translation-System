import unittest
from benchmark_profiles import char_f2, numeric_counts, cases_for

class QualityTests(unittest.TestCase):
    def test_numeric_multiplicity(self):
        self.assertEqual(numeric_counts("3,5 and 3,5 and 2","3.5 and 2"), (3,2))
        self.assertEqual(numeric_counts("12.50, 30","12,50 and 30"),(2,2))
        self.assertEqual(numeric_counts("no digits","none"),(0,0))
    def test_identical_character_reference(self):
        self.assertEqual(char_f2("same phrase","same phrase"),100.0)
    def test_directions_and_unique_cases(self):
        rows=cases_for(None)
        self.assertEqual(len(rows),20)
        self.assertEqual(len({r["id"] for r in rows}),20)
        self.assertEqual({(r["source"],r["target"]) for r in rows},{("en","pt"),("pt","en")})
