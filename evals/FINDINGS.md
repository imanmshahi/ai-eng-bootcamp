# Findings register

Defects and gaps found while building the Week 2 RAG API and the Watchbird agent.
Per-question evidence for F1–F3 lives in `evals/golden_v0.jsonl` (before/after rows).

> Numbering note: F4 and F5 were assigned by Iman. F1–F3 are recorded here in the order they
> were first reported; correct the numbering if the working register differs.

| ID | Finding | Status |
| --- | --- | --- |
| F1 | Retrieval miss at k=3 | FIXED (k=5 mitigation Oct 18; root-cause line-boundary chunking fix Oct 25) |
| F2 | Refusal not detected when hedged | FIXED |
| F3 | Uncited chunk ID in answer prose | OPEN |
| F4 | `stage` off-schema / unconstrained | FIXED |
| F5 | Interim stage enum does not match the capstone Ping schema | OPEN |
| F6 | Startup corpus ingest fails per-file while the API reports healthy | FIXED |
| F7 | Check recall is wording-dependent — a reworded concession made a regression look like an improvement | FIXED |
| F8 | Chunking fix narrowed q13 from a partial answer to a clean refusal | OPEN |
| F9 | Memory store falls back to SQLite when DATABASE_URL is unset, with no warning | FIXED |
| F10 | Fuel normalisation folds e-SAF onto SAF, merging two distinct policy levers into one story | OPEN |

---

## F1 — retrieval miss at k=3 — FIXED

`POST /ask` retrieved only the top 3 chunks. For *"What is the minimum share of synthetic
aviation fuel in 2030 and 2031?"* the answering chunk `REFUELEU-ART4#0006` ranked **5th**
(score 0.6623), so it never reached the LLM. The model answered from the 2035 figures instead
and gave a wrong year.

**Root cause.** Two layers. The immediate cause was `k=3`. The underlying cause is that
`chunk_text()` cuts fixed-size character windows, which splits the Annex I list mid-item: chunk
`#0007` begins *"2034 until 31 December 2034 of synthetic aviation fuels;"*, and the header chunk
`#0000` outranks the list chunk on instrument-style queries.

**Fix.** `/ask` raised from `k=3` to `k=5` in `server/openai_client.py`. Cost: tokens per call
rose roughly 50% (754–814 → 1171–1216), because every prompt now carries two more chunks.

**Residual.** Chunking is unchanged, so the ranking weakness remains. It resurfaced in the
Watchbird agent: on one run, three differently-phrased searches all missed `#0006`, and the agent
correctly reported that the corpus did not support the 6% figure — an honest answer, but an
under-informed one. Chunking on line boundaries is the real fix and is not yet done.

**Root cause fixed (2026-10-25).** The residual above — "chunking on line boundaries is the real
fix and is not yet done" — is now done. `chunk_text()` packs whole lines up to `chunk_size` and
starts a new chunk rather than cutting a line; a line longer than `chunk_size` still splits into
fixed windows, and overlap is carried as whole trailing lines worth at most `chunk_overlap`
characters. The corpus went from 40 chunks to 48 (RED3 7→8, REFUELEU 8→9, TRADE-BIODIESEL 25→31),
since refusing to cut a line means each chunk ends at the last line that fits.

Measured on the 20-question set with the answer path unchanged: over-refusal fell from
**4/14 (28.6%)** to **1/14 (7.1%)**, `declined_despite_retrieval` from 2 failures to 0, and the
three other checks held. q09 now returns the TARIC code `89FQ` and q11 returns `21.7%` — the two
facts that were in the corpus but unreachable. Total tokens *fell* 13% (23,999 → 20,841), because
line-packed chunks end early and five of them is less context than before. q14 remains the one
over-refusal, and is a retrieval miss on a two-part cross-document question rather than a chunking
problem. One regression: see F8.

## F2 — refusal not detected when hedged — FIXED

`refused` was computed as `answer == _REFUSAL`, so it only fired when the fixed refusal sentence
was the *entire* answer. The model instead speculated for a paragraph and then closed with the
refusal sentence. Result: `refused: false`, `confidence: 0.85`, `citations: []` — a confident,
uncited, unsupported answer that reported itself as successful.

**Fix.** `_contains_refusal()` in `server/openai_client.py` looks for the sentence anywhere in the
answer, normalising whitespace and curly apostrophes first — the model mixes `'` and `’`, and it
used a curly one in the very answer that slipped through, so a plain substring test would have
missed it.

**Worth asserting in tests.** `citations == []` together with `refused == false` is a contradictory
state and should fail a check on its own.

## F3 — uncited chunk ID in answer prose — OPEN

The answer text for *"What does RED Article 25 require of Member States for transport?"* cited
`[RED3-ART25#0001]`, which was never retrieved (retrieval returned `#0000`, `#0002`, `#0005`).
The `citations` field correctly dropped it, because `_extract_citations()` keeps only IDs that were
actually retrieved — but the invented ID stayed in the prose the user reads.

**Status.** Deliberately not fixed. It did not reproduce on the k=5 rerun (the model cited
`#0000`, which was retrieved), but nothing in the code prevents a recurrence: IDs in the prose are
never validated against what was retrieved.

**Detection.** The Watchbird run script flags bracketed IDs that appear in the prose but not in
`citations`, so a recurrence is caught automatically.

**Candidate fix.** Validate bracketed IDs in the prose against the retrieved set and either strip
or flag the unknown ones before returning the answer.

## F4 — `stage` off-schema / unconstrained — FIXED

The agent returned free-text `stage` values instead of a constrained set.

**Evidence — three-run instability.** The field was not merely off-vocabulary, it was unstable
run to run. The same two items, same code, same corpus, three consecutive runs:

| Item | Run 1 | Run 2 | Run 3 |
| --- | --- | --- | --- |
| (a) SAF blend 2030 | `"Legislative implementation"` | `"enacted"` | `"in force"` |
| (c) Chinese HVO duties | `"Definitive"` | `"Definitive"` | `"Definitive"` |

Item (a) produced three different strings for one unchanged input. This is why validation was
needed rather than a prompt tweak alone: anything downstream that filters or groups by `stage`
would silently partition the same real-world status across three buckets, and nothing in the
pipeline would report a problem. A prompt instruction alone cannot be verified at runtime; a
schema can.

Note also that there was **no schema to violate** at the time. The agent had no Pydantic model,
no `Literal`, no `output_schema` — the output shape existed only as prose in the instruction. So
the defect was an absent constraint, not a broken one.

**Fix.** In `agent/watchbird_agent.py`:
- a `Ping` Pydantic model with `stage: Optional[Stage]`, `Stage` being a six-value `Literal`;
- rule 7 in the instruction enumerating the six values with a gloss each, and when to use `null`;
- `validate_ping()` plus a `CHECK:` step printed after every run, so drift is loud, not silent;
- `WATCHBIRD_OUTPUT_SCHEMA=1` to switch enforcement to ADK's `output_schema`.

**Verified.** The validator rejects all three strings in the table above and accepts the
on-schema values and `null`. All three test items pass validation in both enforcement modes
(`in_force`, `null`, `definitive`).

**Trade-off measured, not assumed.** ADK supports `output_schema` alongside `tools` — tools stay
available during the thought loop, structure is enforced only on the final reply — so the `THINK:`
narration survives both modes. The real cost of `output_schema` is that on triaged-out items the
model emits only minimal fields, leaving `why_it_matters` empty (reproduced twice). Mode 0
(instruction + post-hoc validation) is therefore the default.

## F5 — interim stage enum does not match the capstone Ping schema — OPEN

The six-value `Stage` enum now in `agent/watchbird_agent.py` is **interim**. It was chosen to close
F4 and covers only what the three documents in this corpus require. It is **not** the capstone
Ping schema, which has ten values:

```
rumour, leaked_draft, proposal, trilogue, adopted, transposed,
investigation_opened, provisional_duties, definitive_duties, review
```

**The two do not line up.**

| Capstone value | Interim equivalent |
| --- | --- |
| `rumour` | none |
| `leaked_draft` | none |
| `proposal` | `proposed` (different spelling) |
| `trilogue` | none |
| `adopted` | none — closest is `in_force`, which is not the same thing |
| `transposed` | none |
| `investigation_opened` | none |
| `provisional_duties` | `provisional` (different name) |
| `definitive_duties` | `definitive` (different name) |
| `review` | none |

Three interim values have no capstone counterpart at all: `in_force`, `amended`, `expired`.

**Consequence.** Any `stage` this agent emits must be mapped before it can feed the capstone
pipeline, and the gaps are not merely cosmetic — the interim list cannot represent the early
stages (`rumour`, `leaked_draft`, `trilogue`) that a watch tool exists to catch, nor
`transposed`/`review`. Treating the two as interchangeable would silently lose those states.

**Not yet decided.** Whether to adopt the capstone's ten values directly in the agent, or keep a
narrow enum plus an explicit mapping layer. Adopting the ten values appeared to mean the agent
could emit stages the current corpus holds no evidence for, which would conflict with the
grounding rule — the corpus has no text about rumours or leaked drafts. That apparent tension is
resolved below.

**Resolution for the design tension:** stage describes the NEWS ITEM's position in the pipeline,
not the corpus. Only why_it_matters needs corpus grounding. So adopting all 10 capstone values
does not conflict with the grounding rule.

## F6 — startup corpus ingest fails per-file while the API reports healthy — FIXED

On a routine restart (2026-10-24) `load_corpus()` hit an `openai.APITimeoutError` embedding
`REFUELEU-ART4.txt`. It logged `ERROR … skipping`, carried on, and finished with
`2 loaded, 1 failed, 32 total chunks in store`. `GET /health` returned `{"status": "ok"}`.

**Why that is worse than a crash.** The store held 32 of 40 chunks and *all* aviation content was
missing — every `REFUELEU-ART4` chunk. So every ReFuelEU question would retrieve only RED and
biodiesel text and refuse, correctly describing a corpus that was wrong. The refusals would read
exactly like the legitimate ones in q16–q18: same fixed sentence, same empty `citations`,
same `refused: true`. Nothing in the response, the trace, or `/health` distinguished "not in the
corpus" from "failed to load this morning". An eval run against that process would have scored
the aviation questions as correct refusals and recorded a clean result.

**Third instance of the same pattern** — a failure that reports itself as success:

| | Failure | Reported as |
| --- | --- | --- |
| F2 | Model speculated, then appended the refusal sentence | `refused: false`, `confidence: 0.85`, `citations: []` |
| F4 | `stage` drifted across three values for one unchanged input | A valid-looking string every time, no error |
| F6 | One of three corpus documents never loaded | `{"status": "ok"}` |

The shared shape: the component that knows something went wrong is not the component that
reports status. F2 was fixed by making the detector look at the whole answer, F4 by adding a
schema and a post-run `CHECK:` line, F6 by making `/health` report what it actually has.

**Fix.** In `server/main.py`:
- `CORPUS_LOAD_ATTEMPTS = 3` — each file is retried twice before it is given up on, since the
  observed failure was a transient embedding timeout, not a bad file. A recovery logs
  `on attempt N` so retries stay visible rather than hidden.
- `_corpus_status` records `expected_documents`, `documents_loaded`, `chunks_total` and
  `failed_documents` at startup.
- `GET /health` returns those counts and reports `"status": "degraded"` plus a
  `failed_documents` list when any file failed. Still no OpenAI call — it reads the startup
  result only, so it stays a cheap heartbeat.
- `chunks_total` comes from a new read-only `store_chunk_count()` in `server/rag.py` rather than
  from the last ingest response, which went stale whenever the final file was the one that failed.

Nothing in the answer path changed.

**Verified.** Two cases with `run_ingest` stubbed: a document failing twice then succeeding loads
on attempt 3 and `/health` stays `ok` (3 documents, 40 chunks); a document failing all three
attempts yields `{"status": "degraded", "documents_loaded": 2, "chunks_total": 32,
"expected_documents": 3, "failed_documents": ["REFUELEU-ART4"]}`. Live restart with all three
documents loading returns:

```json
{"status": "ok", "documents_loaded": 3, "chunks_total": 40, "expected_documents": 3}
```

**Residual.** Retries are immediate, with no backoff — fine for a one-off timeout, not for a
rate-limited or partial outage. The store is still process-memory, so a Render sleep or redeploy
re-runs the whole load and the same risk recurs on every cold start; `/health` now tells you when
it has, but nothing re-attempts a failed document after startup. A `POST /ingest` of the missing
file repairs it by hand, which is how this instance was recovered.

## F7 — check recall is wording-dependent — FIXED

`check_declined_despite_retrieval` in `evals/checks.py` detected hedged declines by testing the
answer against a literal tuple of phrases: `"not detailed"`, `"not explicitly"`,
`"not specified"`, and so on.

**How it failed.** Between the v1 and v2 trace runs, q12 reworded its concession from "not
detailed in the provided context" to "not fully **described** in the provided context". Same
concession, same defect, one different word — and `"not fully described"` was not in the tuple.
The check stopped seeing it and q12 flipped from FAIL to PASS.

**What that did to the result.** The reported before/after for the v2 prompt experiment was
`2 → 3` failures, which read as "q12 improved, q11 and q14 newly flagged" — a mixed result. The
actual figure was `2 → 4`: q12 never improved, and the prompt change made things strictly worse.
The experiment was already being reverted for other reasons (a new `refused=True`-with-citations
contradiction on q14, +6.9% tokens, identical 8/20 declines), so the wrong number did not change
the decision — but it was one trace away from arguing the opposite case.

**Why this one is worse than a false negative.** The error was not random, it was *flattering*. A
model under pressure to concede less bluntly reaches for softer wording, so the phrases that drift
first are exactly the ones a literal matcher is watching. The check therefore degrades precisely
when the output is changing — the only time anyone reads it — and it degrades in the direction of
reporting improvement. A measurement that silently becomes more generous as the thing it measures
changes is not a measurement.

**Fourth instance of the 'fails as success' pattern** (see F2, F4, F6), and the first in the
measurement layer rather than the product. The earlier three were the system reporting success
while failing; this is the *eval harness* reporting success while failing, which is the one that
hides the other three. Extending F6's table:

| | Failure | Reported as |
| --- | --- | --- |
| F2 | Model speculated, then appended the refusal sentence | `refused: false`, `confidence: 0.85`, `citations: []` |
| F4 | `stage` drifted across three values for one unchanged input | A valid-looking string every time, no error |
| F6 | One of three corpus documents never loaded | `{"status": "ok"}` |
| F7 | A hedge the check was built to catch, reworded | `PASS`, and a regression scored as an improvement |

**Fix.** `_HEDGE_PHRASES` is replaced by `_HEDGE`, a regex matching the concession *shape* rather
than specific phrases: a negated verb of stating or covering with an optional adverb
(`not [adverb] stated|specified|detailed|described|covered|…`), plus `does not <verb>`,
`cannot (fully) answer`, `no specific`, and `un/not clear from`. A new `hedges_in()` returns the
matched text, so a failure reason now quotes the model's own words instead of a canned phrase —
q14's v2 reason reads `hedged (does not provide, cannot answer, not detailed, not covered, not
explicitly detailed)`. Both call sites (`check_declined_despite_retrieval` and the `declined()`
helper behind `check_over_refusal`) use it, so the over-refusal rate inherits the fix.

**Verified.** 12 rewordings of the same concession are pinned as tests, including the
`"not fully described"` form that slipped through and the `"I cannot fully answer"` form that
appeared in v2's q11. Five ordinary answers are pinned as negative cases, so the broader pattern
does not start firing on text that merely contains "not" or a listed verb — "is **not** blended
beyond the **stated** share" must stay a pass. 60 tests in `evals/test_checks.py`, all passing.
Re-running both trace files with the repaired check left v1 unchanged at 2 failures (its wording
was always covered) and corrected v2 to 4.

**Residual.** The matcher is still English-specific and still a regex over prose; a concession
phrased without a negated verb ("the excerpts stop short of giving a figure") would pass. The
structural checks are the robust ones — `check_citations_were_retrieved` keys on whether an ID was
retrieved, which no rewording can evade — and the lesson generalises: prefer a check that keys on
structure over one that keys on wording, and when wording is unavoidable, pin the paraphrases.

## F8 — chunking fix narrowed q13 from a partial answer to a clean refusal — OPEN

The line-boundary chunking fix (F1) improved four traces and cost one. q13 asks two things:
*"Are sustainable aviation fuels excluded from the Chinese biodiesel anti-dumping duties, and what
SAF share does ReFuelEU Aviation require from 2030?"*

| | v1 (40 chunks) | v3 (48 chunks) |
| --- | --- | --- |
| Answer | Biodiesel half answered from `TRADE-BIODIESEL#0006`, then *"the specific percentage for that period is not detailed"* on the aviation half | The fixed refusal sentence, nothing else |
| `citations` | 2 | 0 |
| `refused` | false | true |
| Retrieved | `REFUELEU#0000`, `TRADE#0007`, `REFUELEU#0007`, `TRADE#0009`, `TRADE#0006` | `TRADE#0010`, `REFUELEU#0000`, `REFUELEU#0008`, `REFUELEU#0005`, `REFUELEU#0001` |

v1 gave half an answer plus an honest hedge. v3 gives nothing. Material for the biodiesel half was
retrieved in both runs — `TRADE-BIODIESEL#0010` in v3 is the re-chunked equivalent of the exclusion
text — so the model had something to say and did not say it.

**Why it is not in the headline number.** q13 is labelled `answerable=Partly`, and
`check_over_refusal` does not score Partly: a partial decline there may be correct, and deciding
needs to know *which* part was declined. So the 28.6% → 7.1% improvement is real and this loss sits
outside it. That is the honest accounting, but it also means **the metric is blind to exactly this
failure**, which is the more useful observation. A rate that cannot see breadth loss will happily
report progress while answers get narrower.

**Not a chunking defect as such.** Nothing about packing lines should make a model decline. The
likely mechanism is that re-chunking changed which text landed in the top 5 and how it was framed:
v3 retrieved four ReFuelEU chunks and one biodiesel chunk, against v1's three-to-two split, so the
context reads as mostly-aviation for a question whose answerable half is the biodiesel one. That is
a ranking consequence of chunk boundaries moving, not of the boundaries being wrong.

**Candidate next steps, none taken yet.**
- Label the failure mode for q13 on the labelling page, and consider whether `answerable=Partly`
  deserves to be scored once there is a convention for which part was expected.
- Add a breadth measure the headline cannot hide: citations per answerable trace, or a count of
  answered-parts on the multi-part questions (q12–q15), so a narrowing shows up as a number.
- Re-check after any retrieval change; this may move on its own, which is itself worth knowing.

**Do not fix by prompt.** The v2 experiment (see the appendix in `evals/TAXONOMY.md`) tried exactly
that — instructing the model to answer every supported part — and produced no net change plus a new
`refused=True`-with-citations contradiction. A breadth problem detected by one trace is not yet
evidence for a prompt rewrite.

## F9 — memory store falls back to SQLite when DATABASE_URL is unset, with no warning — FIXED

`server/memory.py` resolved its connection URL as `os.getenv("DATABASE_URL") or
"sqlite:///./watchbird.db"`. The fallback is deliberate — the API should run with nothing
configured — but it was silent, and silence is the defect.

**What that would have cost.** Watchbird's memory exists to answer *"what is new versus before"*,
which requires a store that outlives a process. With `DATABASE_URL` unset, the store is a file in
the container filesystem, and Render's free web service has no persistent disk: every restart,
every redeploy, every wake from sleep begins with an empty database. The failure is invisible in
exactly the way that matters most — `POST /ping` keeps returning *"First time this story has
appeared."* forever, which is a well-formed, plausible answer. The planned local durability proof
(write a story, kill the process, start fresh, show recall) would have **passed**, because SQLite
on a laptop genuinely is durable. The same code on Render would lose every story and report
nothing wrong.

**Fifth instance of the 'fails as success' pattern** (see F2, F4, F6, F7):

| | Failure | Reported as |
| --- | --- | --- |
| F2 | Model speculated, then appended the refusal sentence | `refused: false`, `confidence: 0.85`, `citations: []` |
| F4 | `stage` drifted across three values for one unchanged input | A valid-looking string every time, no error |
| F6 | One of three corpus documents never loaded | `{"status": "ok"}` |
| F7 | A hedge the check was built to catch, reworded | `PASS`, and a regression scored as an improvement |
| F9 | Memory store not durable; every ping is a first sighting | `"First time this story has appeared."` |

Worth noticing what these five have in common beyond the slogan: each failure produced output that
was *well-formed*. No exception, no empty field, no malformed value — a schema check would pass all
five. What they lack is a statement of what the component actually has: F6 needed `/health` to
report its chunk count, F9 needs it to report its backend. **Confidence is not a substitute for
provenance**, and the fix in every case was to make the component declare its own state rather than
to make it try harder.

**Fix.** In `server/memory.py`:
- `warn_if_unconfigured()` logs a `WARNING` naming the resolved SQLite path, saying plainly that it
  is not durable on Render, and giving the two ways to configure it. It returns whether it fired,
  so it is testable. When `DATABASE_URL` *is* set it logs an `INFO` line instead, so the backend
  appears in the log either way.
- `backend()` returns `"sqlite"` or `"postgres"`, normalising both the `postgresql://` and
  `postgresql+psycopg://` forms.

In `server/main.py`:
- the lifespan calls `warn_if_unconfigured()` before `load_corpus()`, so the warning sits near the
  top of the startup output rather than buried under ingest logs;
- `GET /health` now returns `"memory_backend": "sqlite" | "postgres"`.

**Verified.** Both branches tested: unset gives `warning fired: True` and `backend() == "sqlite"`;
set gives `False` and `"postgres"`, for both URL schemes. Live restart logs the warning as the third
line of startup, and `/health` returns:

```json
{"status": "ok", "memory_backend": "sqlite", "documents_loaded": 3,
 "chunks_total": 48, "expected_documents": 3}
```

**Residual.** `/health` reports which backend is configured, not whether it is reachable — a wrong
Postgres URL would still read `"memory_backend": "postgres"` until something tried to connect. A
connectivity probe belongs with the store itself, which is not built yet. Note also that
`memory_backend: "sqlite"` is correct and harmless locally; it is only a problem on Render, and
nothing yet distinguishes the two environments automatically.

## F10 — fuel normalisation folds e-SAF onto SAF, merging two policy levers — OPEN

Fuel normalisation folds e-SAF onto SAF, so a story about the ReFuelEU synthetic sub-target
shares a `story_key` with one about headline SAF shares. Under ReFuelEU these are distinct policy
levers with different economics. Fix is a `sub_target` value in the `eu_channel` enum, deferred
because it is a schema change.

**Where.** `CANONICAL_FUELS` in `server/memory.py`. The first group maps `saf`,
`sustainable aviation fuel`, `synthetic aviation fuel`, `e-SAF`, `RFNBO-derived jet`,
`power-to-liquid jet` and `e-kerosene` all onto the single token `saf`, and `story_key()` is built
from those canonical tokens.

**Why the fold was introduced.** It fixed a worse problem. On 2026-10-27 the two-session recall
test posted a draft-stage SAF item and then a later in-force one. The classifier returned
`["SAF", "synthetic aviation fuel"]` for the first and `["SAF"]` for the second — the umbrella
plus the sub-kind, then the umbrella alone. The two fuel sets differed, so the `story_key` differed,
so the exact-key lookup missed. Recall survived only because the embedding fallback matched at
**0.854663**, four thousandths above `SAME_STORY_COSINE = 0.85`, a threshold that is itself
unvalidated. Cross-session memory was resting on a constant nobody has measured.

Folding synonyms alone would not have fixed it: the miss was a difference of *granularity*, not of
naming. `{saf, e-saf}` and `{saf}` are still two different sets. Only folding the sub-kinds onto
the umbrella makes the two items key identically, which it now does — the same re-run matches on
`matched_by: "key"` with `match_score: 1.0`.

**What it costs.** Identity can no longer distinguish the two instruments ReFuelEU actually
creates. Article 4(1) sets a minimum SAF share *and*, separately, a minimum synthetic aviation fuel
sub-share, with its own averaging periods over 2030–2031 and 2032–2034. Those are different
obligations with different compliance economics and different supply constraints, and a watch tool
exists partly to tell them apart. After the fold:

- an item about the synthetic sub-target and an item about headline SAF shares land on one row;
- `latest_stage` and `stages_seen` describe whichever arrived last, so a sub-target moving from
  `proposed` to `in_force` is indistinguishable from the headline share doing so;
- `whats_new_vs_before` can therefore report a stage move on the wrong lever.

The raw classifier words are still stored in the `fuels` column, so the distinction is *readable*
in the row. It is not *separable*: nothing keys on it, nothing queries it, and no stage history is
kept per lever.

**Fix, deferred.** Add `sub_target` to `EU_CHANNELS` and have the classifier choose it when the
item is about a sub-share rather than a headline share. That splits the two back into separate
stories without reintroducing the granularity problem, because the split then lives in the channel
rather than in the fuel set. Deferred because it is a schema change: `EU_CHANNELS` is a closed list
that `story_key()` is built from, so adding a value re-keys existing rows and needs a one-off
migration, and the classifier prompt needs a rule for choosing between `mandate` and `sub_target`
that is itself worth testing.

**Not the same as F5.** F5 is about `stage` — the pipeline position a news item has reached. F10 is
about *which obligation* the item concerns. Both are cases of a closed list being too coarse for
the domain, and both would be caught by the same kind of labelled set: pairs of items that should
and should not share a story.

**How this one announces itself.** Unlike F2/F4/F6/F7/F9, this finding is not a failure reporting
itself as a success — it is a deliberate trade made with its cost written down. The thing that
would make it dangerous is silence: a merged story looks exactly like a correctly recalled one in
the response, the row and the log. That is why the fold is commented at `CANONICAL_FUELS` and
recorded here, rather than left to be rediscovered from a confusing `whats_new_vs_before`.
