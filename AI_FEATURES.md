# AI Features: A Grounded Narrative Agent

This document describes the LLM features built on top of the Career Arc Visualizer.
They share one design constraint, and everything else follows from it:

> **Never show a number that doesn't trace back to the player's real data.**

The project's whole premise is that a data tool that fabricates data isn't a data
tool. An LLM is the most natural way to violate that — so the interesting work
wasn't calling a model, it was building the machinery that keeps a generative
feature honest.

---

## The feature

Each player profile has a short "scouting report" — two or three sentences
summarizing a career — written by an LLM agent from that player's actual
statistics. A tool-using agent gathers the facts, drafts the summary, and the
output is verified number-by-number against the data before it's ever shown. If
verification fails and can't be repaired, the system falls back to a
deterministic template. With no API key configured, it serves the template and
nothing breaks.

The same retrieval layer also powers inline "what does this mean?" explainers on
metrics like WAR, OPS+, and ERA+.

---

## The five pieces

### 1. Grounded generation + verification

`build_facts` assembles the only data the model is allowed to see — career
totals, a season log, awards, comps. `verify_numbers` then extracts every
numeric token from the generated text and checks each against the set of numbers
that data permits (exact for integers, rounding-aware for rate stats, years
constrained to the player's active span). Any unsupported number is rejected.

This is the centerpiece. It's a deterministic grader, so it doubles as the
headline metric in the eval suite (below) — no LLM judge required to answer "is
this hallucinating?"

`render_template` is the floor: a deterministic, prose summary built straight
from the facts, correct by construction, used whenever the LLM is disabled,
errors, or can't pass verification.

### 2. Tool calls (function calling)

Rather than stuffing every fact into the prompt, the agent **requests** what it
needs through typed tools: `get_career_totals`, `get_season_log`, `get_awards`,
`get_similar_players`. The model identifies a player; the executor resolves and
validates it. The model never sees a query language and can't touch anything but
these typed shapes — the clean answer to "how do you stop a prompt-injected
database query?" The narrative is then verified against the union of data the
tools *actually returned*, so a stat the agent never retrieved gets flagged.

### 3. Retrieval / RAG

The methodology documentation (~10 articles) is chunked, embedded with Voyage,
and stored in **pgvector** on the existing Postgres. A `search_methodology` tool
does cosine-distance KNN over the chunks, so the agent can describe a metric in
the project's own words, and the UI can surface contextual explanations.

A deliberate decision worth flagging: at this corpus size exact KNN is instant,
so there's **no ANN (HNSW/IVFFlat) index** — that only earns its keep past tens
of thousands of rows. Knowing when *not* to reach for the heavier tool is part
of the point.

### 4. Agentic orchestration

The agent runs a bounded **plan → gather → draft → verify → repair** loop. On a
verification failure, the flagged numbers are fed back to the model for revision
(it may call more tools to get the figure it needs) before the system gives up
and falls back. Hard caps bound model calls and tool calls per narrative. Every
result carries a `trace` — tools called, model calls, repairs, token usage,
verification outcome — which is both logged and surfaced in the UI.

### 5. Evaluation

`pipeline/eval_narrative.py` scores the agent over a fixed sample:

- **hallucination rate** — fraction of generations the verifier rejected
  (deterministic; the headline safety metric)
- **tool-selection accuracy** — did the agent call the tools it should have?
- **RAG hit-rate@k** — does the expected doc land in the top-k for labeled
  questions?
- **faithfulness** — optional LLM-as-judge score

The metric functions are pure and take injected callables, so the suite runs
offline; the CLI has a `--max-hallucination` flag to act as a CI gate.

---

## Engineering notes

- **Stack:** Anthropic Claude (Haiku 4.5) for generation, Voyage
  (`voyage-3.5-lite`, 1024-dim) for embeddings, pgvector for storage, Django/DRF
  + PostgreSQL on the backend, React/TypeScript on the frontend.
- **Cost & latency:** generation is several model round-trips (~$0.006/player on
  Haiku). Results are persisted in Postgres (`PlayerNarrative`) keyed by a data
  version, so the cost is paid once per player per data refresh, not per page
  view — and the version key invalidates automatically when data is re-ingested.
  A `pregenerate_narratives` command pre-bakes profiles so they load instantly.
- **Graceful degradation:** every external dependency is optional. No Anthropic
  key → template narrative. No Voyage key → empty search. Both seams are
  mockable, so the full test suite (116 tests) runs with no keys and no network.
- **Prompt caching** is applied to the system prompt / tool definitions, which
  matters most in the multi-turn agent loop.

---

## Honest limitations

- "Grounded" means *faithful to our database*, not *correct against the world*.
  If our stored All-Star count for a player differs from Baseball Reference, the
  summary will faithfully use ours. The guarantee `verify_numbers` enforces is
  traceability, not external truth.
- A ~10-document corpus doesn't strictly *need* a vector database; pgvector was
  chosen because it's the pattern that scales and reuses existing infrastructure,
  and because it makes retrieval metrics measurable. At much smaller scale,
  in-memory cosine or keyword search would be the right call.
- The verifier is intentionally strict and the prompt forbids approximations, so
  legitimate phrasings like "over 700 home runs" are rejected rather than risk a
  fabricated figure. That's the tradeoff: a slightly stiffer voice in exchange
  for a hard guarantee.

---

## Where the code lives

| Concern | File |
|---|---|
| Fact assembly, verification, template, agent loop | `players/narrative.py` |
| Function-calling tools | `players/narrative_tools.py` |
| Mockable Anthropic seam (prompt caching) | `players/llm.py` |
| Retrieval (pgvector cosine KNN, cached) | `players/rag.py` |
| Mockable Voyage embedding seam | `players/embeddings.py` |
| Persistence + corpus models | `players/models.py` (`PlayerNarrative`, `MethodologyChunk`) |
| Indexing / pre-generation commands | `players/management/commands/` |
| Eval harness | `pipeline/eval_narrative.py` |
| UI: narrative panel + agent trace | `frontend/src/components/profile/panels/NarrativePanel.tsx` |
| UI: RAG-backed metric explainers | `frontend/src/components/MetricExplainer.tsx` |

To run the live paths locally: set `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` in a
`.env`, then `python manage.py index_methodology`. Without keys, the features
degrade to the deterministic template and empty search.
