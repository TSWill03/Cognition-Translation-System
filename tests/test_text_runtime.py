import unittest
from cts_text import translate_document, split_piece, API_VERSION

class LayoutTests(unittest.TestCase):
    def test_layout_and_boundary(self):
        source = "  a\n\nb\n\nc  "
        self.assertEqual(translate_document(lambda xs:[x.strip().upper() for x in xs], source),
                         "  A\n\nB\n\nC  ")

    def test_long_piece_words_do_not_join(self):
        source = "one " * 1000
        self.assertEqual(translate_document(lambda xs:[x.strip().upper() for x in xs], source),
                         source.upper())

    def test_empty_and_alignment(self):
        self.assertEqual(translate_document(lambda _: [], "\n\n"), "\n\n")
        for f in (lambda _: [], lambda xs: [""]*len(xs)):
            with self.assertRaises(RuntimeError):
                translate_document(f, "a")

    def test_split_is_lossless(self):
        source = "some words. " * 400
        self.assertEqual("".join(split_piece(source)), source)

    def test_api_version(self):
        self.assertEqual(API_VERSION, 1)
