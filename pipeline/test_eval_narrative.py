from __future__ import annotations

import datetime
import io
import os
import re
import sys
import threading
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pca_backend.settings")

from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase

from pipeline.eval_narrative import (
    SAMPLE_PLAYERS,
    _fabricate,
    faithfulness,
    fallback_rate,
    format_scorecard,
    gate_failures,
    hallucination_rate,
    main,
    make_judge,
    rag_hit_rate,
    run_eval,
    tool_selection_accuracy,
)
from players import llm
from players.models import Player
from players.narrative import verify_numbers
from stats.models import BattingSeason


def _res(mode, flagged=None, tools=None, source="llm", text="x", repairs=0):
    trace = {} if mode is None else {
        "mode": mode,
        "repairs": repairs,
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
            _res("agentic", flagged=["999"], source="template", repairs=1),
            _res("agentic", tools=["get_career_totals"]),
            _res("single_shot"),
            _res(None, source="template"),             # no-key template — not an attempt
        ]
        hr = hallucination_rate(results)
        self.assertEqual((hr["n"], hr["caught"]), (3, 1))
        self.assertAlmostEqual(hr["rate"], 1 / 3)

    def test_repaired_draft_counts_as_caught(self):
        hr = hallucination_rate([_res("agentic", repairs=1), _res("agentic")])
        self.assertEqual((hr["n"], hr["caught"]), (2, 1))

    def test_typed_mode_is_an_attempt(self):
        hr = hallucination_rate([_res("agentic_typed", repairs=1), _res("agentic_typed")])
        self.assertEqual((hr["n"], hr["caught"]), (2, 1))

    def test_no_attempts_is_zero(self):
        hr = hallucination_rate([_res(None, source="template")])
        self.assertEqual((hr["n"], hr["rate"]), (0, 0.0))


class TestFallbackRate(SimpleTestCase):
    def test_every_template_cause_counts(self):
        incomplete = _res("agentic", source="template")
        incomplete["trace"]["incomplete"] = "max_tokens"
        results = [
            _res(None, source="template"),
            incomplete,
            _res("agentic", flagged=["999"], source="template", repairs=1),
            _res("agentic", repairs=1),
            _res("agentic"),
        ]
        self.assertEqual(fallback_rate(results, llm_enabled=True), {"n": 5, "template": 3, "rate": 0.6})

    def test_llm_off_measures_nothing(self):
        self.assertEqual(
            fallback_rate([_res(None, source="template")], llm_enabled=False),
            {"n": 0, "template": 0, "rate": 0.0},
        )


def _rates(hallucination, fallback):
    return {
        "hallucination": {"n": hallucination[0], "rate": hallucination[1]},
        "fallback": {"n": fallback[0], "rate": fallback[1]},
    }


class TestGateFailures(SimpleTestCase):
    limits = {"hallucination": 0.3, "fallback": 0.2}

    def test_within_limits_passes(self):
        self.assertEqual(gate_failures(_rates((10, 0.3), (10, 0.2)), self.limits), [])

    def test_hallucination_over_limit(self):
        self.assertEqual(
            gate_failures(_rates((10, 0.4), (10, 0.0)), self.limits),
            ["hallucination rate 40.0% exceeds --max-hallucination 30.0%"],
        )

    def test_fallback_over_limit(self):
        self.assertEqual(
            gate_failures(_rates((10, 0.0), (10, 1.0)), self.limits),
            ["fallback rate 100.0% exceeds --max-fallback 20.0%"],
        )

    def test_reports_every_failure(self):
        self.assertEqual(
            gate_failures(_rates((10, 0.5), (10, 0.5)), self.limits),
            [
                "hallucination rate 50.0% exceeds --max-hallucination 30.0%",
                "fallback rate 50.0% exceeds --max-fallback 20.0%",
            ],
        )

    def test_unrequested_gate_is_not_checked(self):
        self.assertEqual(gate_failures(_rates((10, 0.0), (10, 1.0)), {"hallucination": 0.3}), [])

    def test_nothing_measured_fails(self):
        self.assertEqual(
            gate_failures(_rates((0, 0.0), (10, 1.0)), {"hallucination": 0.3}),
            ["hallucination measured no runs, so --max-hallucination cannot pass"],
        )


class TestToolSelection(SimpleTestCase):
    def test_required_tool_presence(self):
        results = [
            _res("agentic", tools=["get_career_totals", "get_awards"]),
            _res("agentic", tools=["get_awards"]),     # missing required
            _res("single_shot"),                       # ignored (not agentic)
        ]
        ts = tool_selection_accuracy(results)
        self.assertEqual((ts["n"], ts["ok"], ts["rate"]), (2, 1, 0.5))

    def test_typed_mode_is_agentic(self):
        ts = tool_selection_accuracy([_res("agentic_typed", tools=["get_career_totals"])])
        self.assertEqual((ts["n"], ts["ok"]), (1, 1))


class TestRagHitRate(SimpleTestCase):
    def test_hits_and_misses(self):
        # hit, ranking miss, and an empty result (retrieval failed / RAG off)
        cases = [("qA", "war"), ("qB", "positions"), ("qZ", "leaderboard")]
        r = rag_hit_rate(cases, _retrieve, k=3)
        self.assertEqual((r["hits"], r["n"], r["empty"]), (1, 3, 1))
        self.assertAlmostEqual(r["rate"], 1 / 3)
        self.assertEqual(r["misses"], ["positions", "leaderboard"])


class TestFaithfulness(SimpleTestCase):
    def test_mean_of_scores(self):
        f = faithfulness([({"text": "a"}, {}), ({"text": "b"}, {})], judge=lambda t, fa: 4)
        self.assertEqual((f["n"], f["mean"]), (2, 4.0))

    def test_judge_errors_are_skipped(self):
        def bad(text, facts):
            raise RuntimeError("API down")
        f = faithfulness([({"text": "a"}, {})], judge=bad)
        self.assertEqual((f["n"], f["mean"], f["scores"]), (0, None, [None]))

    def test_judge_parses_score_and_rejects_garbage(self):
        with patch("pipeline.eval_narrative.llm.complete_text", side_effect=["4", "N/A"]) as m:
            judge = make_judge("claude-haiku-4-5-20251001")
            self.assertEqual(judge("text", {}), 4)
            with self.assertRaises(ValueError):
                judge("text", {})
        self.assertEqual(m.call_args.kwargs["model"], "claude-haiku-4-5-20251001")

    def test_threaded_scores_stay_aligned(self):
        samples = [({"text": str(i)}, {}) for i in range(1, 6)]
        f = faithfulness(samples, judge=lambda t, fa: int(t), workers=3)
        self.assertEqual(f["scores"], [1, 2, 3, 4, 5])


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
        self.assertEqual([r["faithfulness"] for r in sc["runs"]], [5, 5])
        self.assertEqual(sc["runs"][0]["tools"], ["get_career_totals"])

    def test_untraced_results_count_as_llm_errors(self):
        with self.settings(LLM_ENABLED=True):
            sc = run_eval(
                ["p1", "p2"],
                narrate=lambda pid: _res(None, source="template") if pid == "p1" else _res("agentic"),
                retrieve=_retrieve,
                rag_cases=[],
                workers=2,
            )
        self.assertEqual(sc["llm_errors"], 1)
        self.assertEqual([r["player_id"] for r in sc["runs"]], ["p1", "p2"])

    def test_format_scorecard(self):
        results = {
            "p1": _res("agentic", flagged=["999"], source="template", repairs=1, tools=["get_career_totals"]),
            "p2": _res("agentic", tools=["get_career_totals"]),
        }
        with self.settings(LLM_ENABLED=True, RAG_ENABLED=True):
            sc = run_eval(list(results), narrate=results.__getitem__, retrieve=_retrieve, rag_cases=[("qB", "war")])
        self.assertEqual(format_scorecard(sc).splitlines(), [
            "Narrative eval scorecard",
            "  players evaluated : 2  (llm=on, rag=on)",
            "  llm errors        : 0  (generation raised, served template)",
            "  hallucination     : 50.0% (1/2 first drafts rejected)",
            "  fallback          : 50.0% (1/2 served the template)",
            "  tool selection    : 100.0% (2/2 called ['get_career_totals'])",
            "  rag hit_rate@3    : 100.0% (1/1, 0 empty)",
        ])


def _offline_scorecard(results):
    by_id = {f"p{i}": r for i, r in enumerate(results)}
    return run_eval(list(by_id), narrate=by_id.__getitem__, retrieve=_retrieve, rag_cases=[])


def _cli(argv, scorecard=None):
    err = io.StringIO()
    with redirect_stderr(err), redirect_stdout(io.StringIO()), patch("pipeline.eval_narrative.run_eval") as run:
        run.return_value = scorecard or _offline_scorecard([_res("agentic")])
        try:
            main(argv)
        except SystemExit as e:
            return e.code, err.getvalue(), run
    return 0, err.getvalue(), run


class TestCli(TestCase):
    def test_missing_sample_ids_exit_2_and_are_named(self):
        for pid in SAMPLE_PLAYERS[:-2]:
            Player.objects.create(bbref_id=pid, first_name="F", last_name="L")
        code, err, run = _cli([])
        self.assertEqual(code, 2)
        self.assertEqual(err, "SAMPLE_PLAYERS not in the database: riverma01 mantlmi01\n")
        run.assert_not_called()

    def test_full_sample_runs_in_order(self):
        for pid in SAMPLE_PLAYERS:
            Player.objects.create(bbref_id=pid, first_name="F", last_name="L")
        code, err, run = _cli(["--limit", "3"])
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(run.call_args.args[0], ["ruthba01", "mayswi01", "aaronha01"])

    def test_gate_with_llm_off_exits_2_before_running(self):
        with self.settings(LLM_ENABLED=False):
            code, err, run = _cli(["--max-hallucination", "0.3", "--max-fallback", "0.2"])
        self.assertEqual(code, 2)
        self.assertEqual(
            err,
            "--max-hallucination --max-fallback: the gates need ANTHROPIC_API_KEY; "
            "with the LLM off nothing is measured.\n",
        )
        run.assert_not_called()

    def test_failed_gates_exit_1_with_each_failure(self):
        for pid in SAMPLE_PLAYERS:
            Player.objects.create(bbref_id=pid, first_name="F", last_name="L")
        with self.settings(LLM_ENABLED=True):
            sc = _offline_scorecard([_res("agentic", flagged=["999"], source="template", repairs=1)])
            code, err, _ = _cli(["--max-hallucination", "0.3", "--max-fallback", "0.2"], sc)
        self.assertEqual(code, 1)
        self.assertEqual(err, (
            "FAIL: hallucination rate 100.0% exceeds --max-hallucination 30.0%\n"
            "FAIL: fallback rate 100.0% exceeds --max-fallback 20.0%\n"
        ))

    def test_inject_fault_outside_agentic_mode_exits_2(self):
        for mode, overrides in (
            ("single_shot", {"NARRATIVE_USE_TOOLS": False}),
            ("agentic_typed", {"NARRATIVE_TYPED_VERIFY": True}),
            ("template", {"LLM_ENABLED": False}),
        ):
            with self.subTest(mode), self.settings(**{"LLM_ENABLED": True, **overrides}):
                code, err, run = _cli(["--inject-fault"])
                self.assertEqual(code, 2)
                self.assertEqual(err, (
                    "--inject-fault needs the agentic mode (LLM on, NARRATIVE_USE_TOOLS=true, "
                    f"NARRATIVE_TYPED_VERIFY=false); settings select {mode}.\n"
                ))
                run.assert_not_called()

    def test_passing_gates_exit_0(self):
        for pid in SAMPLE_PLAYERS:
            Player.objects.create(bbref_id=pid, first_name="F", last_name="L")
        with self.settings(LLM_ENABLED=True):
            sc = _offline_scorecard([_res("agentic")])
            code, err, _ = _cli(["--max-hallucination", "0.3", "--max-fallback", "0.2"], sc)
        self.assertEqual((code, err), (0, ""))


class TestFabricate(SimpleTestCase):
    def test_skips_years_and_plants_a_rejected_number(self):
        supported = {1927.0, 60.0, 61.0, 162.4}
        text = "In 1927 he hit 60 home runs and posted 162.4 WAR."
        self.assertEqual(
            _fabricate(text, supported),
            ("In 1927 he hit 62 home runs and posted 162.4 WAR.", "60", "62"),
        )
        self.assertEqual(verify_numbers("In 1927 he hit 62 home runs and posted 162.4 WAR.", supported), ["62"])

    def test_keeps_leading_dot_rate_format(self):
        self.assertEqual(_fabricate("a .342 average", {0.342, 0.343}), ("a .344 average", ".342", ".344"))

    def test_keeps_comma_grouping(self):
        self.assertEqual(_fabricate("2,213 hits", {2213.0}), ("2,214 hits", "2,213", "2,214"))

    def test_nothing_to_plant(self):
        self.assertIsNone(_fabricate("He played from 1914 to 1935.", {1914.0, 1935.0}))
        self.assertIsNone(_fabricate("A great career.", set()))


def _text(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn")


def _agent_model(drafts):
    def complete(system, messages, tools=None, **kwargs):
        pid = re.search(r"'(\w+)'", messages[0]["content"]).group(1)
        if len(messages) == 1:
            call = SimpleNamespace(type="tool_use", name="get_career_totals", input={"player_id": pid}, id="t1")
            return SimpleNamespace(content=[call], stop_reason="tool_use")
        return _text(drafts[pid][(len(messages) - 3) // 2])
    return complete


class TestInjectFault(TestCase):
    def setUp(self):
        cache.clear()
        ruth = Player.objects.create(
            bbref_id="ruthba01", first_name="Babe", last_name="Ruth",
            debut=datetime.date(1914, 5, 6), final_game=datetime.date(1935, 5, 30),
        )
        BattingSeason.objects.create(player=ruth, year=1920, stint=1, team="NYA", league="AL", war=11.5, home_runs=54)

    def test_verifier_catches_plant_and_repair_draft_is_untouched(self):
        clean = "He compiled 11.5 WAR with 54 home runs."
        fake = _agent_model({"ruthba01": [clean, clean]})
        with self.settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=True, NARRATIVE_TYPED_VERIFY=False), \
                patch.object(llm, "complete", side_effect=fake) as model:
            sc = run_eval(["ruthba01"], retrieve=_retrieve, rag_cases=[], inject_fault=True)
            self.assertIs(llm.complete, model)
        run = sc["runs"][0]
        self.assertEqual(run["plant"], {"player_id": "ruthba01", "original": "11.5", "planted": "11.6"})
        self.assertEqual((run["source"], run["repairs"], run["model_calls"], run["text"]), ("llm", 1, 3, clean))
        self.assertEqual(sc["injected"], {"planted": 1, "caught": 1})
        self.assertEqual(sc["hallucination"]["rate"], 1.0)
        self.assertIn("  injected faults   : 1/1 caught", format_scorecard(sc).splitlines())

    def test_off_by_default(self):
        clean = "He compiled 11.5 WAR with 54 home runs."
        with self.settings(LLM_ENABLED=True, NARRATIVE_USE_TOOLS=True, NARRATIVE_TYPED_VERIFY=False), \
                patch.object(llm, "complete", side_effect=_agent_model({"ruthba01": [clean]})):
            sc = run_eval(["ruthba01"], retrieve=_retrieve, rag_cases=[])
        self.assertEqual((sc["runs"][0]["plant"], sc["runs"][0]["repairs"]), (None, 0))
        self.assertNotIn("injected", sc)


class TestInjectFaultThreads(SimpleTestCase):
    def test_each_thread_plants_in_its_own_player(self):
        both_drafting = threading.Barrier(2, timeout=5)

        def model(system, messages, tools=None, **kwargs):
            pid = messages[0]["content"]
            if len(messages) == 1:
                both_drafting.wait()
            return _text({"p1": "He hit 47 home runs.", "p2": "He posted 2.5 WAR."}[pid])

        drafts = {}

        def narrate(pid):
            drafts[pid] = llm.complete("sys", [{"role": "user", "content": pid}]).content[0].text
            repair = llm.complete("sys", [{"role": "user", "content": pid}, {}]).content[0].text
            return {"text": repair, "source": "llm", "flagged": [], "trace": {"mode": "agentic", "repairs": 1}}

        facts = {"p1": {"hr": 47}, "p2": {"war": 2.5}}
        with patch.object(llm, "complete", side_effect=model):
            sc = run_eval(["p1", "p2"], narrate=narrate, retrieve=_retrieve, rag_cases=[],
                          facts_for=facts.__getitem__, workers=2, inject_fault=True)
        self.assertEqual([r["plant"] for r in sc["runs"]], [
            {"player_id": "p1", "original": "47", "planted": "48"},
            {"player_id": "p2", "original": "2.5", "planted": "2.6"},
        ])
        self.assertEqual(drafts, {"p1": "He hit 48 home runs.", "p2": "He posted 2.6 WAR."})
        self.assertEqual([r["text"] for r in sc["runs"]], ["He hit 47 home runs.", "He posted 2.5 WAR."])
