# Thin slice — baselines before pipeline

**Run:** 2026-09-24. **Purpose:** find out whether the task is hard *before*
building Phase 2, per the reordering argued in `PLAN.md` §8.

**Setup.** Corpus: 81,481 English Bavli segments (all 37 tractates, William
Davidson Edition), mean 99 words each. Queries: 500 stratified gold sources.
Retrieval over the whole corpus — no candidate pruning, no tractate hint.
Metric: rank of the first gold segment. Scripts: `corpus.py`, `sources.py`,
`evalset.py`, `run_bm25.py`, `run_dense.py`.

## Corpus facts worth recording

- **81,481 segments**, not the ~45k estimated in `PLAN.md` §9. Steinsaltz
  segmentation is finer than assumed. Index cost rises accordingly (~0.5 GB at
  768 dims); still trivial against 46 GB free.
- **Mean 99 words, p90 149.** Comfortably inside a 512-token window.
  **Chunking is unnecessary** — `rechunk.py` is not needed, and the long-context
  argument for `nomic-embed-text-v1.5` (`PLAN.md` §4) largely evaporates.
- **92% of gold targets are segment-level**, fan-out mean 2.6 / median 2. Gold
  sets are two segments out of 81,481, so Recall@10 is a sharp, interpretable
  metric — unlike math-embed, whose 100+ chunk relevant sets crushed Recall and
  forced reliance on MRR/NDCG.

## Results: BM25

| Split | n | MRR | R@10 | R@1 |
|---|---:|---:|---:|---:|
| **Mishneh Torah** (the real task) | 171 | **0.497** | **0.731** | 0.380 |
| Mishnah (positive control) | 158 | 0.740 | 0.892 | 0.684 |
| Shulchan Arukh (thin data) | 171 | 0.358 | 0.550 | 0.269 |

**The Mishnah row is a control, not a result.** The Gemara quotes each mishnah
verbatim at the head of its sugya, so query and gold passage are often the same
English sentences. BM25 *should* approach ceiling there; that it does is how we
know the harness is wired correctly. Had it scored 0.2, the bug would be in the
pipeline, not the model.

**The Mishneh Torah row is the news, and it is not entirely welcome.** BM25 at
MRR 0.497 and R@10 0.731 is far stronger than expected for a pair type built to
be cross-register. Plain lexical matching already finds the source sugya in the
top ten for nearly three quarters of rulings.

Two readings, and they differ in what they imply:

- *Pessimistic:* the headroom is much narrower than `PLAN.md` §10 assumed. If
  BM25 gets 0.73 R@10, a fine-tuned model must reach ~0.85 to look meaningful.
- *Optimistic:* the ceiling is clearly not reached — R@1 is only 0.380, so in
  62% of cases the correct sugya exists in the corpus and BM25 does not rank it
  first. Precision at the top is exactly what dense retrieval is good at.

The honest reading is that this is now a **reranking-shaped problem**, not a
recall-shaped one. That is a different project from the one `PLAN.md` describes,
and cheaper: a hybrid BM25 + dense pipeline with the fine-tune as the reranker
is likely to beat either alone.

## Results: dense zero-shot

`bge-base-en-v1.5`, 81,481 passages, 1,473s on MPS (fp32 — use fp16 next time;
the Phase 3 bake-off needs one pass per candidate model).

| Split | n | MRR | R@10 | R@1 |
|---|---:|---:|---:|---:|
| **Mishneh Torah** | 171 | **0.500** | **0.737** | 0.374 |
| Mishnah (control) | 158 | 0.684 | 0.842 | 0.601 |
| Shulchan Arukh | 171 | 0.416 | 0.596 | 0.327 |

A near-exact tie with BM25 on the real task (0.500 vs 0.497). Dense loses on the
Mishnah control — expected, since those pairs are lexical duplicates and BM25
owns duplicate detection — and wins on Shulchan Arukh.

## The finding the averages hid: they fail on different queries

| Mishneh Torah, n=171 | R@10 |
|---|---:|
| BM25 alone | 73.1% |
| bge-base alone | 73.7% |
| **Union (either)** | **83.6%** |
| Neither | 16.4% |

Found by BM25 only: 17. By dense only: 18. Overlap just 63.2%. These are not two
measurements of one ability; they are two abilities that happen to average the
same. **Ten points of recall sit in the union that neither reaches alone.**

A naive z-score fusion, with no training at all, already lifts MRR:

| Split | BM25 | dense | naive hybrid |
|---|---:|---:|---:|
| Mishneh Torah | 0.497 | 0.500 | **0.527** |
| Mishnah | 0.740 | 0.684 | 0.742 |
| Shulchan Arukh | 0.358 | 0.416 | 0.419 |

**Methodological note.** Reporting a single mean over a heterogeneous query set
concealed this entirely — two systems at 0.497 and 0.500 read as
interchangeable, and the obvious conclusion ("dense adds nothing") was wrong.
When the fine-tuned model is benchmarked, ask *which queries it fixes*, not
whether the mean moved.

## Verdict

MRR 0.500 falls in the pre-committed 0.45-0.75 band: **proceed, reframed as
reranking.** The complementarity result says the same more sharply.

The project is no longer "replace lexical search with a dense index". It is:

1. **Retrieve** a candidate pool by BM25 ∪ dense — ceiling 83.6% R@10.
2. **Rerank** that pool with the fine-tuned model. R@1 of 0.374 is where the
   room is: the right sugya is usually found and usually not ranked first.
3. **Chunk semantically**, so the unit being ranked is an argument, not a
   99-word fragment (`PHASE2A-PILOT.md`).

Cheaper than the original plan, better matched to the evidence, and it explains
the R@1/R@10 gap visible since the first BM25 run.

## Decision rule, fixed in advance

Set before seeing the dense numbers, so the verdict cannot be fitted to them:

| bge-base zero-shot on MT | Reading | Action |
|---|---|---|
| MRR > 0.75 | Little headroom | Drop the fine-tune; ship hybrid retrieval |
| MRR 0.45–0.75 | Comparable to BM25 | **Proceed, but reframe as reranking** |
| MRR 0.25–0.45 | Dense underperforms lexical | Proceed; large headroom, hybrid essential |
| MRR < 0.25 | Dense is failing | Debug before any training |
