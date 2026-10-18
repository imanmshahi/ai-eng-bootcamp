# Findings register

Defects and gaps found while building the Week 2 RAG API and the Watchbird agent.
Per-question evidence for F1–F3 lives in `evals/golden_v0.jsonl` (before/after rows).

> Numbering note: F4 and F5 were assigned by Iman. F1–F3 are recorded here in the order they
> were first reported; correct the numbering if the working register differs.

| ID | Finding | Status |
| --- | --- | --- |
| F1 | Retrieval miss at k=3 | FIXED |
| F2 | Refusal not detected when hedged | FIXED |
| F3 | Uncited chunk ID in answer prose | OPEN |
| F4 | `stage` off-schema / unconstrained | FIXED |
| F5 | Interim stage enum does not match the capstone Ping schema | OPEN |

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
narrow enum plus an explicit mapping layer. Adopting the ten values means the agent can emit
stages the current corpus holds no evidence for, which conflicts with the grounding rule — the
corpus has no text about rumours or leaked drafts. That tension needs resolving before the enums
are merged.
