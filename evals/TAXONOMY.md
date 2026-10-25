# Failure taxonomy — v1

Five categories for the failure modes visible in `evals/traces_v1.jsonl` (20 traces, k=5,
corpus = RED3-ART25, REFUELEU-ART4, TRADE-BIODIESEL).

This sits alongside `evals/FINDINGS.md`: findings (F1–F5) are *defects in the code*, categories
(C1–C5) are *classes of wrong output*. One finding can cause several categories, and one category
can survive after every known finding is fixed.

**Why any of this matters.** Watchbird is a false-ping tool: it watches regulatory and trade news
and pings a human only when something real has moved. Its value is the ratio of true pings to
total pings. Every category below is scored by what it does to that ratio — a wrong ping that
costs an analyst an hour, or a silent miss that defeats the point of a watch tool.

Chunk-location claims below were verified by re-chunking `corpus/` with the server's own
`chunk_text()` at the live 800/100 settings and searching the result, not inferred from the
answers.

---

## C1 — retrieval-miss-tabular

**Definition.** The answer exists in the corpus but in a *tabular or annex-style* chunk — a long
list of `Name | value | code` rows, or an Annex of numeric shares — and that chunk either never
reaches the top-k or ranks below prose chunks that merely describe the table. Fixed-size character
chunking splits such tables mid-row and leaves the column header stranded in an earlier chunk, so
a row like `Tangshan Jinlihai Biodiesel Co., Ltd | 89FQ` carries no text saying what `89FQ` is.
The embedding of a headerless row block therefore matches almost nothing a user would type.

**Evidence.**

| Trace | What was asked | Where the answer actually is | What retrieval returned |
| --- | --- | --- | --- |
| q09 | TARIC additional code for Tangshan Jinlihai | `TRADE-BIODIESEL#0024` (`… Jinlihai Biodiesel Co., Ltd \| 89FQ`) | `#0002, #0003, #0001, #0021, #0005` — the answering chunk is absent; `#0021` holds only the Annex *header* |
| q13 | SAF share from 2030 | `REFUELEU-ART4#0006` (`6 %`) | `#0000, TRADE#0007, #0007, TRADE#0009, TRADE#0006` — `#0006` absent, so the model hedged |
| q12 | Synthetic share for 2030–2031 (half of a comparison question) | `REFUELEU-ART4#0006` (`1,2 %` average, `0,7 %` each year) | `RED3#0000, REFUELEU #0000, #0007, #0003, #0001` — `#0006` absent again; the model hedged on the aviation half |
| q14 | Annex I synthetic shares + RNFBO obligation | `REFUELEU-ART4#0006/#0007` and `RED3-ART25#0001–#0004` | `REFUELEU #0000, #0003, #0001, RED3#0000, #0004` — neither answering chunk retrieved; refused |
| q07 | Minimum synthetic share 2030 and 2031 | `REFUELEU-ART4#0006` (`0,7 %`) | `#0007` ranks **1st** (0.7801), the answering `#0006` only 4th (0.6791) |
| q19 | "saf 2030 how much" | `REFUELEU-ART4#0006` | `#0007` 1st again (0.5551), `#0006` 2nd |

q07 and q19 are the F1 residual: raising k to 5 bought enough headroom that the answering chunk
still lands in context, but the ranking defect is unchanged. q09 shows what happens when it
doesn't — the Annex table runs across `#0021`–`#0024` and only the header chunk is retrievable.

**Why it matters for Watchbird.** This is the silent-miss category, and it is aimed squarely at
the data Watchbird is built to watch. Duty rates, TARIC codes and Annex mandate schedules are the
*facts that trigger a ping* — "this producer's rate changed", "this share steps up in 2032". They
live in tables almost without exception. A watch tool that cannot retrieve its own trigger values
produces no ping and no error: it simply reports nothing, indistinguishable from a quiet week.
That is the worst failure a watch tool has, because it is invisible to the user and to the logs.

---

## C2 — under-synthesis

**Definition.** The needed text *was* retrieved and placed in context, and the model still
declined, hedged, or answered only the easier half of a two-part question. Distinct from C1 by
where the fault lies: C1 is retrieval, C2 is the model wasting good retrieval.

**Evidence.**

- **q11 — the clearest instance.** Asked the duty rate for cooperating companies listed in the
  Annex that were not sampled. The row `Other cooperating companies listed in the Annex | 21,7`
  is in `TRADE-BIODIESEL#0004`, which was retrieved at **rank 1** (score 0.5559). The model
  returned the fixed refusal sentence. The answer was in the top chunk of its own context.
- **q13 — hedge on a two-part question.** Answered the biodiesel half from `TRADE-BIODIESEL#0006`,
  then said the 2030 SAF share "is not detailed in the provided context" and jumped to the 2035
  figure. The 2030 figure genuinely was not retrieved (C1), so the hedge is honest — but it
  hedged on one half while answering the other, which is the shape of the defect even when
  retrieval is the root cause.
- **q12 — same hedge, same missing chunk.** Compared the RED transport target against the SAF
  share, answered the RED half from `RED3-ART25#0000`, then conceded the 2030–2031 synthetic
  percentage "is not detailed in the provided excerpts" while citing `REFUELEU-ART4#0001`. The
  figures are in `#0006`, not retrieved. Together with q13 this is the same defect twice, from the
  same absent chunk — these are the two traces the automated checks actually catch.
- **q14 — all-or-nothing refusal.** A two-part question where part of the material (`RED3-ART25#0000`,
  the Article 25 transport obligation) *was* retrieved. The model refused the whole question
  rather than answering the part it could support and declining the rest.

**Why it matters for Watchbird.** Watchbird's output is a judgement — *is this news item a real
move, and why does it matter* — assembled from several corpus facts at once. A model that declines
whenever any one part is thin will refuse most real items, because real news rarely maps onto a
single chunk. Worse, q14 shows the refusal is all-or-nothing: partial grounding yields zero
output rather than a partial ping. That converts a tool that should degrade gracefully into one
that goes silent under exactly the conditions it was built for. It also corrodes trust in the
refusal itself — once an analyst learns that "not in the corpus" sometimes means "it was on the
first line of the context", they stop believing refusals, and the honest ones lose their value.

---

## C3 — citation-mismatch

**Definition.** A chunk ID in the user-visible prose, or in the `citations` field, that was not in
the retrieved set — or a cited ID that was retrieved but does not contain the claim attributed to
it. Either way the citation does not do the one job a citation has: letting a reader check the
claim against the source.

**Evidence.** **No instance in `traces_v1.jsonl`.** Every bracketed ID in every answer appears in
`citations`, and every `citations` entry appears in that trace's retrieved list — checked across
all 20 traces. The category is here on the strength of a prior instance and because nothing in the
code prevents a recurrence:

- **F3 (OPEN)** — the answer prose for a RED Article 25 question cited `[RED3-ART25#0001]`, which
  was never retrieved. `_extract_citations()` correctly dropped it from the `citations` field, so
  the structured output looked clean while the prose the user reads carried an invented ID. IDs in
  the prose are still never validated against what was retrieved.
- **Near-miss worth recording, not a defect:** q08 answers `35.6%` for the Jiaao Group citing
  `TRADE-BIODIESEL#0004`. The corpus writes that figure `35,6` in EU comma-decimal form, in
  `#0004` — so both the number and the citation are correct. The model silently renormalised the
  decimal separator. Correct here, but it means a `%` figure in an answer cannot be matched to the
  source by string equality, which any future citation-content check has to handle.

So C3 is currently a **regression guard**, not an active failure. `check_citations_were_retrieved`
in `evals/checks.py` is that guard, and it fails on the F3 trace shape by construction.

**Why it matters for Watchbird.** A ping's whole claim to an analyst's attention is that it links
to the regulation that moved. A ping citing a chunk that does not exist, or that says something
else, is worse than no ping: the analyst chases a dead reference, and the one unverifiable ping
teaches them to verify every future one by hand — which is the manual work the tool exists to
remove. Note also that F3 was invisible in the structured output while being plainly visible in
the prose, so this class has to be checked on the text a human reads, not only on the JSON field.

---

## C4 — domain-term-confusion

**Definition.** The question uses a term that is adjacent to, but not the same as, something in
the corpus — a sibling instrument, a different jurisdiction, a different transport mode — and the
retrieved chunks contain plausible-looking text about the *neighbour*. The failure mode is
answering about the neighbour as though it were the thing asked about.

**Evidence.** In v1 the model handled all four correctly; the category records the near-misses and
the lures that were present in context.

| Trace | The adjacency | The lure that was retrieved | Outcome |
| --- | --- | --- | --- |
| q17 | FuelEU **Maritime** vs ReFuel**EU Aviation** | `RED3-ART25#0002` — "share of renewable fuels of non-biological origin … maritime transport sector is at least 1,2 %". A real maritime share, in context, next to a maritime question | Correctly refused |
| q16 | **Indonesian** palm oil biodiesel vs **Chinese** biodiesel | `TRADE-BIODIESEL#0000/#0003/#0005` — a complete definitive-duty table, right product, wrong country | Correctly refused |
| q15 | The biodiesel investigation *mentions* RED; the question asks what RED Article 25 requires | Both documents retrieved together | Answered from RED3-ART25 correctly |
| q13 | "SAF excluded from the duties" (scope of an AD measure) vs "SAF share required" (a mandate) — same three letters, opposite kind of obligation | Both senses in context | Kept the two apart |

q17 is the sharpest: a wrong answer there would have cited a real chunk with a real percentage,
and the `citations` field would have looked perfect. No code-based check in `checks.py` catches
this — it needs the human label set.

**Why it matters for Watchbird.** This is the false-ping engine, and the low-carbon fuels domain
is dense with these adjacencies: RED III / ReFuelEU Aviation / FuelEU Maritime / ETS, provisional
vs definitive duties, China vs Indonesia vs Argentina biodiesel, HVO vs FAME vs SAF. A tool that
confuses two of them pings about an obligation that does not apply to the client — the expensive
failure, because the ping is specific, cited, confidently worded and wrong, so it survives review
and reaches a decision. These four traces passing is the single most encouraging signal in v1, and
the least protected: nothing automated is holding it in place.

---

## C5 — ambiguous-question

**Definition.** The question is too underspecified to have one right answer — missing the
instrument, the year, the jurisdiction or the metric — so retrieval has nothing sharp to match and
the model picks an interpretation without flagging that it picked.

**Evidence.**

- **q20 "what about the duties"** — top score **0.3437**, and all five retrieved chunks score
  below 0.35, far under every other trace in the set (the next-lowest top score is q05 at 0.5747).
  The model answered anyway, with a generic paragraph about invoice conditionality citing
  `#0005` and `#0003`, and `refused: false`. Nothing in the output records that the question was
  unanswerable as asked.
- **q19 "saf 2030 how much"** — answered correctly, but the low scores (top 0.5551) and the
  `#0007`-over-`#0006` inversion from C1 both show up here; terse keyword questions degrade
  ranking even when the corpus plainly holds the answer.

The retrieval scores are the usable signal: a top score below roughly 0.45 marks a question that
retrieval could not resolve. This threshold is observed on 20 traces, not calibrated — treat it as
a hypothesis for v2, not a constant to hard-code.

**Why it matters for Watchbird.** Real inputs look like q20, not like q01. Items arrive as
headlines and half-sentences — "new duties on Chinese imports", "SAF mandate tightened" — and the
tool must decide whether that is a ping without a well-formed question to work from. An answer
built on 0.34-similarity chunks is a guess, and v1 presents the guess in the same voice, with the
same citation formatting, as the 0.84-similarity answer in q10. Watchbird needs ambiguity to
surface as a distinct state — ask, or ping with low confidence — and the confidence an analyst
would need in order to triage is exactly what the current output does not carry.

---

## Coverage: which categories the code-based checks can see

`evals/checks.py` runs four checks with no LLM calls. They do not cover the taxonomy evenly, and
the gaps matter more than the coverage.

| Category | Automated check | Coverage |
| --- | --- | --- |
| C1 retrieval-miss-tabular | — | **None.** Needs a gold chunk ID per question; `evals/golden_v0.jsonl` is the start of that |
| C2 under-synthesis | `check_declined_despite_retrieval`, `check_no_uncited_numbers` | Partial — catches hedge phrases, **misses q11**, where the model used the fixed refusal sentence rather than a hedge (see below) |
| C3 citation-mismatch | `check_citations_were_retrieved` | Good for invented IDs; cannot tell whether a cited chunk actually supports the claim |
| C4 domain-term-confusion | — | **None.** Requires knowing the right answer; human labels only |
| C5 ambiguous-question | — | **None.** A retrieval-score floor would catch q20 and is the obvious v2 addition |
| F2 class (refusal/citation contradiction) | `check_refusal_consistency` | Good — the contradictory state is checkable without knowing the answer |

**The q11 gap is deliberate and should be closed in v2.** `check_declined_despite_retrieval` looks
for hedge concessions by shape — a negated verb of stating or covering, e.g. "not detailed", "not
fully described", "does not specify" (see the appendix for why a literal phrase list was not
enough). q11 declined with the *fixed
refusal sentence* instead, so no hedge phrase appears and the check passes it — the single most
clear-cut defect in the trace set is invisible to the check aimed at its category. Widening the
check to treat every refusal-with-5-chunks as a flag would catch q11, but would also flag q16,
q17 and q18, where refusing was correct because the fact is genuinely absent from the corpus. The
distinction cannot be made from the trace alone; it needs a per-question "is this answerable from
this corpus" label. That label set is the real v2 deliverable, and the labelling page is where it
gets built.

---

## Appendix — the v2 prompt experiment (2026-10-19), reverted

`evals/traces_v2.jsonl` and `evals/results_v2.json` are **a dead experiment, not current
behaviour.** The grounding instruction in `server/openai_client.py` was reverted on 2026-10-24 and
the file is byte-identical to the version that produced `traces_v1.jsonl`. Read v2 as evidence
about a hypothesis that failed, and treat v1 as the live baseline.

**The hypothesis.** C2 looked like a refusal-policy problem: the model declined rather than
answering the part of a question the context covered. So the instruction was changed to require
answering every supported part, and to permit the fixed refusal sentence *only* when no chunk
addresses any part of the question. One constant, one change.

**What happened.** Nothing improved and two things got worse.

| Measure | v1 | v2 |
| --- | --- | --- |
| Traces that declined (matched by concession shape, not phrase list) | 8/20 | 8/20 — *the same eight* |
| `declined_despite_retrieval` failures | 2 (q12, q13) | 4 (q11, q12, q13, q14) |
| `refused=True` with a non-empty `citations` (the F2 contradiction) | 0 | **1** (q14) |
| Total tokens across 20 calls | 23,999 | 25,643 (+6.9%) |

q09, q11, q12, q13, q14, q16, q17 and q18 declined in both runs. The instruction changed *how*
the model declined, not *whether* it did: clean refusals became paragraph-long explanations of
why it could not answer, which cost more tokens and read as less honest.

**q11 is the decisive case.** It was the clearest C2 instance — the row
`Other cooperating companies listed in the Annex | 21,7` is in `TRADE-BIODIESEL#0004`, retrieved
at rank 1 in both runs. v1 returned the fixed refusal. v2 returned *"The context does not specify
the duty rate … The only related information mentions that there are cooperating exporting
producers not sampled, but it does not provide specific duty rates for them
[TRADE-BIODIESEL#0021]"* — and never surfaced `21,7`. Note which chunk it cited: `#0021`, the
Annex *header*, not `#0004`, the duty table. The question says "listed in the Annex", so the model
went to the Annex. **The defect is reading a value out of a pipe-delimited table row, not
reluctance to answer partially.** That is C1, and it points at F1's unfinished work — chunking on
line boundaries so a table row keeps its column header — not at the prompt.

**The regression.** q14 began emitting a partial answer *with* a citation and still closed with
the fixed refusal sentence, so `refused=True` while `citations` was non-empty. Instructing the
model to "state plainly which part the context does not cover" invited it to reach for the refusal
sentence mid-answer — reintroducing exactly the shape F2 was fixed to remove.

**A lesson about the checks, not the model.** The first comparison read `2 → 3` and appeared to
show q12 improving. It had not: q12 reworded its hedge from "not detailed" to "not fully
described", and `check_declined_despite_retrieval` matched against a literal phrase list that did
not contain the new wording, so the check stopped seeing a concession that was still there. The
check now matches the concession *shape* — a negated verb of stating or covering, with an optional
adverb — and the corrected numbers are the `2 → 4` in the table above. **A check whose recall
depends on the model's choice of adverb will report improvements that did not happen**, and it
fails in the flattering direction, which is the dangerous one. Generalising the matcher is why
C3's `check_citations_were_retrieved` is worth more than it looks: it keys on structure (an ID
either was or was not retrieved) rather than on wording.
