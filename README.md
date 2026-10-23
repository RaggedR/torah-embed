# torah-embed

A domain retrieval model for the Talmud, fine-tuned on a relevance dataset that
predates information retrieval by centuries.

## Idea

The **ein mishpat / ner mitsvah** apparatus — the cross-reference system printed
in the margins of the Vilna Talmud — maps passages of Talmudic argument to the
medieval legal codes that rule from them. It is, in effect, a large,
hand-curated, cross-register relevance dataset assembled long before anyone
spoke of "retrieval."

This project extracts **50,214** such pairs from the Sefaria link graph — of
which **27,013** connect Maimonides' *Mishneh Torah* to the Babylonian Talmud at
segment granularity, English on both sides — and uses them to fine-tune a dense
retrieval model. Measurement precedes training: the paper first establishes a
lexical/dense baseline (code-to-source MRR ≈ 0.50 for both), then shows where
fine-tuning moves the needle.

- `paper/talmud_retrieval.tex` — the write-up.
- `scripts/`, `crawl*.py` — corpus harvesting from the Sefaria API and training.
- `models/torah-embed/` — the fine-tuned model.
- `data/` — the derived corpus and the 50k+ relevance pairs (see **Data & attribution**).

## Data & attribution

All texts were obtained from the **[Sefaria](https://www.sefaria.org) API**. The
English Talmud is the **William Davidson Edition** (Koren–Steinsaltz), and the
*Mishneh Torah* and other sources are likewise from Sefaria's digitised library.

These texts are distributed by Sefaria under **Creative Commons
Attribution-NonCommercial 4.0 International (CC-BY-NC 4.0)**; the derived corpus
and relevance pairs bundled in `data/` are redistributed here under the same
terms, for non-commercial research use, with attribution to Sefaria and to the
William Davidson Talmud. If you use this data, cite Sefaria
(*Sefaria: A Living Library of Jewish Texts*) and the William Davidson Edition.

The code, scripts, and trained model in this repository are the author's own
work.
