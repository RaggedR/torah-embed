# Phase 1 — link census

**Run:** 2026-09-24. **Method:** Sefaria `/api/links/<ref>?with_text=0`,
whole-book where the endpoint tolerates it, per-siman for Shulchan Arukh.
1,661 refs cached (736 MB of raw link JSON, in scratch).
**Scripts:** `crawl.py`, `crawl2.py`, `analyse3.py`. **Output:**
`data/gold_pairs.json` (2.9 MB), `data/phase1_counts.json`.

## Answer

The open risk in `PLAN.md` §10 was pair volume — whether enough clean
cross-register pairs exist to move a strong pretrained retriever. **Resolved:
50,214 unique pairs.** That is ample. Build the pipeline.

| Source | Unique pairs | Distinct source segs | Distinct Bavli targets |
|---|---:|---:|---:|
| Mishneh Torah → Bavli | 27,601 | 9,675 | 21,300 |
| Shulchan Arukh → Bavli | 15,860 | 6,968 | 12,494 |
| Mishnah → Bavli | 6,753 | 2,932 | 6,056 |
| **Combined** | **50,214** | — | **27,573** |

All 37 tractates covered; 79 of 88 Mishneh Torah books contribute.

## What carries the signal

The dominant link type is **`ein mishpat / ner mitsvah`** — 25,448 of the
Mishneh Torah pairs and 14,715 of the Shulchan Arukh ones. This is the classical
cross-reference apparatus printed in the margin of the Vilna Shas, mapping each
talmudic passage to the codes that rule from it. It is:

- **curated by hand**, centuries before anyone thought about retrieval;
- **cross-register by construction** — terse codified law ↔ discursive argument;
- **exactly the evaluation task** in `PLAN.md` §7.

The Mishnah pairs come from a different apparatus (`mesorat hashas` 3,536,
`mishnah in talmud` 2,096) and are structural rather than inferential — keep
them as a separate, easier eval split.

## Scale check

27,573 distinct Bavli segments carry at least one gold link. Against a Bavli of
roughly 45k segments, that is over half the corpus reachable as a positive —
and a tractate-level split (§7) still leaves substantial held-out material.

For comparison: math-embed was trained on pairs derived from **559** KG
concepts and beat OpenAI's `text-embedding-3-small` by 0.816 to 0.461 MRR. This
is two orders of magnitude more supervision, and human-curated rather than
LLM-extracted.

## Known undercounts

- **Shulchan Arukh, Even HaEzer is missing entirely.** Its index uses a
  `SchemaNode` with sub-nodes (`Seder HaGet`, `Seder Halitzah`) and reports
  `lengths: None`, so the siman enumeration produced zero refs. One of four
  books absent — the true SA figure is materially higher. Fix in Phase 2 by
  walking the schema rather than assuming a flat depth-2 structure.
- Three Mishneh Torah books 504'd on whole-book requests (Marriage, Sacrifices
  Rendered Unfit, Creditor and Debtor) and need chapter-level retries.
- Tanakh-citation and parallel-sugya pairs not yet counted.

So 50,214 is a **floor**, not an estimate.

## Correction made during the run

A first pass counted 39,204 Mishneh Torah → Bavli pairs. Wrong: the tractate
filter was built from every title under `Talmud > Bavli`, which includes
commentaries *on* the Talmud — `Reshimot Shiurim on Sanhedrin` surfaced in the
tractate rankings and gave it away. Restricting to the 37 actual tractates
(no ` on ` in the title, not under a `Commentary` path) gives 27,601. The
tighter number is the one used above.

Together with the coverage-denominator error recorded in `PLAN.md` §0, that is
two counting mistakes in one afternoon, both inflating results, both caught by
a figure that looked implausibly good. The lesson holds for the benchmark:
**when a number flatters the project, find the denominator before believing it.**

## Next

Phase 2 (pipeline) is unblocked. First tasks: walk Even HaEzer's schema, retry
the three 504'd books, then pull English text for the 27,573 target segments and
build anchor/positive records with same-daf hard negatives.
