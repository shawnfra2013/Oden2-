import unittest

from scripts.odin_note_check import byte_count_proposal


class CodingReviewTests(unittest.TestCase):
    def test_recognizes_utf8_byte_count(self):
        for expression in ("len(text.encode())", 'len(text.encode("utf-8"))'):
            self.assertEqual(byte_count_proposal(expression), (expression, True))

    def test_accepts_correct_expression_wrapped_in_inline_markdown(self):
        proposal, match = byte_count_proposal("`len(text.encode('utf-8'))`")
        self.assertEqual(proposal, "len(text.encode('utf-8'))")
        self.assertTrue(match)

    def test_does_not_accept_wrong_expression_or_extra_text_in_backticks(self):
        for response in (
            "`len(text)`",
            "`len(text.encode())` and nothing else",
            "``len(text.encode())``",
            "`len(text.encode())\nmore`",
        ):
            with self.subTest(response=response):
                self.assertFalse(byte_count_proposal(response)[1])

    def test_rejects_character_count_and_extended_code(self):
        for expression in ("len(text)", "len(text.encode()) + 1", "def f(): pass", "x"*200):
            proposal, match = byte_count_proposal(expression)
            self.assertFalse(match)
            self.assertLessEqual(len(proposal), 160)
