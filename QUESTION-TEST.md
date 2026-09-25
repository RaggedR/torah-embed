# The question test — does retrieval survive real queries?

**Run:** 2026-09-24. **Design:** 40 Mishneh Torah rulings with known gold sugyot.
Two sub-agents rewrote each as the question a learner would actually ask, in
plain English, avoiding the ruling's technical vocabulary. Retrieval measured
against the **same gold targets**, over the full 81,481-segment corpus. A paired
comparison isolating exactly one variable: query phrasing.
Script: `run_questions.py`.

Example:

> **Ruling:** "Once the time for Minchah Gedolah arrives, one should not enter a
> bathhouse, even [if only] to sweat, until he has prayed, lest he faint…"
>
> **Question:** "Can I take a bath or get a haircut before I've said afternoon
> prayers?"

## Result — retrieval collapses

| Method | MRR | R@1 | R@10 |
|---|---|---|---|
| BM25 | 0.514 → **0.145** | 0.375 → 0.075 | 0.750 → **0.325** |
| Dense (`bge-base`) | 0.451 → **0.271** | 0.325 → 0.125 | 0.725 → **0.500** |
| Naive z-sum hybrid | 0.504 → **0.177** | 0.350 → 0.050 | 0.775 → 0.475 |

**Every metric produced today was measured in the left column. The deployed
system lives in the right one.**

## Three consequences

**1. Dense is far more robust than lexical.** BM25 loses 72% of its MRR,
dense 40%. The near-tie that shaped the architecture (0.497 vs 0.500) was an
artifact of using rulings as queries — a ruling shares vocabulary with its
source sugya in a way a question does not. On realistic queries dense wins
clearly. **Revises D9.**

**2. The naive hybrid becomes harmful.** 0.177 against dense's 0.271. Unweighted
z-score fusion lets a badly-degraded arm drag down a good one. Dense-primary;
keep BM25 only with learned or weighted fusion. **Revises D9.**

**3. Recall is the bottleneck again, not ranking.** Dense R@10 falls to 0.500. A
reranker cannot recover what retrieval never returned. **Demotes D10** behind
fixing the retriever.

## Mechanism — specificity, not overlap

Token overlap with the gold passage is essentially unchanged: ruling 0.41,
question 0.42. The collapse is **not** explained by vocabulary disappearing.

A question is short, and its words are common. It carries few *discriminative*
terms. "Can I take a bath before afternoon prayers?" shares ordinary words with
thousands of passages and distinctive words with almost none. The overlap proxy
measured the wrong property and would have declared the two query forms
equivalent.

## What this means for training

The distribution mismatch flagged earlier as "not urgent" is the dominant
effect. Training anchors must be **question-shaped**, not ruling-shaped:

- Generate synthetic questions at scale from the 27,013 gold pairs — the same
  method used here, which produced usable questions in one pass.
- Train the bi-encoder on (question, sugya) pairs. This attacks the measured
  failure directly.
- Keep ruling-anchored pairs as a secondary signal, not the primary one.

**This reinstates the bi-encoder fine-tune as the priority** and moves the
cross-encoder reranker behind it.

## Refinement — like-for-like under sugya-level credit

The strict metric demands the *exact* linked segment. But D8 decided the system
**displays the enclosing sugya**, so a retrieved neighbour of the right argument
is a correct answer, not a near-miss. Re-scored with credit for landing within
±3 segments of a gold target (a sugya proxy), same 40 items, both query forms:

| credit | method | ruling → question (R@10) | change |
|---|---|---|---:|
| strict | bm25 | 0.750 → 0.325 | −57% |
| strict | dense | 0.725 → 0.500 | −31% |
| **relaxed** | bm25 | 0.800 → 0.375 | **−53%** |
| **relaxed** | **dense** | 0.750 → **0.675** | **−10%** |
| relaxed | dense MRR | 0.607 → 0.346 | −43% |

**BM25 genuinely collapses** — both metrics, both credit rules. That stands.

**Dense does not.** Under the metric matching the product, its recall barely
moves (−10%). What degrades is **ranking** (MRR −43%). Dense finds the right
argument for a natural question nearly as often as for a ruling; it cannot put
it first.

The strict metric was scoring segment-pinpointing — a task D8 already decided
the product would not perform. Roughly half the apparent catastrophe was the
evaluation measuring a capability we had chosen not to need.

**This partly reverses the demotion of the cross-encoder reranker.** Corrected
picture: recall is adequate (0.675 R@10 on real questions), ranking is the
bottleneck (MRR 0.346). Both the question-anchored bi-encoder *and* the reranker
are justified — the bi-encoder to lift ranking within the retrieved set, the
reranker to reorder it.

**Checked, not assumed:** gold fan-out for these 40 is mean 3.5, median 2, and
27/40 have more than one target. Since credit is given if *any* gold segment
ranks in top-k, multi-target gold makes retrieval **easier** — so the writers'
concern that narrowed questions would be unfairly penalised does not hold in
that direction.

## Caveats

- n=40. Effect sizes are large (3.5× for BM25) but the sample is small.
- Questions were written by a language model, not by real users. They may be
  more fluent and more on-topic than genuine queries — if anything this makes
  the measured collapse an **optimistic** bound.
- ±3 segments is a proxy for "same sugya", not the real boundary. The pilot
  chunk map would give an exact answer for Berakhot.
- The relaxed numbers are the honest ones **for a system that displays sugyot**.
  For a system returning bare segments, the strict numbers apply.
