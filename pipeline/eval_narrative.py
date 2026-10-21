from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pca_backend.settings")
django.setup()

from django.conf import settings

from players import llm
from players.models import Player
from players.narrative import build_facts, generate_narrative
from players.rag import search_methodology

SAMPLE_PLAYERS: list[str] = [
    "ruthba01", "mayswi01", "aaronha01", "bondsba01", "troutmi01",
    "koufasa01", "johnswa01", "maddugr01", "riverma01", "mantlmi01",
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

REQUIRED_TOOLS = {"get_career_totals"}

MIN_SAMPLE_SEASONS = 5


LLM_MODES = ("agentic", "agentic_typed", "single_shot")
AGENTIC_MODES = ("agentic", "agentic_typed")


def hallucination_rate(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Among runs where the LLM actually generated text, the fraction whose first
    draft the verifier rejected. A rejected draft either gets repaired (trace
    `repairs` > 0, served as LLM text) or falls back (`flagged` set, served as the
    template); both count. `fell_back` is how many runs ended on the template."""
    attempts = [r for r in results if r.get("trace", {}).get("mode") in LLM_MODES]
    caught = [r for r in attempts if r["trace"].get("repairs") or r.get("flagged")]
    fell_back = [r for r in attempts if r.get("source") == "template"]
    n = len(attempts)
    return {
        "n": n,
        "caught": len(caught),
        "fell_back": len(fell_back),
        "rate": (len(caught) / n) if n else 0.0,
    }


def tool_selection_accuracy(
    results: list[dict[str, Any]], required: set[str] = REQUIRED_TOOLS
) -> dict[str, Any]:
    agentic = [r for r in results if r.get("trace", {}).get("mode") in AGENTIC_MODES]
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
    (With one relevant doc per query this is recall@k / hit-rate.) `empty`
    counts queries that returned nothing at all — retrieval failing or RAG off,
    not a ranking miss — so a broken embedder can't pass for poor relevance."""
    hits = 0
    misses: list[str] = []
    empty = 0
    for query, expected in cases:
        results = retrieve(query, k=k)
        empty += not results
        if expected in {r["slug"] for r in results}:
            hits += 1
        else:
            misses.append(expected)
    n = len(cases)
    return {"n": n, "hits": hits, "rate": (hits / n) if n else 0.0, "k": k, "misses": misses, "empty": empty}


def faithfulness(
    samples: list[tuple[dict[str, Any], dict[str, Any]]],
    judge: Callable[[str, dict[str, Any]], int],
    workers: int = 1,
) -> dict[str, Any]:
    """Average LLM-judge score (1-5) over (result, facts) pairs. `samples` should
    be the LLM-sourced narratives only. `scores` is aligned with `samples`, with
    None where the judge failed (failures are skipped, not scored)."""
    def score(sample: tuple[dict[str, Any], dict[str, Any]]) -> int | None:
        result, facts = sample
        try:
            return int(judge(result["text"], facts))
        except Exception:
            return None

    scores = _map(score, samples, workers)
    valid = [s for s in scores if s is not None]
    n = len(valid)
    return {"n": n, "mean": round(sum(valid) / n, 2) if n else None, "scores": scores}


def _map(fn: Callable[[Any], Any], items: list[Any], workers: int = 1) -> list[Any]:
    if workers <= 1:
        return [fn(x) for x in items]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, items))


def _default_narrate(bbref_id: str) -> dict[str, Any]:
    return generate_narrative(Player.objects.get(pk=bbref_id))


_JUDGE_PROMPT = (
    "You are grading a baseball player summary for faithfulness to the data. "
    "Given the FACTS (JSON) and the SUMMARY, rate 1-5 how fully the summary is "
    "supported by the facts (5 = every claim supported, 1 = mostly unsupported). "
    "Respond with only the integer."
)


def make_judge(model: str | None = None) -> Callable[[str, dict[str, Any]], int]:
    """LLM judge on `model` (default NARRATIVE_MODEL). Pin it when comparing
    narrative models so the grader stays fixed across runs."""
    def judge(text: str, facts: dict[str, Any]) -> int:
        out = llm.complete_text(
            _JUDGE_PROMPT, f"FACTS:\n{json.dumps(facts)}\n\nSUMMARY:\n{text}", max_tokens=8, model=model,
        )
        digits = [c for c in out if c in "12345"]
        if not digits:  # unparseable — skipped by faithfulness(), never scored 0
            raise ValueError(f"unparseable judge reply: {out!r}")
        return int(digits[0])
    return judge


_default_judge = make_judge()


def run_eval(
    player_ids: list[str],
    narrate: Callable[[str], dict[str, Any]] = _default_narrate,
    retrieve: Callable[..., list[dict[str, Any]]] = search_methodology,
    rag_cases: list[tuple[str, str]] = RAG_CASES,
    k: int = 3,
    judge: Callable[[str, dict[str, Any]], int] | None = None,
    facts_for: Callable[[str], dict[str, Any]] | None = None,
    workers: int = 1,
) -> dict[str, Any]:
    def timed(pid: str) -> tuple[dict[str, Any], int]:
        started = time.monotonic()
        result = narrate(pid)
        return result, round((time.monotonic() - started) * 1000)

    timed_results = _map(timed, player_ids, workers)
    results = [r for r, _ in timed_results]
    llm_enabled = bool(getattr(settings, "LLM_ENABLED", False))

    scorecard: dict[str, Any] = {
        "players": len(results),
        "llm_enabled": llm_enabled,
        "rag_enabled": bool(getattr(settings, "RAG_ENABLED", False)),
        # With the LLM on, a result with no trace means generation raised and
        # silently degraded to the template (API error, rate limit, ...).
        "llm_errors": sum(1 for r in results if not r.get("trace")) if llm_enabled else 0,
        "hallucination": hallucination_rate(results),
        "tool_selection": tool_selection_accuracy(results),
        "rag_hit_rate": rag_hit_rate(rag_cases, retrieve, k=k),
    }

    judged: dict[str, int | None] = {}
    if judge is not None:
        get_facts = facts_for or (lambda pid: build_facts(Player.objects.get(pk=pid)))
        llm_ids = [pid for pid, r in zip(player_ids, results) if r.get("source") == "llm"]
        by_id = dict(zip(player_ids, results))
        samples = _map(lambda pid: (by_id[pid], get_facts(pid)), llm_ids, workers)
        f = faithfulness(samples, judge, workers)
        judged = dict(zip(llm_ids, f.pop("scores")))
        scorecard["faithfulness"] = f

    scorecard["runs"] = [
        {
            "player_id": pid,
            "source": r.get("source"),
            "mode": r.get("trace", {}).get("mode"),
            "repairs": r.get("trace", {}).get("repairs"),
            "model_calls": r.get("trace", {}).get("model_calls"),
            "tools": [t["name"] for t in r.get("trace", {}).get("tool_calls", [])],
            "flagged": r.get("flagged", []),
            "faithfulness": judged.get(pid),
            "incomplete": r.get("trace", {}).get("incomplete"),
            "latency_ms": ms,
            "input_tokens": r.get("trace", {}).get("input_tokens", 0),
            "output_tokens": r.get("trace", {}).get("output_tokens", 0),
            "cache_read_tokens": r.get("trace", {}).get("cache_read_tokens", 0),
            "text": r.get("text"),
        }
        for pid, (r, ms) in zip(player_ids, timed_results)
    ]
    return scorecard


def sample_players(n: int, seed: int = 0) -> list[str]:
    pool = sorted(
        pid
        for pid, debut, final in Player.objects.filter(debut__isnull=False, final_game__isnull=False)
        .values_list("bbref_id", "debut", "final_game")
        if final.year - debut.year + 1 >= MIN_SAMPLE_SEASONS
    )
    return random.Random(seed).sample(pool, min(n, len(pool)))


def format_scorecard(sc: dict[str, Any]) -> str:
    lines = [
        "Narrative eval scorecard",
        f"  players evaluated : {sc['players']}  (llm={'on' if sc['llm_enabled'] else 'off'}, "
        f"rag={'on' if sc['rag_enabled'] else 'off'})",
        f"  llm errors        : {sc['llm_errors']}  (generation raised, served template)",
        f"  hallucination     : {sc['hallucination']['rate']:.1%} "
        f"({sc['hallucination']['caught']}/{sc['hallucination']['n']} first drafts rejected, "
        f"{sc['hallucination']['fell_back']} fell back to template)",
        f"  tool selection    : {sc['tool_selection']['rate']:.1%} "
        f"({sc['tool_selection']['ok']}/{sc['tool_selection']['n']} called {sorted(REQUIRED_TOOLS)})",
        f"  rag hit_rate@{sc['rag_hit_rate']['k']}    : {sc['rag_hit_rate']['rate']:.1%} "
        f"({sc['rag_hit_rate']['hits']}/{sc['rag_hit_rate']['n']}, {sc['rag_hit_rate']['empty']} empty)",
    ]
    if "faithfulness" in sc:
        f = sc["faithfulness"]
        lines.append(f"  faithfulness      : {f['mean']}/5  (n={f['n']})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate the grounded narrative agent.")
    parser.add_argument("--limit", type=int, default=None, help="Cap number of sample players.")
    parser.add_argument(
        "--sample", type=int, default=None,
        help=f"Evaluate N random players (careers >= {MIN_SAMPLE_SEASONS} seasons) instead of the fixtures.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Random seed for --sample.")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent generations / judge calls.")
    parser.add_argument("--out", default=None, help="Write the scorecard plus per-player runs to this JSON file.")
    parser.add_argument("--k", type=int, default=3, help="top-k for RAG hit-rate.")
    parser.add_argument("--json", action="store_true", help="Emit the scorecard as JSON.")
    parser.add_argument("--faithfulness", action="store_true", help="Run the LLM-judge metric (needs a key).")
    parser.add_argument("--judge-model", default=None, help="Model for the judge (default NARRATIVE_MODEL).")
    parser.add_argument(
        "--max-hallucination", type=float, default=None,
        help="CI gate: exit 1 if hallucination rate exceeds this (e.g. 0.0).",
    )
    args = parser.parse_args(argv)

    if args.sample:
        player_ids = sample_players(args.sample, args.seed)
    else:
        present = set(Player.objects.filter(bbref_id__in=SAMPLE_PLAYERS).values_list("bbref_id", flat=True))
        missing = [pid for pid in SAMPLE_PLAYERS if pid not in present]
        if missing:
            print(f"SAMPLE_PLAYERS not in the database: {' '.join(missing)}", file=sys.stderr)
            sys.exit(2)
        player_ids = list(SAMPLE_PLAYERS)
    if args.limit:
        player_ids = player_ids[: args.limit]
    if not player_ids:
        print("No sample players found in the database — ingest data first.", file=sys.stderr)
        sys.exit(2)

    judge = make_judge(args.judge_model) if (args.faithfulness and getattr(settings, "LLM_ENABLED", False)) else None
    scorecard = run_eval(player_ids, k=args.k, judge=judge, workers=args.workers)
    runs = scorecard.pop("runs")

    print(json.dumps(scorecard, indent=2) if args.json else format_scorecard(scorecard))
    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"scorecard": scorecard, "runs": runs}, fh, indent=2)

    if args.max_hallucination is not None and scorecard["hallucination"]["rate"] > args.max_hallucination:
        print(f"FAIL: hallucination rate {scorecard['hallucination']['rate']:.1%} "
              f"exceeds gate {args.max_hallucination:.1%}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
