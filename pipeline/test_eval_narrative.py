"""
Tests for pipeline/eval_narrative.py.

The metric functions are pure and `run_eval` takes injected callables, so the
whole suite runs offline with no keys, no model calls, and no database.

Run from project root:
    python -m pytest pipeline/test_eval_narrative.py -v
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pca_backend.settings")

from django.test import SimpleTestCase

from pipeline.eval_narrative import (
    faithfulness,
    format_scorecard,
    hallucination_rate,
    rag_hit_rate,
    run_eval,
    tool_selection_accuracy,
)


def _res(mode, flagged=None, tools=None, source="llm", text="x"):
    trace = {} if mode is None else {
        "mode": mode,
        "tool_calls": [{"name": t, "input": {}} for t in (tools or [])],
    }
    return {"text": text, "source": source, "flagged": flagged or [], "trace": trace}


def _retrieve(query, k=3):
    table = {
        "qA": [{"slug": "war"}],
        "qB": [{"slug": "similarity"}, {"slug": "war"}],
    }
    return table.get(query, [])[:k]


class TestHallucinationRate(SimpleTestCase):
    def test_counts_only_llm_attempts(self):
        results = [
            _res("agentic", flagged=["999"]),          # caught
            _res("agentic", tools=["get_career_totals"]),
            _res("single_shot"),
            _res(None, source="template"),             # no-key template — not an attempt
        ]
        hr = hallucination_rate(results)
        self.assertEqual((hr["n"], hr["caught"]), (3, 1))
        self.assertAlmostEqual(hr["rate"], 1 / 3)

    def test_no_attempts_is_zero(self):
        hr = hallucination_rate([_res(None, source="template")])
        self.assertEqual((hr["n"], hr["rate"]), (0, 0.0))


class TestToolSelection(SimpleTestCase):
    def test_required_tool_presence(self):
        results = [
            _res("agentic", tools=["get_career_totals", "get_awards"]),
            _res("agentic", tools=["get_awards"]),     # missing required
            _res("single_shot"),                       # ignored (not agentic)
        ]
        ts = tool_selection_accuracy(results)
        self.assertEqual((ts["n"], ts["ok"], ts["rate"]), (2, 1, 0.5))


class TestRagHitRate(SimpleTestCase):
    def test_hits_and_misses(self):
        cases = [("qA", "war"), ("qB", "positions")]  # first hits, second misses
        r = rag_hit_rate(cases, _retrieve, k=3)
        self.assertEqual((r["hits"], r["n"]), (1, 2))
        self.assertAlmostEqual(r["rate"], 0.5)
        self.assertEqual(r["misses"], ["positions"])


class TestFaithfulness(SimpleTestCase):
    def test_mean_of_scores(self):
        f = faithfulness([({"text": "a"}, {}), ({"text": "b"}, {})], judge=lambda t, fa: 4)
        self.assertEqual((f["n"], f["mean"]), (2, 4.0))

    def test_judge_errors_are_skipped(self):
        def bad(text, facts):
            raise ValueError("nope")
        f = faithfulness([({"text": "a"}, {})], judge=bad)
        self.assertEqual((f["n"], f["mean"]), (0, None))


class TestRunEval(SimpleTestCase):
    def test_assembles_scorecard_offline(self):
        sc = run_eval(
            ["p1", "p2"],
            narrate=lambda pid: _res("agentic", tools=["get_career_totals"]),
            retrieve=_retrieve,
            rag_cases=[("qA", "war")],
            k=3,
            judge=lambda t, f: 5,
            facts_for=lambda pid: {},
        )
        self.assertEqual(sc["players"], 2)
        self.assertEqual(sc["hallucination"]["rate"], 0.0)
        self.assertEqual(sc["tool_selection"]["rate"], 1.0)
        self.assertEqual(sc["rag_hit_rate"]["hits"], 1)
        self.assertEqual(sc["faithfulness"]["mean"], 5.0)

    def test_format_scorecard_smoke(self):
        sc = run_eval(
            ["p1"],
            narrate=lambda pid: _res("agentic", flagged=["999"], tools=["get_career_totals"]),
            retrieve=_retrieve,
            rag_cases=[("qB", "war")],
        )
        out = format_scorecard(sc)
        self.assertIn("hallucination", out)
        self.assertIn("rag hit_rate@3", out)
