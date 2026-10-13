# VibeMathed LLM analysis

Which vendors and models are behind the AI-in-the-loop problem resolutions tracked by
[VibeMathed](https://vibemathed.com/)? A reproducible scan of its public dataset,
broken down by AI contribution tier, verification level, and problem significance.

Read the report: **`vibemathed-llm-models.html`** (self-contained; open in a browser).

## Reproduce

Stdlib-only Python, no dependencies.

```sh
python scan_vibemathed.py
python analyze_vibemathed.py
python render_vibemathed_report.py
```

Vendor attribution mixes the semi-structured `modelMaker` field with regex mining
(`PROV_PATTERNS`) of free-text model descriptions; "Unreleased internal X model"
labels attribute to lab X. Matched spans are kept per problem (`spans`) for audit.

Headline (dataset 2026-10-13, 1276 problems): OpenAI 1120 (87.8%), Anthropic 194
(15.2%), Google DeepMind 56, Harmonic 55. 517 resolved (40.5%), 706 unreviewed,
only 14 expert-verified. Open weights appear on 6 problems.

## Layout

- `scan_vibemathed.py` — one-shot `/api/dataset` fetch.
- `analyze_vibemathed.py` — vendor/model normalization and cross-tabs
  → `data/vibemathed_analysis.json`.
- `render_vibemathed_report.py` — rebuilds only the report body from the analysis JSON.
- `data/` — committed snapshots + analysis so figures reproduce offline.
- `vibemathed-llm-models.html` — the report. Every number is generated; don't hand-edit.

## Data and license

Code: MIT (see `LICENSE`). Data: site classifications, scores, and notes are
[VibeMathed](https://vibemathed.com/methodology#the-dataset) content under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); snapshots are attributed
accordingly. Quoted paper material stays with its authors. Re-run
`scan_vibemathed.py` for a fresh snapshot.
