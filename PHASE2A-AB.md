# Phase 2a A/B — does semantic chunking improve retrieval?

**Run:** 2026-09-24. Pool: Berakhot 2a-17b. 844 segments vs 209 sugya chunks
(full partition, 0 segments uncovered). 126 queries, 99 Mishneh Torah.
Script: `run_ab.py`.

**Gate (pre-registered in `PLAN.md` §8):** if the A/B does not move MRR and R@1,
abandon semantic chunking and keep segments.

## The confound, and how it was controlled

Chunking shrinks the candidate pool 844 → 209. Retrieving from a pool a quarter
the size mechanically improves MRR and R@10 with no change in model quality.
Control: **matched-fraction recall** — top 1% of pool either way (8 segments vs
2 chunks). Also roughly matched by text volume, since a chunk holds ~4 segments.

## Results — Mishneh Torah, n=99

| Condition | pool | MRR | R@1 | R@10 | **R@1%** |
|---|---:|---:|---:|---:|---:|
| A. Segments, bm25 | 844 | 0.580 | 0.465 | 0.788 | **0.747** |
| A. Segments, dense | 844 | 0.527 | 0.394 | 0.818 | **0.818** |
| B. Chunks body, bm25 | 209 | 0.683 | 0.566 | 0.919 | **0.677** |
| B. Chunks body, dense | 209 | 0.587 | 0.444 | 0.838 | **0.596** |
| C. Chunks+heading, bm25 | 209 | 0.681 | 0.556 | 0.919 | 0.687 |
| C. Chunks+heading, dense | 209 | 0.595 | 0.444 | 0.838 | **0.646** |
| D. Heading only, dense | 209 | 0.415 | 0.283 | 0.707 | 0.384 |

## Verdict: chunking does NOT improve retrieval

Raw MRR rose 0.580 → 0.683 and R@10 0.788 → 0.919. **Every point of that is the
pool-shrinkage artifact.** Under matched-fraction retrieval chunking is *worse*:
dense R@1% falls 0.818 → 0.646, BM25 0.747 → 0.687.

Uncontrolled, this experiment would have reported a 10-point MRR gain and written
semantic chunking into the pipeline. The confound did not merely inflate the
result — **it reversed its sign.**

**Mechanism: dilution.** A chunk containing the gold segment also contains three
or four others; the embedding averages toward their mean and the gold signal is
attenuated. This is the precision cost of context, and it is real.

Per the pre-registered gate: **semantic chunking is not adopted as the retrieval
unit.**

## Two results worth keeping

**1. Headings help dense retrieval, slightly.** B vs C share a pool, so this
comparison has no confound at all. Dense R@1% 0.596 → 0.646, MRR 0.587 → 0.595.
BM25 unchanged (it cannot use context it can only lexically match). Small,
positive, free.

**2. Condition D empirically disproves heading leakage.** Heading-only retrieval
scores MRR 0.415 against 0.595 for heading+body. Had the agents encoded the
answer in the headings, heading-alone would have been excellent. It is
substantially worse than the text itself. This is stronger evidence than the
regex check — a behavioural test, not a string match. **Keep condition D in the
harness permanently** as the leakage detector for any future context-generation.

## The objection, preserved

The metric assumes **segment-level precision** is the goal, because `ein mishpat`
links point at specific segments. Semantic chunking rejects that premise: it
argues the right unit is the argument. The evaluation therefore encodes the very
assumption the design disputes, and scores it as a loss.

Both positions are defensible. For a user asking "where does this ruling come
from", returning the whole sugya is arguably the better answer even where the
segment-level metric punishes it.

**Resolution — retrieve narrow, present wide.** Keep the **segment** as the
retrieval and indexing unit; use the sugya chunk as the **display and context
unit**. Retrieve the segment, return the enclosing sugya with its heading. This
takes the precision of fine granularity and the readability of coarse, and the
chunking work is used rather than discarded.

**Practical difference (mai nafka minah):** the index is built over 81,481
segments, not ~20,000 sugyot; chunk boundaries live in a metadata table mapping
segment → sugya; and the `continues_previous` cross-daf fix still matters, but
for presentation rather than embedding — so its cost/benefit changes and the
full 5,349-amud agent run is no longer on the critical path.

## Caveats

- One tractate, 99 MT queries. Directionally clear, not conclusive.
- Restricting the pool to 16 dapim inflates all absolute numbers; only the
  between-condition comparison is meaningful.
- Chunks came from the *original* (defective) prompt for 7 of 8 batches.
  The corrected prompt produces 23% fewer, larger chunks — which on the dilution
  mechanism would make chunking score **worse**, not better.
