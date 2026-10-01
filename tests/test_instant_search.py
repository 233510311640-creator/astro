import json
import sys
import unittest
import unittest.mock
from datetime import date
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


class FreshnessTests(unittest.TestCase):
    TODAY = date(2026, 10, 1)

    def test_time_sensitive_detection(self):
        self.assertTrue(s.is_time_sensitive("What is the latest stable Python version?"))
        self.assertTrue(s.is_time_sensitive("What was the most recent Fed decision?"))
        self.assertFalse(s.is_time_sensitive("In what year was Python 1.0 released?"))
        self.assertIn("current information", s.build_system(False, True))
        self.assertNotIn("current information", s.build_system(False))

    def test_page_date_prefers_metadata_then_text(self):
        html = '<meta property="article:published_time" content="2026-09-02T10:00:00Z">'
        self.assertEqual(s.page_date(html, "", self.TODAY), date(2026, 9, 2))
        self.assertEqual(s.page_date("", "Released Aug 5, 2026. Next on Dec 1, 2027.", self.TODAY), date(2026, 8, 5))
        self.assertIsNone(s.page_date("", "no dates here", self.TODAY))

    def test_freshness_verdict(self):
        official = {"url": "https://www.python.org/downloads/", "page_full": "x", "date": "2026-09-01"}
        self.assertTrue(s.freshness_verdict([official], self.TODAY)[0])
        stale = dict(official, date="2025-01-01")
        self.assertFalse(s.freshness_verdict([stale], self.TODAY)[0])
        wiki = dict(official, url="https://en.wikipedia.org/wiki/Python")
        self.assertFalse(s.freshness_verdict([wiki], self.TODAY)[0])
        self.assertFalse(s.freshness_verdict([dict(official, page_full="")], self.TODAY)[0])

    def test_newer_source_conflict_catches_stale_version(self):
        old = {"url": "https://a.example/1", "page_full": "Python 3.12.1 is current.", "date": "2025-01-01"}
        new = {"url": "https://www.python.org/d", "page_full": "Python 3.14.6 is current.", "date": "2026-09-01"}
        hit = s.newer_source_conflicts("The latest is Python 3.12.1 [1].", [old, new])
        self.assertEqual(hit[0], 2)
        self.assertIn("3.12.1", hit[2])
        self.assertIsNone(s.newer_source_conflicts("The latest is Python 3.14.6 [2].", [old, new]))

    def test_official_python_latest_picks_newest_stable_release(self):
        feed = json.dumps([
            {"name": "Python 3.14.7", "version": 3, "pre_release": False, "release_date": "2026-09-02T00:00:00Z"},
            {"name": "Python 3.14.6", "version": 3, "pre_release": False, "release_date": "2026-08-01T00:00:00Z"},
            {"name": "Python 3.11.17", "version": 3, "pre_release": False, "release_date": "2026-09-25T00:00:00Z"},
            {"name": "Python 3.15.0rc1", "version": 3, "pre_release": True, "release_date": "2026-09-20T00:00:00Z"},
            {"name": "Python 3.99.0", "version": 3, "pre_release": False, "release_date": "2030-01-01T00:00:00Z"},
            {"name": "Python 2.7.18", "version": 2, "pre_release": False, "release_date": "2020-04-20T00:00:00Z"},
        ]).encode()
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = feed
        with unittest.mock.patch.object(s, "urlopen", return_value=response):
            found = s.official_python_latest(self.TODAY)
        self.assertIn("Python 3.14.7", found["page_full"])
        self.assertIn("2026-09-02", found["page_full"])
        self.assertEqual(s.tier(found["url"]), 0)
        with unittest.mock.patch.object(s, "urlopen", side_effect=OSError("offline")):
            self.assertIsNone(s.official_python_latest(self.TODAY))

    def test_unsafe_version_claim_withholds_stale_or_unbacked_version(self):
        page = {"url": "https://www.python.org/downloads/", "page_full": "Python 3.14.7 is out. Earlier: 3.14.6, 3.13.9."}
        self.assertIn("3.14.7", s.unsafe_version_claim("The latest is Python 3.14.6 [1].", [page]))
        self.assertIsNone(s.unsafe_version_claim("The latest is Python 3.14.7 [1].", [page]))
        self.assertIn("not on any", s.unsafe_version_claim("The latest is Python 3.15.2 [1].", [page]))
        snippet_only = {"url": "https://en.wikipedia.org/wiki/Python", "page_full": ""}
        self.assertIsNone(s.unsafe_version_claim("The latest is Python 3.14.6 [1].", [snippet_only]))
        self.assertIsNone(s.unsafe_version_claim("The Fed raised rates 0.25 points [1].", [page]))
        q = "What is the latest stable release of Python?"
        self.assertIn("no full version", s.unsafe_version_claim("Python 3.14 is the latest stable release [1].", [page], q))
        self.assertIsNone(s.unsafe_version_claim("Python 3.14 is the latest stable release [1].", [page]))
        self.assertIsNone(s.unsafe_version_claim("The Fed raised rates 0.25 points [1].", [page], "What was the latest Fed decision?"))


class QuestionSetTests(unittest.TestCase):
    def test_question_file_shape(self):
        data = json.loads((ROOT / "tests" / "instant_search_questions.json").read_text(encoding="utf-8"))
        questions = data["questions"]
        self.assertEqual(len(questions), 20)
        self.assertEqual(len({q["id"] for q in questions}), 20)
        for category in ("research", "everyday"):
            self.assertEqual(sum(q["category"] == category for q in questions), 10)
        for q in questions:
            for field in ("id", "category", "question", "expected_key_facts", "preferred_source_types", "evaluation_notes"):
                self.assertTrue(q.get(field), (q.get("id"), field))


if __name__ == "__main__":
    unittest.main()
