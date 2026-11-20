import unittest

from scripts.odin_note_check import byte_count_proposal


class CodingReviewTests(unittest.TestCase):
    def test_recognizes_utf8_byte_count(self):
        for expression in ("len(text.encode())", 'len(text.encode("utf-8"))'):
            self.assertEqual(byte_count_proposal(expression), (expression, True))

    def test_rejects_character_count_and_extended_code(self):
        for expression in ("len(text)", "len(text.encode()) + 1", "def f(): pass", "x"*200):
            proposal, match = byte_count_proposal(expression)
            self.assertFalse(match)
            self.assertLessEqual(len(proposal), 160)
