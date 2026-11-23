"""Prevent stale or accidentally concatenated active document headings."""
import unittest

from scripts import check_active_docs


class HeadingGuardTests(unittest.TestCase):
    def test_two_headings_joined_on_one_line_are_rejected(self):
        bad = "## November 22 — reset## November 23 — live tests\n"
        self.assertIsNotNone(check_active_docs.JOINED_HEADINGS.search(bad))

    def test_separate_headings_do_not_trigger(self):
        correct = "## November 22 — reset\n\n## November 23 — live tests\n"
        self.assertIsNone(check_active_docs.JOINED_HEADINGS.search(correct))

    def test_optional_closing_atx_heading_does_not_trigger(self):
        valid = "## A heading ##\nText follows.\n"
        self.assertIsNone(check_active_docs.JOINED_HEADINGS.search(valid))


if __name__ == "__main__":
    unittest.main()
