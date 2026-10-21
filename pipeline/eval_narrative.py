from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterator, NamedTuple

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pca_backend.settings")
django.setup()

from django.conf import settings

from players import llm, narrative
from players.models import Player
from players.narrative import allowed_numbers, build_facts, generate_narrative, narrative_mode, verify_numbers
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


def _first_draft_rejected(result: dict[str, Any]) -> bool:
    """The verifier rejected the first draft: it was repaired (trace `repairs` > 0,
    served as LLM text) or fell back (`flagged` set, served as the template)."""
    return bool(result.get("trace", {}).get("repairs") or result.get("flagged"))


def hallucination_rate(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Among runs where the LLM actually generated text, the fraction whose first
    draft the verifier rejected."""
    attempts = [r for r in results if r.get("trace", {}).get("mode") in LLM_MODES]
    caught = [r for r in attempts if _first_draft_rejected(r)]
    n = len(attempts)
    return {"n": n, "caught": len(caught), "rate": (len(caught) / n) if n else 0.0}


def fallback_rate(results: list[dict[str, Any]], llm_enabled: bool) -> dict[str, Any]:
    """With the LLM on, the fraction of players served the template, whatever the
    cause: verifier rejection after repair, a truncated or empty draft, or a
    generation error. A model that only ever falls back scores 0% hallucination,
    so this is the metric that catches it."""
    attempts = results if llm_enabled else []
    template = sum(1 for r in attempts if r.get("source") == "template")
    n = len(attempts)
    return {"n": n, "template": template, "rate": (template / n) if n else 0.0}


def injection_caught(results: list[dict[str, Any]], plants: list[Plant | None]) -> dict[str, Any]:
    """Of the runs that got a planted number, how many the verifier rejected."""
    planted = [r for r, plant in zip(results, plants) if plant is not None]
    return {"planted": len(planted), "caught": sum(1 for r in planted if _first_draft_rejected(r))}


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


@dataclass(frozen=True)
class Plant:
    """One unsupported number planted in a player's first final draft."""
    player_id: str
    original: str
    planted: str


def _fabricate(text: str, supported: set[float]) -> tuple[str, str, str] | None:
    """Bump the first non-year number in `text` to the nearest value, at the same
    precision and format, that verify_numbers rejects against `supported`.
    Returns (new_text, original, planted), or None if no number can be bumped."""
    for m in narrative._NUM_RE.finditer(text):
        tok = m.group()
        val, decimals = narrative._parse_token(tok)
        if decimals == 0 and 1850 <= val <= 2030:  # a bumped year usually lands on another active year
            continue
        sep = "," if "," in tok else ""
        for bump in range(1, 20):
            new = f"{val + bump * 10 ** -decimals:{sep}.{decimals}f}"
            if tok.startswith("."):
                new = new.removeprefix("0")
            if verify_numbers(new, supported):
                return text[: m.start()] + new + text[m.end():], tok, new
    return None


@dataclass
class _Draft:
    player_id: str
    plant: Plant | None = None


# Per eval thread: the player whose first final draft has not been seen yet.
_awaiting_draft = threading.local()


@contextmanager
def _planting_faults(supported_for: Callable[[str], set[float]]) -> Iterator[None]:
    """While active, llm.complete plants one unsupported number in each player's
    first final draft (the first response with no tool_use) and passes every
    other response through, so tool turns and repair drafts are untouched."""
    real = llm.complete

    def complete(*args: Any, **kwargs: Any) -> Any:
        resp = real(*args, **kwargs)
        draft: _Draft | None = getattr(_awaiting_draft, "draft", None)
        if draft is None or any(getattr(b, "type", None) == "tool_use" for b in resp.content):
            return resp
        _awaiting_draft.draft = None
        supported = supported_for(draft.player_id)
        for block in (b for b in resp.content if getattr(b, "type", None) == "text"):
            found = _fabricate(block.text, supported)
            if found:
                block.text, original, planted = found
                draft.plant = Plant(draft.player_id, original, planted)
                break
        return resp

    llm.complete = complete
    try:
        yield
    finally:
        llm.complete = real


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
    inject_fault: bool = False,
) -> dict[str, Any]:
    get_facts = facts_for or (lambda pid: build_facts(Player.objects.get(pk=pid)))

    def timed(pid: str) -> tuple[dict[str, Any], int, Plant | None]:
        draft = _awaiting_draft.draft = _Draft(pid)
        started = time.monotonic()
        try:
            result = narrate(pid)
        finally:
            _awaiting_draft.draft = None
        return result, round((time.monotonic() - started) * 1000), draft.plant

    planting = _planting_faults(lambda pid: allowed_numbers(get_facts(pid))) if inject_fault else nullcontext()
    with planting:
        timed_results = _map(timed, player_ids, workers)
    results = [r for r, _, _ in timed_results]
    plants = [plant for _, _, plant in timed_results]
    llm_enabled = bool(getattr(settings, "LLM_ENABLED", False))

    scorecard: dict[str, Any] = {
        "players": len(results),
        "llm_enabled": llm_enabled,
        "rag_enabled": bool(getattr(settings, "RAG_ENABLED", False)),
        # With the LLM on, a result with no trace means generation raised and
        # silently degraded to the template (API error, rate limit, ...).
        "llm_errors": sum(1 for r in results if not r.get("trace")) if llm_enabled else 0,
        "hallucination": hallucination_rate(results),
        "fallback": fallback_rate(results, llm_enabled),
        "tool_selection": tool_selection_accuracy(results),
        "rag_hit_rate": rag_hit_rate(rag_cases, retrieve, k=k),
    }
    if inject_fault:
        scorecard["injected"] = injection_caught(results, plants)

    judged: dict[str, int | None] = {}
    if judge is not None:
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
            "plant": asdict(plant) if plant else None,
        }
        for pid, (r, ms, plant) in zip(player_ids, timed_results)
    ]
    return scorecard


class Gate(NamedTuple):
    metric: Callable[[dict[str, Any]], dict[str, Any]]  # scorecard -> section with "n" and "rate"
    flag: str


GATES: dict[str, Gate] = {
    "hallucination": Gate(lambda sc: sc["hallucination"], "--max-hallucination"),
    "fallback": Gate(lambda sc: sc["fallback"], "--max-fallback"),
}


def gate_failures(scorecard: dict[str, Any], limits: dict[str, float]) -> list[str]:
    """One message per gate in `limits` (name -> max rate) that the scorecard
    fails. A gate that measured no runs fails rather than passing on nothing."""
    failures: list[str] = []
    for name, limit in limits.items():
        gate = GATES[name]
        metric = gate.metric(scorecard)
        if not metric["n"]:
            failures.append(f"{name} measured no runs, so {gate.flag} cannot pass")
        elif metric["rate"] > limit:
            failures.append(f"{name} rate {metric['rate']:.1%} exceeds {gate.flag} {limit:.1%}")
    return failures


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
        f"({sc['hallucination']['caught']}/{sc['hallucination']['n']} first drafts rejected)",
        f"  fallback          : {sc['fallback']['rate']:.1%} "
        f"({sc['fallback']['template']}/{sc['fallback']['n']} served the template)",
        f"  tool selection    : {sc['tool_selection']['rate']:.1%} "
        f"({sc['tool_selection']['ok']}/{sc['tool_selection']['n']} called {sorted(REQUIRED_TOOLS)})",
        f"  rag hit_rate@{sc['rag_hit_rate']['k']}    : {sc['rag_hit_rate']['rate']:.1%} "
        f"({sc['rag_hit_rate']['hits']}/{sc['rag_hit_rate']['n']}, {sc['rag_hit_rate']['empty']} empty)",
    ]
    if "injected" in sc:
        lines.append(f"  injected faults   : {sc['injected']['caught']}/{sc['injected']['planted']} caught")
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
        "--inject-fault", action="store_true",
        help="Plant one unsupported number in each player's first draft, to prove the verifier and gates react.",
    )
    for name, gate in GATES.items():
        parser.add_argument(
            gate.flag, dest=f"gate_{name}", type=float, metavar="RATE",
            help=f"CI gate: exit 1 if the {name} rate exceeds RATE (needs ANTHROPIC_API_KEY).",
        )
    args = parser.parse_args(argv)

    limits = {name: getattr(args, f"gate_{name}") for name in GATES if getattr(args, f"gate_{name}") is not None}
    if limits and not getattr(settings, "LLM_ENABLED", False):
        flags = " ".join(GATES[name].flag for name in limits)
        print(f"{flags}: the gates need ANTHROPIC_API_KEY; with the LLM off nothing is measured.", file=sys.stderr)
        sys.exit(2)
    mode = narrative_mode()
    if args.inject_fault and mode != "agentic":
        print(f"--inject-fault needs the agentic mode (LLM on, NARRATIVE_USE_TOOLS=true, "
              f"NARRATIVE_TYPED_VERIFY=false); settings select {mode}.", file=sys.stderr)
        sys.exit(2)

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
    scorecard = run_eval(player_ids, k=args.k, judge=judge, workers=args.workers, inject_fault=args.inject_fault)
    runs = scorecard.pop("runs")

    print(json.dumps(scorecard, indent=2) if args.json else format_scorecard(scorecard), flush=True)
    if args.out:
        with open(args.out, "w") as fh:
            json.dump({"scorecard": scorecard, "runs": runs}, fh, indent=2)

    failures = gate_failures(scorecard, limits)
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
