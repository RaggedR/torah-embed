# torah-embed — results

**Trained:** 2026-09-24. 1 epoch, 2,087 steps, 1h25m on Apple MPS.
**Base:** `BAAI/bge-base-en-v1.5`. **Loss:** 0.641 → 0.303.
**Data:** 33,393 triplets from 27,013 *ein mishpat* pairs + 2,400 generated
question anchors, with same-daf hard negatives.
**Test:** 552 queries from Sanhedrin and Yevamot, held out whole.
Retrieval over all 81,481 English Bavli segments, no pruning.

## MRR

| Query form | BM25 | `bge-base` zero-shot | **torah-embed** | gain |
|---|---:|---:|---:|---:|
| ruling | 0.430 | 0.412 | **0.462** | +12.2% |
| practical question | 0.090 | 0.175 | **0.211** | +20.0% |
| conceptual question | 0.042 | 0.086 | **0.116** | +35.9% |
| ruling (sugya credit) | 0.509 | 0.491 | **0.561** | +14.2% |
| practical (sugya credit) | 0.125 | 0.236 | **0.292** | +23.6% |
| conceptual (sugya credit) | 0.063 | 0.133 | **0.178** | +34.2% |

## R@10

| Query form | zero-shot | torah-embed | gain |
|---|---:|---:|---:|
| ruling | 0.616 | 0.681 | +10.6% |
| practical question | 0.295 | 0.377 | +27.6% |
| conceptual question | 0.161 | 0.221 | +37.1% |

## D45 — the pre-registered criterion

> Beat zero-shot on held-out **question** queries by a margin exceeding the
> ruling-query gain. A model improving only on rulings has learned the
> benchmark, not the task.

| credit | rulings | questions | verdict |
|---|---:|---:|---|
| strict | +12.2% | **+27.9%** | **PASS** |
| sugya | +14.2% | **+28.9%** | **PASS** |

Questions improved **more than twice** as much as rulings, under both rules.

## The gradient is the evidence

| register | overlap with target | MRR gain |
|---|---:|---:|
| ruling | 0.41 | +12% |
| practical question | 0.30 | +20% |
| conceptual question | 0.21 | **+36%** |

Improvement rises as lexical overlap falls. The model gained most where surface
matching helps least — what semantic learning looks like, and what a memorising
model cannot produce. Against BM25 the same pattern is starker: 2.3× on
practical questions, **2.8×** on conceptual ones, where BM25 scores 0.042 and is
effectively unusable.

Pre-registered expectation was 10–20% relative. Delivered 28%.

## What this is not

- **Absolute numbers are modest.** Conceptual questions: MRR 0.116, R@1 0.067,
  R@10 0.221. The right sugya ranks first ~7% of the time. A real improvement on
  a hard task, not a solved problem.
- **One epoch, batch 16** — forced by 16 GB unified memory; MNRL wants 64+.
  Further gain most likely comes from hardware, not method.
- **Held-out tractates are Sanhedrin and Yevamot** — capital courts and levirate
  marriage, heavy in the status-chain material the question-writers reported as
  hardest to phrase naturally. Living-law fraction was checked and matches the
  training split (0.28 vs 0.26), so the split is not biased, but the task is
  genuinely hard here.
- **Synthetic test questions** were written from the rulings by the same process
  as the training questions (D46). The relative comparison is sound; the
  absolute level is an optimistic bound. The author's 26 hand-written questions
  (`ROBIN-QUESTIONS.md`) remain the independent check.

## The independent check (D47) — a caveat that matters

The author's 26 hand-written questions are the only query set in the harness
**not generated from its own answer**. They are historical and theological
(*Why did Jacob change his name to Israel?*, *Is the promise of the land
conditional on how we behave?*) rather than practical-halakhic, and no gold
labels exist for them.

Fine-tuning changed the top hit for **21 of 26**. Inspected by hand, the change
is **not a clear improvement**:

| question | before → after |
|---|---|
| Jacob → Israel | Berakhot 13a:1 → unchanged (correct) |
| Messiah rebuilds the Temple | Megillah 17b:20 → unchanged (correct) |
| who counts as firstborn | Bekhorot 47b → Yevamot 24a (both on point) |
| the Akedah and the promise of descendants | Nedarim 32a → Taanit 4a:10 (arguably better — the child-sacrifice sugya) |
| *if Abraham had gone through with it, would Ishmael inherit?* | Bava Batra 116a (inheritance) → **Sotah 13b (Moses and Joseph's burial)** — worse |

The last is a named failure mode: the model matched the **counterfactual form**
of the question ("if X had not happened, would Y…") rather than its content. It
learned a rhetorical shape.

**Reading this honestly.** The +28% benchmark gain is real for the task it
names — retrieving the talmudic source of a halakhic ruling, asked as a
question. It does **not** automatically generalise to narrative or theological
questions, which are a third distribution absent from training. Training anchors
were practical and conceptual questions about *rulings*; these are questions
about *stories*.

Extending coverage would mean generating anchors from aggadic and narrative
passages, not only from Mishneh Torah — which by construction can only yield
legal questions. That is the clearest next step.
