"""
Evaluation harness for the grounded narrative agent (step 5).

Runs the agent over a fixed sample of players and the methodology retriever over
labeled questions, and reports a scorecard:

  - hallucination_rate   — fraction of LLM generations that emitted a number the
                           verifier rejected (caught → fell back). Deterministic,
                           no judge needed; this is the headline safety metric.
  - tool_selection       — fraction of agent runs that called the required tools.
  - rag_hit_rate@k       — fraction of labeled questions whose expected doc is in
                           the top-k retrieved chunks.
  - faithfulness         — optional LLM-as-judge score (1-5) of how well each
                           summary is supported by its facts; skipped without a key.

The metric functions are pure and take injected `narrate` / `retrieve` / `judge`
callables, so the suite is fully testable offline (see pipeline/test_eval_narrative.py).
Run for real (needs ANTHROPIC_API_KEY, and VOYAGE_API_KEY + an indexed corpus):

    python pipeline/eval_narrative.py
    python pipeline/eval_narrative.py --max-hallucination 0.0   # CI gate

Run from the project root.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pca_backend.settings")
django.setup()

from django.conf import settings  # noqa: E402

from players import llm  # noqa: E402
from players.models import Player  # noqa: E402
from players.narrative import build_facts, generate_narrative  # noqa: E402
from players.rag import search_methodology  # noqa: E402

# --- Labeled fixtures ------------------------------------------------------

# Well-known players spanning eras and roles; filtered to those present in the DB.
SAMPLE_PLAYERS: list[str] = [
    "ruthba01", "mayswi01", "aaronha01", "bondsba01", "troutmi01",
    "koufasa01", "johnswa01", "maddugr01", "riverma01", "mantmi01",
]

# (question, expected methodology doc slug) — the doc that should answer it.
RAG_CASES: list[tuple[str, str]] = [
    ("which WAR system is used and why bWAR over fWAR", "war"),
    ("what does OPS+ mean and how is it calculated", "era-adjusted-metrics"),
    ("how are similar players found", "similarity"),
    ("how is a player's primary position determined", "positions"),
    ("what is the career WAR cutoff for the leaderboard", "leaderboard"),
    ("how do the pitch zone heatmaps work", "pitch-zones"),
    ("how are the hall of fame scores computed", "james-scores"),
]

REQUIRED_TOOLS = {"get_career_totals"}  # the minimum an agent run should call

# --- Metric functions (pure; operate on result dicts) ----------------------


def hallucination_rate(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Among runs where the LLM actually generated text, the fraction whose
    output contained a number the verifier rejected."""
    attempts = [r for r in results if r.get("trace", {}).get("mode") in ("agentic", "single_shot")]
    caught = [r for r in attempts if r.get("flagged")]
    n = len(attempts)
    return {"n": n, "caught": len(caught), "rate": (len(caught) / n) if n else 0.0}


def tool_selection_accuracy(
    results: list[dict[str, Any]], required: set[str] = REQUIRED_TOOLS
) -> dict[str, Any]:
    agentic = [r for r in results if r.get("trace", {}).get("mode") == "agentic"]
    ok = [
        r for r in agentic
        if required.issubset({t["name"] for t in r["trace"].get("tool_calls", [])})
    ]
    n = len(agentic)
    return {"n": n, "ok": len(ok), "rate": (len(ok) / n) if n else 0.0}


def rag_hit_rate(
    cases: list[tuple[str, str]],
    retrieve: Callable[..., list[dict[str, Any]]],
    k: int = 3,
) -> dict[str, Any]:
    """Fraction of questions whose expected doc appears in the top-k results.
    (With one relevant doc per query this is recall@k / hit-rate.)"""
    hits = 0
    misses: list[str] = []
    for query, expected in cases:
        slugs = {r["slug"] for r in retrieve(query, k=k)}
        if expected in slugs:
            hits += 1
        else:
            misses.append(expected)
    n = len(cases)
    return {"n": n, "hits": hits, "rate": (hits / n) if n else 0.0, "k": k, "misses": misses}


def faithfulness(
    samples: list[tuple[dict[str, Any], dict[str, Any]]],
    judge: Callable[[str, dict[str, Any]], int],
) -> dict[str, Any]:
    """Average LLM-judge score (1-5) over (result, facts) pairs. `samples` should
    be the LLM-sourced narratives only."""
    scores: list[int] = []
    for result, facts in samples:
        try:
            scores.append(int(judge(result["text"], facts)))
        except (ValueError, TypeError):
            continue
    n = len(scores)
    return {"n": n, "mean": round(sum(scores) / n, 2) if n else None}


# --- Default live wiring ---------------------------------------------------


def _default_narrate(bbref_id: str) -> dict[str, Any]:
    return generate_narrative(Player.objects.get(pk=bbref_id))


_JUDGE_PROMPT = (
    "You are grading a baseball player summary for faithfulness to the data. "
    "Given the FACTS (JSON) and the SUMMARY, rate 1-5 how fully the summary is "
    "supported by the facts (5 = every claim supported, 1 = mostly unsupported). "
    "Respond with only the integer."
)


def _default_judge(text: str, facts: dict[str, Any]) -> int:
    out = llm.complete_text(_JUDGE_PROMPT, f"FACTS:\n{json.dumps(facts)}\n\nSUMMARY:\n{text}", max_tokens=8)
    return int("".join(c for c in out if c.isdigit())[:1] or "0")


# --- Orchestration ---------------------------------------------------------


def run_eval(
    player_ids: list[str],
    narrate: Callable[[str], dict[str, Any]] = _default_narrate,
    retrieve: Callable[..., list[dict[str, Any]]] = search_methodology,
    rag_cases: list[tuple[str, str]] = RAG_CASES,
    k: int = 3,
    judge: Callable[[str, dict[str, Any]], int] | None = None,
    facts_for: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run all metrics and assemble a scorecard. Inject `narrate`/`retrieve`/
    `judge` for offline testing; defaults call the real agent and retriever."""
    results = [narrate(pid) for pid in player_ids]

    scorecard: dict[str, Any] = {
        "players": len(results),
        "llm_enabled": bool(getattr(settings, "LLM_ENABLED", False)),
        "rag_enabled": bool(getattr(settings, "RAG_ENABLED", False)),
        "hallucination": hallucination_rate(results),
        "tool_selection": tool_selection_accuracy(results),
        "rag_hit_rate": rag_hit_rate(rag_cases, retrieve, k=k),
    }

    if judge is not None:
        get_facts = facts_for or (lambda pid: build_facts(Player.objects.get(pk=pid)))
        samples = [
            (r, get_facts(pid))
            for pid, r in zip(player_ids, results)
            if r.get("source") == "llm"
        ]
        scorecard["faithfulness"] = faithfulness(samples, judge)

    return scorecard


def format_scorecard(sc: dict[str, Any]) -> str:
    lines = [
        "Narrative eval scorecard",
        f"  players evaluated : {sc['players']}  (llm={'on' if sc['llm_enabled'] else 'off'}, "
        f"rag={'on' if sc['rag_enabled'] else 'off'})",
        f"  hallucination     : {sc['hallucination']['rate']:.1%} "
        f"({sc['hallucination']['caught']}/{sc['hallucination']['n']} caught & repaired/fell back)",
        f"  tool selection    : {sc['tool_selection']['rate']:.1%} "
        f"({sc['tool_selection']['ok']}/{sc['tool_selection']['n']} called {sorted(REQUIRED_TOOLS)})",
        f"  rag hit_rate@{sc['rag_hit_rate']['k']}    : {sc['rag_hit_rate']['rate']:.1%} "
        f"({sc['rag_hit_rate']['hits']}/{sc['rag_hit_rate']['n']})",
    ]
    if "faithfulness" in sc:
        f = sc["faithfulness"]
        lines.append(f"  faithfulness      : {f['mean']}/5  (n={f['n']})")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the grounded narrative agent.")
    parser.add_argument("--limit", type=int, default=None, help="Cap number of sample players.")
    parser.add_argument("--k", type=int, default=3, help="top-k for RAG hit-rate.")
    parser.add_argument("--json", action="store_true", help="Emit the scorecard as JSON.")
    parser.add_argument("--faithfulness", action="store_true", help="Run the LLM-judge metric (needs a key).")
    parser.add_argument(
        "--max-hallucination", type=float, default=None,
        help="CI gate: exit 1 if hallucination rate exceeds this (e.g. 0.0).",
    )
    args = parser.parse_args()

    present = list(
        Player.objects.filter(bbref_id__in=SAMPLE_PLAYERS).values_list("bbref_id", flat=True)
    )
    player_ids = [pid for pid in SAMPLE_PLAYERS if pid in present]
    if args.limit:
        player_ids = player_ids[: args.limit]
    if not player_ids:
        print("No sample players found in the database — ingest data first.", file=sys.stderr)
        sys.exit(2)

    judge = _default_judge if (args.faithfulness and getattr(settings, "LLM_ENABLED", False)) else None
    scorecard = run_eval(player_ids, k=args.k, judge=judge)

    print(json.dumps(scorecard, indent=2) if args.json else format_scorecard(scorecard))

    if args.max_hallucination is not None and scorecard["hallucination"]["rate"] > args.max_hallucination:
        print(f"FAIL: hallucination rate {scorecard['hallucination']['rate']:.1%} "
              f"exceeds gate {args.max_hallucination:.1%}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
