# torah-embed — a BERT embedding model for talmudic retrieval

**Status:** plan, not started. v2, 2026-09-24 — **English corpus decided.**
**Supersedes:** `PLAN-v1-hebrew.md` (Hebrew/Aramaic-primary). Kept for the
reasoning, not the conclusions.
**Model after:** `~/git/embeddings` (math-embed), whose recipe this reuses.

---

## D. Decision log

Every decision taken on 2026-09-24, with what forced it. Decisions marked
**settled** should not be relitigated without new measurement.

### Scope and corpus

| # | Decision | Evidence | Status |
|---|---|---|---|
| D1 | Corpus language is **English** | Robin's call | settled |
| D2 | Drop **Rashi** and **Tosafot** pairs | 9.5% / 27% English coverage | settled |
| D3 | Drop **Shulchan Arukh** as training data | **5.4%** segment-level English (the earlier 89% was an unrepresentative chapter sample) | settled |
| D4 | **Mishnah** pairs demoted to positive control, not training data | Gemara quotes each mishnah verbatim; token overlap 0.62, 34/158 above 0.9 | settled |
| D5 | **Mishneh Torah** is the gold set — 27,013 pairs, ~9,500 queries | 97.9% coverage; mean token overlap 0.42, none above 0.9 | settled |
| D6 | Do **not** clone `Sefaria-Export-Archive` | 7.9 GB of git history, archived; API pull is ~1.5 GB | settled |

### Retrieval architecture

| # | Decision | Evidence | Status |
|---|---|---|---|
| D7 | **Segments** are the indexing and retrieval unit | A/B: matched-fraction R@1% 0.818 (segments) vs 0.646 (chunks); dilution | settled |
| D8 | Sugya chunks are the **display/context** unit ("retrieve narrow, present wide") | resolves the granularity dispute without paying the dilution cost | settled |
| D9 | ~~Hybrid BM25 ∪ dense~~ → **dense-primary** | **REVISED by `QUESTION-TEST.md`.** On question queries BM25 collapses (MRR 0.514→0.145) and naive z-sum fusion is *worse* than dense alone (0.177 vs 0.271). Keep BM25 only with learned/weighted fusion | revised |
| D10 | **Both**: question-anchored bi-encoder *and* cross-encoder reranker | **REVISED TWICE.** Under sugya-level credit (the metric matching D8) dense recall on questions holds at R@10 0.675, only −10% vs rulings — but MRR falls 43% to 0.346. Recall is adequate; **ranking is the bottleneck**. Train the bi-encoder on question anchors, then rerank | revised |
| D26 | **Evaluate with sugya-level credit**, not exact-segment | D8 displays the enclosing sugya, so a retrieved neighbour of the right argument is a correct answer. Strict scoring measured a capability the product does not perform, and understated dense by ~half | settled |
| D24 | Training anchors must be **question-shaped**, not ruling-shaped | the ruling→sugya task we measured all day is not the deployed task | settled |
| D25 | Generate **synthetic questions at scale** from the 27,013 gold pairs | one agent pass produced usable questions for 40 rulings; same method scales | settled |
| D11 | Keep **headings** on displayed chunks | +0.05 R@1% for dense at no cost (clean same-pool comparison) | settled |
| D12 | Drop **Matryoshka** | it existed to shrink an index now measured under 1 GB | settled |
| D13 | Context window is **moot**; `bge-base`'s 512 tokens suffices | segments are 99 words mean, 149 p90 | settled |
| D14 | Full 5,349-amud chunking run leaves the **critical path** | D7 — chunking is presentation, not retrieval | settled |

### Method

| # | Decision | Rationale | Status |
|---|---|---|---|
| D15 | **Write acceptance criteria before seeing results** | the A/B confound did not merely inflate the result, it **reversed its sign** | standing rule |
| D16 | **Report BM25 on every split**, however embarrassing | it is the lexical-leakage alarm | standing rule |
| D17 | Keep the **Mishnah positive control** in the harness | BM25 must near-ceiling on duplicate pairs; if it does not, the pipeline is broken | standing rule |
| D18 | Keep **heading-only retrieval (condition D)** in the harness | behavioural leakage detector: 0.415 vs 0.595 proves headings do not encode the answer | standing rule |
| D19 | Always ask sub-agents **what they were unsure about** | both chunking defects passed every mechanical check; self-report was the only channel that found them | standing rule |
| D20 | Agents return **ref ranges, never text** | makes corruption structurally impossible; 0 failures in 216 chunks | standing rule |
| D21 | Never give agents an **expected output count** | A/B: the numeric hint produced 23% more, smaller chunks — agents treated it as a target | settled |
| D22 | Use **fp16** for corpus encodes | fp32 on MPS took 1,473s for 81,481 passages | settled |
| D23 | **Verify denominators** when a number flatters the project | three of the session's errors were mine and all inflated results | standing rule |

### Training and benchmarking (Phase 4, decided 2026-09-24)

| # | Decision | Value | Why |
|---|---|---|---|
| D27 | Base model | `BAAI/bge-base-en-v1.5` | strongest English retriever at BERT-base scale that fine-tunes in 16 GB unified memory; `bge-m3`/`e5-large` at 568M would need ~9 GB of optimizer state before activations |
| D28 | Loss | `MultipleNegativesRankingLoss` | in-batch negatives, the standard for (anchor, positive) retrieval data; same choice as math-embed |
| D29 | Batch size | **24** | MNRL quality scales with batch size (negatives come *from the batch*, so gradient accumulation does **not** substitute). 24 is the largest that fits at 256 tokens on MPS |
| D30 | Max sequence length | **256** | corpus segments are 99 words mean, 149 p90 (~200 tokens). 512 doubles compute for the tail alone |
| D31 | Learning rate | **2e-5**, 10% warmup | standard for BERT-base contrastive fine-tuning; the base is already a trained retriever, so a low LR avoids destroying it |
| D32 | Epochs | **2** | ~38k pairs with oversampling; more risks memorising a corpus this small |
| D33 | Anchors | **both** ruling-shaped and question-shaped | questions teach the deployment distribution (D24); rulings supply volume |
| D34 | Question oversampling | **×3** | only 1,200 rulings have generated questions vs 8,210 with ruling anchors; without oversampling the deployment distribution is diluted ~7:1 |
| D35 | Questions per ruling | **2** — one practical, one conceptual | the author's own questions (`ROBIN-QUESTIONS.md`) were conceptual/theological while agent-generated ones defaulted to practical. Both registers are real |
| D36 | Hard negatives | same-daf, non-linked, up to 3 per query | random in-batch negatives are trivially easy here — a random segment is another tractate on another subject. Same-daf negatives force the model to discriminate *within* a topic |
| D37 | Positives per query | capped at **4** | fan-out is mean 2.6 but reaches 31; uncapped, a few queries would dominate the epoch |
| D38 | Precision | fp32 | MPS `use_amp` is unreliable; fp16 is for inference encodes (D22), not this training run |

### Split and evaluation protocol

| # | Decision | Value | Why |
|---|---|---|---|
| D39 | Split unit | **whole tractates** — Sanhedrin, Yevamot held out | splitting by link leaks: both endpoints of a held-out link still appear via their other links |
| D40 | Mixed-tractate queries **discarded**, not assigned | 784 of 9,514 | a query with targets on both sides of the split leaks regardless of which side it is put |
| D41 | Test set | **520 queries**, train 8,210 (38,242 pairs) | ~6% clean test; the discard is the price of a leak-free split |
| D42 | Retrieval pool at eval | **all 81,481 segments**, no pruning, no tractate hint | pruning to the held-out tractates would shrink the pool and inflate every metric — the same confound that reversed the chunking verdict (§`PHASE2A-AB.md`) |
| D43 | Primary metric | **R@10 and MRR on question queries** | the deployed task. Ruling-query metrics reported as secondary, for comparison with the pre-training baselines |
| D44 | Mandatory comparison rows | BM25; `bge-base` zero-shot; fine-tuned | the zero-shot row is the honest floor (MRR 0.500). Without it, any number looks good |
| D45 | Success criterion, **pre-registered** | beat `bge-base` zero-shot on the held-out question split by a margin exceeding the ruling-query gain | a model that improves only on ruling queries has learned the benchmark, not the task |
| D46 | Test questions generated by the **same process** as training questions | same prompt, same model, same two registers | if the test questions were hand-written, any gain could be an artifact of the two sets differing in *style* rather than the model having learned anything. Only the measured variable may differ (cf. D42) |
| D47 | The author's own 26 questions stay in the harness as an **independent out-of-distribution check** | `ROBIN-QUESTIONS.md` | D46 means the evaluation inherits the generator's biases; a human-written, theologically-framed set is the only control on that. It is also the only query set not written *from* its own answer |
| D48 | Keep **both** question registers; do not filter degenerate ones | measured: practical questions overlap their ruling 0.30, conceptual 0.18; only 1% exceed 0.7 | two agents independently reported that Temple-ritual mechanics, architectural inventories and legal edge-case chains have no everyday analogue, so the practical question degenerates toward restating the ruling. Measured, the effect is 1% and needs no filtering. The **conceptual** register is the more divergent and carries the harder signal |

**Pre-registered expectation (written before training):** a 10–20% relative MRR
gain over zero-shot would be a real result. math-embed's 0.816-vs-0.461 is not
the comparison — that was measured against a weak baseline, whereas
`bge-base-en-v1.5` already scores MRR 0.500 here untrained.

### Open

| # | Question | Why it matters |
|---|---|---|
| O1 | ~~Does retrieval survive question-shaped queries?~~ | **ANSWERED: no.** See `QUESTION-TEST.md`. BM25 MRR 0.514→0.145, dense 0.451→0.271, R@10 0.725→0.500. Revised D9, D10; added D24, D25. The single most consequential measurement of the session. |
| O4 | ~~How much of the collapse is metric strictness?~~ | **ANSWERED: about half, for dense.** Sugya-level credit lifts dense R@10 on questions 0.500 → 0.675 (−10% vs rulings, not −31%). BM25's collapse is real under both rules. Added D26 |
| O2 | Does the cross-encoder reranker beat the hybrid floor of MRR 0.527? | the project's actual thesis |
| O3 | Is 16.4% "found by neither" recoverable? | the union ceiling is 83.6%; reranking cannot exceed it |

### Errors made and corrected (kept deliberately)

1. **Coverage denominator** — computed non-empty ÷ returned, so refs with no English fell out of the denominator. Could only ever report 100%.
2. **Tractate filter** — counted commentaries *on* the Talmud as Talmud; 39,204 pairs → 27,601.
3. **Amud-boundary constraint** — the chunking output format forced every cross-daf sugya to be severed, systematically, at all 5,349 boundaries.
4. **Shulchan Arukh coverage** — sampled simanim 1, 50, 150; early ones are translated and the tail is not. 89% → 5.4%.
5. **Pool-size confound** — nearly reported a 10-point MRR gain for semantic chunking that was entirely arithmetic.

All five flattered the result or hid a problem. Each was caught by a figure
looking implausibly good. Hence D15, D16, D23.

---

## 0. The decision, and what it cost

§7 of v1 left the corpus language open. **Decided: English.** That reverses the
v1 recommendation, so the consequences are measured here rather than assumed.

Translation coverage, sampled from the Sefaria v3 API on 2026-09-24. Denominator
is the *Hebrew* segment count, numerator the English — coverage, not existence:

| Text | Coverage | English version | Licence |
|---|---:|---|---|
| Talmud Bavli | **100%** | William Davidson Edition | CC-BY-NC |
| Mishnah | **100%** | Davidson / Kulp | CC-BY-NC, CC-BY |
| Mishneh Torah | **100%** | Touger | CC-BY-NC |
| Shulchan Arukh | **89%** | mixed (Denburg, Wikisource) | CC-BY, CC-BY-SA |
| Tanakh | 100% | JPS | CC-BY-NC / PD (1917) |
| **Rashi on Talmud** | **9.5%** | Community Translation | CC0 |
| **Tosafot on Talmud** | **27%** | Buckler | CC-BY |

*Measurement note:* a first pass reported 100% everywhere. It was wrong — it
computed non-empty ÷ segments-returned, and refs with no English version at all
returned nothing and so dropped out of the denominator. `Rashi on Sanhedrin 74a`
has no English version whatsoever. The corrected figures are above. Worth
recording because the same denominator error would flatter any coverage or
recall number we produce later.

### What this costs, and what it buys

**Cost: the bulk supervision is gone.** Rashi and Tosafot were the
"very high volume" pair classes in v1. At 9.5% and 27% they cannot carry a
training set. The pair inventory drops from millions to tens of thousands.

**Buy: the poison went with it.** The *dibbur hamatchil* leakage of v1 §5 — the
hazard that a careless run trains a substring-matcher scoring 0.95 on a
meaningless benchmark — lived almost entirely in the Rashi and Tosafot pairs.
Choosing English deletes the largest data-hygiene risk in the project.

**Buy: what survives is exactly the gold set.** Mishneh Torah at 100% and Talmud
at 100% means the primary evaluation task — halakhic ruling → talmudic source —
is *fully* available in English. In v1 that was the best pair class. It is now
the main one.

**Buy: BEREL's absence solves the memory problem.** English retrievers at
BERT-base scale fine-tune comfortably in 16 GB.

**Buy: the index shrinks ~5×.** Without the Rashi/Tosafot layers the corpus is
~100k segments, not ~500k. Budget in §9.

This turns the project from *bulk supervision, hygiene-limited* into *precision
supervision, volume-limited*. That is the better of the two problems, and it is
the one math-embed already solved: that model trained on pairs derived from 559
KG concepts and beat OpenAI by a wide margin. Tens of thousands of clean,
human-curated, cross-register pairs is more supervision than math-embed had.

---

## 1. Goal

Train a domain-specific English sentence-embedding model over the classical
Jewish canon, so RAG retrieves *the right sugya* rather than passages sharing
vocabulary with the query.

Target capability, as a test: given a halakhic ruling in Mishneh Torah or
Shulchan Arukh, retrieve the talmudic passage it derives from. Terse codified
law against discursive argument — almost no shared surface vocabulary, so BM25
loses badly and a genuine semantic retriever wins. It is the sharpest available
discriminator.

Not a generative model. An encoder. Generation is a separate layer, out of scope.

---

## 2. Component mapping

| math-embed | torah-embed |
|---|---|
| `allenai/specter2_base` | `BAAI/bge-base-en-v1.5` (see §4) |
| 4,794 chunks in ChromaDB | ~100k English segments |
| 559 KG concepts, hand-constructed | Sefaria link graph, hand-curated |
| (concept, chunk) pairs | (citing text, cited text) pairs |
| 108 queries | held-out links, split by tractate |
| MNRL + MatryoshkaLoss | same |
| MRR / NDCG@10 | same, plus Recall@K |

The Rust layer (`cosine.rs`, `knn.rs`, `metrics.rs`) and the `EmbeddingModel`
ABC carry over unchanged. Only the data pipeline is new.

The method prior still holds: SPECTER2 works by contrastive training on citation
triplets. Sefaria's link graph is a citation graph, curated by editors at
segment granularity — finer ground truth than math-embed's
concept→paper→all-chunks approximation, which is why its Recall@20 sat at 3–4%.
Recall@K should become a usable metric here.

---

## 3. Licensing — now load-bearing

With an English corpus the CC-BY-NC text is in the training data **and in the
index**. In the sample, 460 of 617 English segments were CC-BY-NC.

CC-BY-NC **permits** redistribution and adaptation with attribution, for
non-commercial purposes. So publishing weights and an index to HuggingFace with
proper attribution is allowed. What is excluded is commercial use — by us or by
anyone downstream.

Practical consequences:
- Label the model card CC-BY-NC and attribute Sefaria, Steinsaltz and Touger
  explicitly.
- Any commercial path requires rebuilding on unencumbered text. A public-domain
  fallback exists — Rodkinson (1918) and the A. Cohen Cambridge tractates — but
  both are partial and the Rodkinson is poor. Treat a commercial variant as a
  separate project, not a re-export.

---

## 4. Base model

BEREL is out — no English. The slot goes to an English retriever already
contrastively trained, which changes the character of the exercise (see §11).

Candidates, all fine-tunable in 16 GB:

| Model | Params | Ctx | Note |
|---|---:|---:|---|
| `BAAI/bge-base-en-v1.5` | 109M | 512 | strong MTEB baseline; default choice |
| `intfloat/e5-base-v2` | 109M | 512 | close second |
| `nomic-ai/nomic-embed-text-v1.5` | 137M | **8192** | native Matryoshka; long ctx |
| `sentence-transformers/all-mpnet-base-v2` | 110M | 384 | older, weaker |

**Recommendation: benchmark `bge-base-en-v1.5` and `nomic-embed-text-v1.5`
before committing — and as of the Phase 2a pilot this is no longer optional.**
Semantic chunking produces sugyot of which **34% exceed 512 tokens** (longest
~1,700). `bge-base` would silently truncate a third of the index — no error,
just the end of every long argument dropped. The bake-off question is therefore
not "which scores better on MTEB" but "which can represent a sugya whole".
See `PHASE2A-PILOT.md`. Nomic is the interesting one — an 8192-token window would
let a long sugya be embedded whole rather than split with overlap, and it is
natively Matryoshka, which is the trick §9 relies on for index size. If it holds
up on the baseline run it is the better base for this corpus specifically.

Unlike v1, the first benchmark run will *not* look terrible. These models are
trained for sentence similarity. That is good for the baseline and bad for the
headline — see §11.

---

## 5. Training pairs

| Pair type | Coverage | Signal | Status |
|---|---|---|---|
| Mishneh Torah → talmudic source | **97.9%** | **cross-register, semantic** | **gold — the core set, 27,013 pairs** |
| Parallel sugyot across tractates | 100% | high | uncounted; likely useful |
| Talmud → Tanakh verse citation | 100% | topical | verse quoted verbatim — leakage risk |
| Mishnah → its Gemara sugya | 93.9% | **lexically duplicate** | **demoted to sanity check — see below** |
| Shulchan Arukh → source | **5.4%** | cross-register | **dropped, insufficient coverage** |
| Rashi / Tosafot → daf | 9.5% / 27% | — | **dropped, insufficient coverage** |

**Two corrections, measured 2026-09-24 (superseding §0's table, which sampled
chapters rather than segments):**

- **Shulchan Arukh is 5.4% translated at segment level, not 89%.** The §0 sample
  took simanim 1, 50 and 150 of each book; early simanim are translated and the
  long tail is not. Of 15,860 SA→Bavli pairs, only 855 have English on the
  source side. SA joins Rashi and Tosafot as unusable in English.
- **The Mishnah pairs are lexical duplicates.** The Gemara quotes each mishnah
  verbatim at the head of its sugya and the Davidson edition reproduces it, so
  source and target are frequently the *same English sentences* (token overlap:
  mean 0.62, and 34/158 sampled pairs above 0.9). Training on them teaches
  copy-detection.

  **But they are not worthless — promote them to a positive control.** BM25
  must score near-ceiling on Mishnah pairs. If it does not, the retrieval
  pipeline is broken. It scored MRR 0.740 / R@10 0.892 on first run, which is
  how we know the harness works.

Mishneh Torah is clean by the same measure: mean token overlap 0.42, and **not
one** of 171 sampled pairs above 0.9. The gold set survives at **27,013 pairs
across ~9,500 distinct queries** — still two orders of magnitude more
supervision than math-embed had.

Residual leakage risk is now confined to verse-citation pairs, where the verse
appears verbatim in the sugya. Same mitigation as v1: strip the quoted verse from
the anchor, and report BM25.

**Hard negatives remain non-optional.** In-batch MNRL negatives are random
segments — trivially easy, since a random segment is from another tractate on
another subject. Mine negatives from the **same daf or adjacent sugya** that are
not linked. Without them the model learns "purity or torts?", not "is this the
source of that ruling?".

**Steinsaltz interpolations.** The Davidson English weaves Steinsaltz's
explanatory expansions into the translation inline. Two consequences: the English
Talmud is already commentary-glossed, which does much of Rashi's explanatory work
and softens the loss of the Rashi pairs; and "the text" is not neutral — the
model learns Steinsaltz's reading. Worth stating in the model card.

---

## 6. Chunking — semantic, agent-derived

**Direction of travel: merge, not split.** Measured 2026-09-24: the English
Bavli is 81,481 Sefaria segments, mean 99 words, median 96, 15.2 segments per
amud across 5,349 amudim. Nothing is too long for a 512-token window. The
problem is the opposite — **a sugya spans five to fifteen segments, so every
indexed unit is already a fragment of an argument.** We are not at risk of
cutting mid-argument; we are starting mid-argument 81,481 times.

This likely distorts measurement, not just retrieval. In the thin slice
(`THIN-SLICE.md`) BM25 scored R@10 0.731 but R@1 only 0.380. The gold target is
one fragment of a sugya whose neighbours are on the identical topic; no model
can reliably prefer fragment 6 to fragment 7, because that distinction is
editorial rather than semantic. Merging to sugya units should raise R@1 *and*
make the number mean something.

### The unit: a sugya, chosen by agents that have read the text

Sub-agents read the text and mark natural boundaries. Concretely:

**Input.** One amud (~15 segments, ~1,500 words), presented as a numbered list
of segments with their Sefaria refs, plus the last two segments of the previous
amud and first two of the next as context (marked as context, not for chunking —
sugyot cross the daf break constantly).

**Output.** A JSON list of chunks, each `{first_ref, last_ref, heading}`.

**Hard constraint — boundaries fall only at existing segment edges.** The agent
selects which edges to keep, never where to cut. Because Sefaria segments never
break mid-sentence, **mid-sentence cuts become structurally impossible** rather
than something we check for afterwards. The output is a *partition*: every
segment in exactly one chunk, none dropped, none duplicated.

**What the agent is asked to find:** where one argument ends and the next
begins — a new mishnah, a new question (*ba'ei*), a shift from the *stam* to a
named dispute, the close of a *teiku*. Where it is genuinely unsure, it is
instructed to prefer the larger chunk. A slightly over-long chunk costs
precision; a chunk that severs an argument costs correctness.

### Headings

Each chunk carries a 1–2 sentence heading giving its context in the surrounding
text, prepended to the body before embedding. This is the contextual-retrieval
pattern: the embedded text becomes `heading + "\n\n" + body`, so a chunk
carries the context a reader would have from the facing page.

A heading must state: the tractate and daf; what the passage is about in plain
English; and **how it sits in the surrounding argument** — "continues Abaye's
objection begun at 12a:4", "opens the fourth chapter", "the resolution of the
contradiction raised above".

**Anti-leakage constraint, and it is not optional.** Headings must describe the
passage *in its own terms* and must never mention Rambam, Mishneh Torah,
Shulchan Arukh, or the halakhic conclusion drawn from the passage. A heading
reading "the source for Rambam's ruling on lost property" would write the
evaluation label directly into the index and inflate every metric we then
report. The agent is not shown the link graph. Given the two counting errors
already recorded in §0 and `PHASE1.md`, assume this will be got wrong somewhere
and grep the finished headings for code names before indexing.

### Verification

Agent judgment varies; the guardrails are mechanical:

1. **Partition invariant.** Concatenated chunk bodies must equal the original
   amud text exactly, modulo whitespace. Any amud failing this is re-run, then
   escalated. This catches dropped, duplicated and silently rewritten text.
2. **Size distribution.** Report words per chunk. A collapse to one-chunk-per-amud
   means the agent defaulted rather than read.
3. **Leakage grep.** No code names, no halakhic conclusions in headings.
4. **Spot audit.** Read 20 chunk boundaries by hand against the text.
5. **A/B on the real harness.** Re-run the thin slice over sugya chunks and
   compare to the 81,481-segment baseline. **This is the only test that
   matters** — if semantic chunking does not move MRR and R@1 on the Mishneh
   Torah split, it is aesthetic and should be abandoned.

### Cost and batching

5,349 amudim. One agent per amud is 5,349 calls; batching four amudim per agent
gives ~1,340, at roughly 8k input and 1.2k output tokens each — order 11M input
and 1.6M output tokens. Sonnet, per the standing default; Opus only for amudim
that fail the partition invariant twice. Cache the result keyed by amud so the
run is resumable and never repeated.

Run it on **one tractate first** (Berakhot, 64 dapim) and A/B that before
committing to the full corpus.

### What this deletes — and what it restores

`rechunk.py` is not needed; nothing needs splitting. But the long-context
argument for `nomic-embed-text-v1.5` does **not** evaporate — the pilot measured
34% of sugyot past 512 tokens, so it becomes decisive instead. See §4.

### Two corrections from the pilot

**1. Never tell the agent an expected chunk count.** The pilot prompt said "~15
segments usually yields 2-5 chunks". Three agents in nine referenced that number
unprompted as a target they were deviating from, and split long arguments for
size. A/B on identical amudim (Berakhot 10a-11b, 123 segments): the original
prompt produced 30 chunks, the corrected prompt 23 — **23% fewer, never more on
any amud**, mean chunk 322 → 420 words. Keep only the boundary rule and the
prefer-larger tie-break. Catch defaulting with the distribution check
afterwards, not a hint beforehand.

**2. Chunks must be allowed to cross the amud boundary.** The pilot required
each amud's chunks to partition that amud, which *forced* every sugya running
across the daf break to be severed. `chunker-04b` flagged three in four amudim
(Hezekiah's illness 10a:26-10b:5; the Shema-posture mishna 10b:37-11a:14; the
"who forms light" blessing 11a:26-11b:7) and had to split them regardless. This
is the precise failure the exercise exists to prevent, built into the output
format — and it is systematic, firing at all 5,349 amud boundaries, always in
the same place.

The amud is a typesetting artifact of the Vilna edition. No sugya respects it.

**Fix, preserving the invariant that made the pilot trustworthy:** each agent
emits `continues_previous: true` on an amud's first chunk when it continues the
previous amud's last chunk. A **mechanical** merge pass then joins flagged
pairs. The partition check still runs per amud on raw agent output — unchanged
— and the merge is deterministic code, not agent judgment. Verification stays
strict; the unit stops being the printer's page and becomes the argument.

Consequence for §4: merged cross-daf sugyot will be longer still, so the share
of chunks exceeding 512 tokens rises above the 34% measured in the pilot. The
long-context base model becomes correspondingly more important.

## 7. Evaluation

- **Split by tractate, not by link.** Splitting by link leaks: both endpoints of
  a held-out link still appear in training via their other links. Costs us the
  cross-tractate parallel-sugya pairs; accepted.
- **Primary task:** Mishneh Torah / Shulchan Arukh ruling → talmudic source.
- **Secondary:** Mishnah → Gemara; parallel sugyot.
- **Metrics:** Recall@{5,10,20}, MRR, NDCG@10 — reusing Rust `metrics.rs`.
- **Mandatory baselines on every split:** BM25, un-tuned base, and one large
  frozen model (`bge-m3` or `e5-large`). BM25 is the leakage alarm and is
  reported even when embarrassing.
- **Check denominators.** See §0. Recall must be computed over the gold set, not
  over what the retrieval pipeline happened to return.

---

## 8. Phases

**Phase 1 — measure. ✅ DONE 2026-09-24, see `PHASE1.md`.** Pull the Sefaria links dump. Count links by type, count
segments, measure size distribution. Replaces every estimate here with a number.
Deliverable: pair volumes per category, and whether the Mishneh Torah → Talmud
set alone carries the model. ~1 afternoon.

**Phase 2a — semantic chunking. ✅ DONE, gate NOT passed. See `PHASE2A-AB.md`.**
The pilot succeeded mechanically (216 chunks, 0 partition failures, 0 leaks) but
the A/B failed its pre-registered gate: under matched-fraction retrieval,
chunking is *worse* than segments (dense R@1% 0.818 → 0.646). The apparent raw
gain was entirely pool-shrinkage; the confound reversed the result's sign.
**Decision: retrieve narrow, present wide** — segments remain the indexing unit,
sugya chunks become the display/context unit. Headings are kept (they help dense
slightly, +0.05 R@1%, at no cost). The full 5,349-amud agent run leaves the
critical path.

**Phase 2b — pipeline.** Pair generation against the new chunk ids, verse
stripping, hard-negative mining. The real engineering, and where the risk lives.

**Phase 3 — baselines.** BM25, `bge-base-en-v1.5`, `nomic-embed-text-v1.5`,
one large frozen model. Establishes the floor *before* training, so the lift is
honest. Also decides the base model.

**Phase 4 — train. ✅ DONE 2026-09-24. See `RESULTS.md`.** MNRL on
`bge-base-en-v1.5`, 1 epoch, 2,087 steps. **D45 PASSED under both credit
rules**: questions +27.9% vs rulings +12.2% (strict), +28.9% vs +14.2% (sugya).
Gain rises as lexical overlap falls — ruling +12%, practical +20%, conceptual
+36%. Absolute numbers remain modest (conceptual MRR 0.116).

**Phase 5 — benchmark and write up.** `bench.py` with a new wrapper; paper
alongside `paper/math_embeddings.tex`.

---

## 9. Budget

Measured 2026-09-24: 46 GB free, no local APFS snapshots inflating it. 16 GB
unified memory.

| Component | Estimate |
|---|---:|
| Sefaria corpus (English + links, API pull) | 1.0 GB |
| Base models (2 candidates for §4 bake-off) | 1.1 GB |
| Frozen large baseline | 2.3 GB |
| Training pairs (JSONL) | 0.3 GB |
| Checkpoints (`save_total_limit=2`) | 1.0 GB |
| Final model | 0.5 GB |
| ChromaDB index (~100k segments, 768-dim) | 0.7 GB |
| **Total** | **~7 GB** |

Down from v1's 11 GB: English drops the Rashi/Tosafot layers (~5× fewer
segments) and needs no Hebrew-side duplicate. ~6.5 KB/segment at 768 dims —
3 KB vector, ~1.3 KB HNSW, ~2 KB text and metadata — calibrated against
arxiv-rag (4,794 chunks → 206 MB).

Index at 256 dims via Matryoshka if it ever tightens; at 7 GB it will not.
Do not clone `Sefaria-Export-Archive` (7.9 GB of git history, now archived) —
pull the ~15 works we need via the API.

Housekeeping: `~/git/embeddings/models/waarnar-embed` is 2.9 GB, apparently
accumulated per-epoch checkpoints. Set `save_total_limit=2`.

Neither disk nor memory is a binding constraint — and as of Phase 1, neither is
pair volume. The binding constraint is now **pipeline correctness**: verse
stripping, hard negatives, and honest denominators.

---

## 10. Confidence

Revised down from v1, and the reason matters.

- **MEASURED 2026-09-24, see `THIN-SLICE.md`.** `bge-base-en-v1.5` zero-shot
  ties BM25 on Mishneh Torah (MRR 0.500 vs 0.497, R@10 0.737 vs 0.731). But
  they solve *different* queries — overlap 63%, union R@10 **83.6%**, and a
  naive z-fusion reaches MRR 0.527 untrained. The project is reframed as
  **hybrid retrieval + reranking**, not dense replacement. Headroom is real and
  sits in ranking (R@1 = 0.374), not recall.
- **~60%** (was 85%) that this substantially beats the strongest frozen
  baseline. v1 was measured against BEREL — a raw MLM encoder that would have
  performed terribly out of the box, making a large lift nearly free.
  `bge-base-en-v1.5` is already a well-trained retriever. The floor is far
  higher, so the visible lift will be far smaller. **Do not expect math-embed's
  0.816 vs 0.461.** A 10–20% relative gain in MRR would be a real result here.
- **~80%** (was 55%) that the result *means what it appears to mean*. Dropping
  the Rashi and Tosafot pairs removed the dominant leakage channel. This is the
  single biggest improvement English buys.
- **~~Unknown: pair volume.~~ RESOLVED 2026-09-24 — see `PHASE1.md`.** The
  census found **50,214 unique cross-register pairs** (Mishneh Torah 27,601,
  Shulchan Arukh 15,860, Mishnah 6,753), covering all 37 tractates and 27,573
  distinct Bavli segments. That is a floor — Shulchan Arukh, Even HaEzer is
  missing entirely from the count. Two orders of magnitude more supervision than
  math-embed had. **Volume is not the risk. Phase 2 is unblocked.**

Honest summary: v1's risk was that we would get a big number that meant nothing.
v2's risk is that we get an honest number that is small. That is the better
failure mode, but it is a real one, and Phase 1 is where we find out.

---

## E. Incident: session crash, 2026-09-24

The machine ran out of memory and Claude Code restarted, taking the session
scratchpad with it. Roughly 15 agent-runs of generated training questions,
the fetched corpus, and the corpus embeddings were lost. All findings,
decisions and the paper survived, because they were written to the repository.

**Cause, in two parts, both avoidable:**

1. Working data lived in the session scratchpad, which is session-scoped by
   definition. A 239 MB embedding array and the entire generated training set
   were stored somewhere guaranteed not to persist.
2. Fifteen agent processes were run concurrently with GPU training on a 16 GB
   machine. The same contention had already been diagnosed an hour earlier as
   the cause of a 50 s/step training rate; the conclusion drawn was too narrow
   ("wait for agents to finish") rather than the correct one ("agent fan-out
   and training cannot share this machine, and neither can fifteen agents and
   a 45 MB corpus in memory").

| # | Decision | Value |
|---|---|---|
| D49 | Agent fan-out and GPU training are **mutually exclusive** on a 16 GB machine | generate, drain, verify, *then* train — never overlap |
| D50 | **Persist generated data to the repo immediately**, never to scratch | anything costing more than a minute to recreate is written to `bert/data/` as it is produced |
| D51 | Cap concurrent agents at **5** on this hardware | fifteen Claude processes plus a loaded corpus exhausted 16 GB |
| D52 | Re-fetch and re-encode are cheap; **regenerating questions is not** | corpus ~5 min, embeddings ~25 min, questions ~15 agent-runs. Checkpoint the expensive artefact, not the cheap one |
