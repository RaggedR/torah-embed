# Phase 2a pilot — semantic chunking of Berakhot

**Run:** 2026-09-24. 8 Sonnet sub-agents, 4 amudim each, Berakhot 2a–17b.
**Verifier:** `validate_chunks.py`, written *before* the results landed so the
acceptance criteria could not drift toward whatever the agents produced.

## Results (24/32 amudim at time of writing)

| Check | Result |
|---|---|
| Partition invariant | **0 failures / 155 chunks** |
| Hard heading leaks (names a later code) | **0** |
| Soft flags (normative language) | 1 — inspected, in-text, clean |
| Merge ratio | 26.4 segments → 6.5 chunks per amud |
| Segments per chunk | mean 3.9, median 3, max 17 |
| Words per chunk | mean 312, median 275, **max 1,272** |

The distribution is the point: neither 1.0 chunks/amud (agents defaulting to the
whole amud) nor 26.4 (agents not merging at all). They read the text.

Sample heading:

> *Berakhot 2b, continuing the proof begun on 2a: whether 'the sun sets and he
> is purified' refers to the start of sunset or its completion.*

A chunk that knows it begins mid-argument and says so. That is context a
retrieval model has no other way to obtain, and it is what §6's heading
requirement was for.

## Finding 1 — the context window reverses (again)

**34% of chunks exceed a 512-token window; the longest is 1,272 words ≈ 1,700
tokens.**

This reverses the conclusion recorded in `THIN-SLICE.md`, which observed 99-word
segments and concluded chunking was unnecessary and `nomic-embed-text-v1.5`'s
8192-token window had "largely evaporated" as an argument. Merging to real
argument boundaries puts a third of the corpus past `bge-base-en-v1.5`'s limit.

**Consequence: the Phase 3 bake-off is no longer optional, and its question
changes.** Not "which model scores better on MTEB" but "which model can
represent a sugya without truncating it". Truncation is silent — no error, just
the end of every long argument quietly dropped from the index.

Order of operations mattered here. Had the base model been fixed while segments
looked short, semantic chunking would have invisibly gutted a third of the index.

## Finding 2 — a prompt defect, surfaced only by self-report

`chunker-00` reported splitting two long dialectic runs "for size". That is
contrary to the instruction to cut on argument boundaries and prefer the larger
chunk when unsure.

The fault is in the prompt. It said *"an amud of ~15 segments usually yields 2-5
chunks"*, and that number became a target competing with the boundary rule.

**Fix for the full run: delete the numeric guidance.** Keep only "if two adjacent
passages belong to one argument, keep them together", and let chunk count fall
where the text puts it. Replace the anti-default guard with a distribution check
after the fact rather than a hint in the prompt.

Not universal: `chunker-02` kept a 15-segment digression on divine anger whole,
and `chunker-06` kept an 8-segment objection-resolution chain whole, both citing
the prefer-larger rule. One agent in eight leaned on the size prior.

**Method note.** No mechanical check would have caught this. A size-motivated
split partitions perfectly, and 6.5 chunks/amud looks healthy either way. It
surfaced only because the agents were asked what they were unsure about.
**Always ask subagents for their uncertainties, not just their output.**

## Still outstanding

- Batches 04–05 (Berakhot 10a–13b).
- The A/B that decides everything: re-run the thin slice over sugya chunks and
  compare MRR and R@1 against the 81,481-segment baseline. Per `PLAN.md` §8,
  if it does not move, semantic chunking is aesthetic and gets abandoned.

---

## Final pilot result — 8/8 batches

| Check | Result |
|---|---|
| Amudim | 32/32 |
| Chunks | 216 |
| Partition failures | **0** |
| Hard heading leaks | **0** |
| Merge ratio | 26.4 segments → 6.8 chunks/amud |
| Words per chunk | mean 311, max 1,272 |

Zero partition failures across 216 chunks from eight independent agents. The
design that bought this: agents return **ref ranges, never text**, and the
verifier was written before the results landed.

## Finding 3 — the output format was severing sugyot at every daf break

`chunker-04b` reported three sugyot in four amudim running across the amud
boundary, which it had to split because the format demanded the partition close
within each amud. See `PLAN.md` §6 correction 2 for the fix (a
`continues_previous` flag plus a mechanical merge pass).

This was my design error, it was systematic rather than occasional, and no
mechanical check would have found it — a severed sugya partitions perfectly.
Like Finding 2, it surfaced only because the agents were asked what they were
unsure about. That is now twice in one pilot.

## A/B on the prompt fix

Berakhot 10a-11b, 123 segments, identical input:

| Amud | segs | original prompt | corrected prompt |
|---|---:|---:|---:|
| 10a | 32 | 8 | 7 |
| 10b | 41 | 10 | 7 |
| 11a | 27 | 7 | 4 |
| 11b | 23 | 5 | 5 |
| **Total** | 123 | **30** | **23** |

23% fewer chunks, never more on any amud, mean chunk 322 → 420 words.
Original preserved at `chunkwork/batch04-ORIGINAL-PROMPT.json`.

## Verdict on the pilot

Mechanically sound: the protocol produces verifiable, uncorrupted partitions
with contextual headings and no label leakage. Two design defects found and
fixed. **Whether it improves retrieval is still unanswered** — that is the A/B
against the segment baseline, gated in `PLAN.md` §8, and it remains the only
test that matters.
