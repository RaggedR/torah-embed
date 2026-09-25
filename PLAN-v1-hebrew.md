# torah-embed — a BERT embedding model for talmudic retrieval

**Status:** plan, not started. Written 2026-09-24.
**Model after:** `~/git/embeddings` (math-embed), whose recipe this reuses almost
component-for-component.

---

## 1. Goal

Train a domain-specific sentence-embedding model over the classical Jewish canon
— Tanakh, Mishnah, Talmud Bavli, and the major commentary and halakhic layers —
so that a RAG system can retrieve *the right sugya* for a query, rather than
passages that merely share vocabulary with it.

The target capability, stated as a test: given a halakhic ruling in Mishneh
Torah or Shulchan Aruch, retrieve the talmudic passage it derives from. That
pair shares almost no surface vocabulary — terse medieval Hebrew against
discursive Babylonian Aramaic — so a lexical baseline (BM25) loses badly and a
genuine semantic retriever wins. It is the sharpest available discriminator
between the two.

### What this is *not*

Not a generative model. Not a chavruta that argues back. An encoder that maps
text to a vector, nothing more. Generation, if it happens, is a separate layer
on top and sits outside this plan.

---

## 2. Why the Talmud suits this recipe better than the maths papers did

The math-embed ground truth was approximate: a knowledge-graph concept mapped to
*every chunk of every relevant paper*, which is why Recall@20 sat at 3–4% and
MRR/NDCG had to carry the comparison. Sefaria's links are **segment-to-segment
and hand-curated by editors**. The ground truth stops being a proxy and becomes
the actual object. Recall@K should become a usable metric again.

There is also a strong method prior. SPECTER2 — the math-embed base — works by
contrastive training on *citation triplets* over SciBERT. Sefaria's link graph
is a citation graph, and BEREL is the rabbinic SciBERT. Doing to BEREL what
AllenAI did to SciBERT is a known-good move, not a hope.

### Component mapping

| math-embed | torah-embed |
|---|---|
| `allenai/specter2_base` | `dicta-il/BEREL` |
| 4,794 chunks in ChromaDB | ~500k segments (estimate — to be measured) |
| 559 KG concepts, hand-constructed | Sefaria link graph, ~2M+ links, shipped |
| (concept, chunk) pairs | (citing text, cited text) pairs |
| 108 queries; concept → papers → chunks | held-out links, split by tractate |
| MNRL + MatryoshkaLoss | same |
| MRR / NDCG@10 | same, plus Recall@K |

The Rust layer (`cosine.rs`, `knn.rs`, `metrics.rs`) and the `EmbeddingModel`
ABC carry over unchanged. Only the data pipeline is new.

---

## 3. Sources

Sefaria is the centre of gravity: a structured, linked digital library with a
public API, bulk exports, and now a `sefaria-mcp` server and a `Sefaria/LLM`
repo — they are actively building for this use case.

| Text | Language | Licence |
|---|---|---|
| Tanakh, Mishnah, Talmud Bavli/Yerushalmi | Hebrew / Aramaic | public domain |
| Rashi, Tosafot, Ramban, Rif, Rosh | Hebrew | public domain |
| Mishneh Torah, Shulchan Aruch, Tur | Hebrew | public domain |
| Steinsaltz / William Davidson Talmud (English) | English | **CC-BY-NC** |
| JPS 1917 Tanakh (English) | English | public domain |

**Do not clone `Sefaria-Export-Archive`.** It is 7.9 GB of git history covering
every text in every language and version, and it is now archived. Pull the
fifteen or so works we need via the API or a sparse checkout: ~1.5 GB.

Known gap: the Bar-Ilan Responsa Project (the largest *she'elot u-teshuvot*
corpus) is proprietary. Out of scope.

---

## 4. Base model

**`dicta-il/BEREL`** — BERT pretrained on the rabbinic corpus itself. Correct
vocabulary, correct orthographic conventions, handles Aramaic. This is the
`specter2_base` slot. (`BEREL_2.0` currently returns an HTTP redirect — resolve
where it points before pinning a revision.)

Two things to expect:

- **The first benchmark run will look terrible, and that is correct.** BEREL is
  a raw MLM encoder, never trained for sentence similarity. Mean-pooled MLM BERT
  embeddings are poor out of the box — the founding observation of the SBERT
  paper. It is an argument for the fine-tune, not against the base.
- **BEREL is also the only base that trains on this machine.** 16 GB unified
  memory. BERT-base at 110M parameters needs ~1.8 GB of optimizer state and fits
  easily at `--batch-size 8 --grad-accum 4`. `bge-m3` at 568M would need ~9 GB
  before activations. Use the large multilingual models as **frozen inference
  baselines only**.

Baselines to beat (the `openai-small` row): `BAAI/bge-m3`,
`intfloat/multilingual-e5-large`. Both handle Hebrew and are contrastively
trained; one may well beat un-tuned BEREL outright.

---

## 5. Training pairs

Sefaria's links are *typed*, and the types are not equally useful.

| Pair type | Volume | Signal | Risk |
|---|---|---|---|
| Mishneh Torah / Shulchan Aruch → talmudic source | ~10k+ | **semantic, cross-register** | none — this is the gold set |
| Parallel sugyot across tractates | moderate | high | none |
| Mishnah → its Gemara sugya | ~4k | structural | low |
| Rashi / Tosafot → daf segment | very high | high | **lexical leakage — see below** |
| Verse → midrash or talmudic citation | high | topical | verse quoted verbatim |
| (Aramaic segment, its English translation) | very high | cross-lingual alignment | licence — see §7 |

### The poisoned well

Rashi's comments open with a *dibbur hamatchil* — the lemma, **copied verbatim
from the daf**. Train on (Rashi, daf) pairs without stripping it and the result
is not a semantic retriever but a substring-matcher that scores ~0.95 on the
benchmark and collapses on real queries. The same applies to verse→midrash
pairs, where the verse is quoted in full.

Mitigation, and it is not optional:

1. Strip the *dibbur hamatchil* from every commentary anchor.
2. Hold out a separately lemma-stripped eval split and report on it.
3. Report a BM25 baseline on the same split. If BM25 is close, the model has
   learned lexical overlap and the result means nothing.

This is the same class of failure as the math-embed directory-prefix mismatch
(`core/file.pdf` vs `file.pdf`): a data-hygiene detail that silently decides
whether the headline number means anything at all.

### Hard negatives

MNRL's in-batch negatives are random passages, which in this corpus is trivially
easy — a random segment is from another tractate on another subject entirely.
Mine negatives from the **same daf or the adjacent sugya** that are *not* linked.
Without them the model learns "purity or torts?", not "is this the source of
that ruling?".

---

## 6. Chunking

Not by daf. A daf runs ~800–1000 words and holds several unrelated sugyot; it
would blur exactly the way over-broad paper-level ground truth did in math-embed.

Sefaria's native segmentation (Steinsaltz's) is roughly sugya-aligned and is
already the unit the links point at. **Take the segment as given.** BEREL's limit
is 512 tokens; long sugyot need splitting with overlap — the job `rechunk.py`
already does.

Normalisation, before anything else: strip nikkud and te'amim (Tanakh is
vocalised, the Talmud is not — the mismatch would hurt), and expand rabbinic
abbreviations (ר״ל, ת״ש, קמ״ל) rather than letting them tokenise as garbage.
Dicta publish tooling for both.

---

## 7. The open decision: which language do we embed?

Recorded as a genuine dispute, because it forks the base-model choice and it is
the first thing to settle.

**Position.** Embed the Hebrew/Aramaic. It is the primary text, it carries no
licence encumbrance, and BEREL exists precisely for it.

**Objection.** The English Davidson translation is far better served by
available encoders, queries will often arrive in English, and the Aramaic is
unvocalised, abbreviation-dense and orthographically inconsistent — we would be
fighting the data with a weaker toolchain. The Davidson translation is also
CC-BY-**NC**, and publishing a model derived from it (as `RobBobin/math-embed`
was published) raises a question worth answering first.

**Resolution.** Embed Hebrew/Aramaic as the corpus. Use the English translation
only as *training signal*: (Aramaic segment, its English translation) is a free,
perfectly aligned positive pair at enormous volume, and it pulls English queries
and Aramaic passages into a shared space. The translations become an input to
gradients rather than a component of the published artifact. This wants a
clean-hands check before release, but it is a far better position than embedding
the NC text directly.

**What actually changes.** If Hebrew/Aramaic-primary → BEREL, and cross-lingual
retrieval is a phase-2 experiment. If cross-lingual is a phase-1 requirement →
the base may have to be `bge-m3`, which does not fine-tune on 16 GB. **Settle
this before downloading anything.**

---

## 8. Evaluation

- **Split by tractate, not by link.** Splitting by link leaks: the two ends of a
  held-out link both appear in training through their other links.
- **Primary task:** Mishneh Torah / Shulchan Aruch ruling → talmudic source.
  Gold labels, cross-register, the task a lexical baseline cannot fake.
- **Secondary:** parallel-sugya retrieval; Mishnah → Gemara.
- **Metrics:** Recall@{5,10,20}, MRR, NDCG@10 — reusing the Rust `metrics.rs`
  path unchanged.
- **Mandatory baselines on every split:** BM25, un-tuned BEREL, `bge-m3`. The
  BM25 row is the lexical-leakage alarm and must be reported even when
  embarrassing.

---

## 9. Budget

Measured 2026-09-24: 46 GB genuinely free, no local APFS snapshots inflating the
figure. 16 GB unified memory.

| Component | Lean | Everything |
|---|---:|---:|
| Sefaria corpus (filtered: Hebrew + links) | 1.5 GB | 8.0 GB (full clone) |
| BEREL base | 0.5 GB | 0.5 GB |
| Baseline models | 2.3 GB | 4.5 GB |
| Training pairs (JSONL, ~2M) | 1.5 GB | 2.0 GB |
| Checkpoints | 1.0 GB | 3.0 GB |
| Final model | 0.5 GB | 0.5 GB |
| ChromaDB index (~500k segments) | 3.3 GB | 6.0 GB |
| **Total** | **~11 GB** | **~25 GB** |

Index cost is ~6.5 KB/segment at 768 dims: 3 KB vector, ~1.3 KB HNSW graph,
~2 KB text and metadata in sqlite. Calibrated against the arxiv-rag footprint
(4,794 chunks → 206 MB).

Two levers if it tightens:

- **Index at 256 dims, not 768.** We train with `MatryoshkaLoss` — this is what
  it is for. Cuts the index from 3.3 GB to ~1.8 GB. Keep the 768-dim weights.
- **Don't clone the archive.** Saves 6.5 GB on its own.

Housekeeping: `~/git/embeddings/models/waarnar-embed` is at 2.9 GB, which looks
like accumulated per-epoch checkpoints. Set `save_total_limit=2` on this run.

Disk is not the binding constraint. **Memory is** — see §4.

---

## 10. Phases

**Phase 0 — settle §7.** Nothing downloads until the language question is
answered, because it decides the base model.

**Phase 1 — measure.** Pull the Sefaria links dump. Count links by type, count
segments, measure the real size distribution. Replaces every estimate in this
document with a number. Deliverable: a table of pair volumes per category, and
an answer to whether the Rambam→Talmud set is large enough to carry the model
alone or needs the Rashi pairs as bulk. ~1 afternoon.

**Phase 2 — pipeline.** Normalisation, segmentation, lemma stripping, pair
generation, hard-negative mining. The bulk of the real engineering, and where
the risk lives.

**Phase 3 — baselines.** BM25, un-tuned BEREL, `bge-m3` on the eval splits.
Establishes the floor *before* training, so the lift is honest.

**Phase 4 — train.** MNRL + MatryoshkaLoss on BEREL. Reuses `train.py` with a
new data loader.

**Phase 5 — benchmark and write up.** `bench.py` with a new model wrapper;
paper alongside `paper/math_embeddings.tex`.

---

## 11. Confidence

- **~85%** that this substantially beats `bge-m3` and un-tuned BEREL on
  held-out link retrieval. The method is proven in our own repo and the
  supervision here is stronger.
- **~55%** that a first result *means what it appears to mean*. The lexical
  leakage trap is severe enough that a careless run yields an impressive and
  worthless MRR. Most of the engineering risk is in pair hygiene and
  hard-negative mining, not in training.
- **Low** on cross-lingual retrieval quality without experiment. Phase 2 at the
  earliest.

The honest summary: the training is the easy part. The corpus is small, the
supervision is excellent, the base model is right, and the hardware is
sufficient. Everything that can go wrong goes wrong in the data.
