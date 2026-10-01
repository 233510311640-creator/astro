import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "v1"))

import instant_search as s  # noqa: E402


class TierTests(unittest.TestCase):
    def test_university_repository_is_not_official(self):
        url = "https://touroscholar.touro.edu/cgi/viewcontent.cgi?article=1326"
        self.assertEqual(s.tier("https://touroscholar.touro.edu/sjlcas/vol16/iss2/12/"), 2)
        self.assertEqual(s.label_of(url), "UNIVERSITY (unvetted)")

    def test_official_and_news_tiers(self):
        self.assertEqual(s.tier("https://pmc.ncbi.nlm.nih.gov/articles/PMC9099935/"), 0)
        self.assertEqual(s.tier("https://www.python.org/download/releases/"), 0)
        self.assertEqual(s.tier("https://www.isro.gov.in/"), 0)
        self.assertEqual(s.tier("https://airandspace.si.edu/explore"), 0)
        self.assertEqual(s.tier("https://www.bbc.com/news/x"), 1)
        self.assertEqual(s.tier("https://timesofindia.indiatimes.com/a"), 1)
        self.assertEqual(s.tier("https://www.thehindu.com/a"), 1)
        self.assertEqual(s.tier("https://en.wikipedia.org/wiki/History_of_Python"), 2)
        self.assertEqual(s.tier("https://github.com/python/cpython"), 2)


class SensitiveTests(unittest.TestCase):
    def test_non_health_questions(self):
        for q in ["In what year was Python 1.0 released?",
                  "What is the minimum TLS version recommended by NIST?",
                  "Is it safe to use Python's pickle module on untrusted data?",
                  "What was the outcome of the most recent US Federal Reserve interest rate decision?"]:
            self.assertFalse(s.is_sensitive(q), q)
            self.assertIn("do not add any advice", s.build_system(False))

    def test_health_questions(self):
        for q in ["Is it safe to take ibuprofen and acetaminophen together?",
                  "Does creatine damage the kidneys?",
                  "How does intermittent fasting compare with calorie restriction?",
                  "Does vitamin D supplementation reduce fracture risk?"]:
            self.assertTrue(s.is_sensitive(q), q)
        self.assertIn("check with a qualified professional", s.build_system(True))


class ExcerptTests(unittest.TestCase):
    def test_excerpt_reaches_the_relevant_passage(self):
        filler = "history of the language and community. " * 400
        text = "Intro text. " + filler + " Python 1.0 was released in January 1994. " + filler
        excerpt = s.focus_excerpt(text, "In what year was Python 1.0 released?")
        self.assertIn("January 1994", excerpt)
        self.assertLessEqual(len(excerpt), s.PAGE_CHARS + 400)

    def test_short_text_unchanged(self):
        self.assertEqual(s.focus_excerpt("short page", "anything"), "short page")


class ClaimCheckTests(unittest.TestCase):
    sources = [
        {"url": "https://a.test", "title": "Fed holds", "description": "Rates stay at 3.5%-3.75% after a 9-3 vote."},
        {"url": "https://b.test", "title": "BBC", "description": "Fed raised rates to 3.75%-4%.", "page_full": "unanimous vote"},
    ]

    def test_supported_figures_pass(self):
        checked, missing = s.verify_claims("The Fed raised rates to 3.75%-4% in a unanimous vote [2].", self.sources)
        self.assertEqual(missing, [])
        self.assertGreaterEqual(checked, 2)

    def test_unsupported_claim_flagged_against_cited_source_only(self):
        _, missing = s.verify_claims("The vote was unanimous [1].", self.sources)
        self.assertEqual(len(missing), 1)
        self.assertIn("unanimous", missing[0])

    def test_invented_figure_flagged(self):
        _, missing = s.verify_claims("Rates rose to 5.25% [2].", self.sources)
        self.assertTrue(any("5.25%" in m for m in missing))

    def test_uncited_official_and_snippet_only(self):
        results = [
            {"url": "https://www.python.org/x", "page_text": "text", "page_full": "released in 1994"},
            {"url": "https://blog.example.com/y"},
        ]
        self.assertEqual(s.uncited_official("Released in 1994 [2].", results), [1])
        self.assertEqual(s.uncited_official("Released in 1995 [2].", results), [])   # page does not back the claim
        self.assertEqual(s.uncited_official("Answer [1].", results), [])
        self.assertTrue(s.only_snippets_cited("Answer [2].", results))
        self.assertFalse(s.only_snippets_cited("Answer [1].", results))


class QuestionSetTests(unittest.TestCase):
    def test_question_file_shape(self):
        data = json.loads((ROOT / "tests" / "instant_search_questions.json").read_text(encoding="utf-8"))
        questions = data["questions"]
        self.assertEqual(len(questions), 20)
        self.assertEqual(len({q["id"] for q in questions}), 20)
        for category in ("stable_factual", "current_events", "multi_source_comparison", "health_or_technical"):
            self.assertEqual(sum(q["category"] == category for q in questions), 5)
        for q in questions:
            for field in ("id", "category", "question", "expected_key_facts", "preferred_source_types", "evaluation_notes"):
                self.assertTrue(q.get(field), (q.get("id"), field))


if __name__ == "__main__":
    unittest.main()
