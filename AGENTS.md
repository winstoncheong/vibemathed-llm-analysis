# AGENTS.md — vibemathed-llm-analysis

Reproducible scan of vendor/model use in VibeMathed AI-solved problems
(https://vibemathed.com/). Stdlib-only Python; no dependencies.

## Pipeline (in order)

```sh
python scan_vibemathed.py
python analyze_vibemathed.py
python render_vibemathed_report.py
```

## Rules

- Every number in `vibemathed-llm-models.html` is generated. Never hand-edit figures;
  change `analyze_vibemathed.py` or `render_vibemathed_report.py` and re-render.
- `render_vibemathed_report.py` replaces only the region between `<!-- NOTE BODY -->`
  and `</article>`. Never touch the managed head (stylesheet, theme, KaTeX glue).
- After rendering, open the HTML in a browser: all math must render (no red
  literal `\commands`, no `.katex-error`). Math lives in text nodes as
  `$…$`/`\(…\)`, never inside `<code>` (use `<code class="no-katex">` for literals).
- Titles carry TeX `$…$`: strip the sigils before putting them in tables, or KaTeX
  auto-render will try to typeset them.
- Bar charts: the SVG `viewBox` must fit the longest value label — labels sit past
  the bar end, and a fixed-width box clips the maximum bar's number (seen before).
- Vendor attribution mixes the semi-structured `modelMaker` field with regex mining
  (`PROV_PATTERNS`) of free-text `model`/`aiRole`. "Unreleased internal X model"
  labels attribute to lab X. Matched spans are kept per problem as `spans` — audit
  them after any pattern change.
- Resolution status (resolved/candidate/partial) and vendor coverage are independent
  axes — never phrase one as the other.
- Data discipline: the dated snapshot (`data/vibemathed_<date>.json`) is the artifact
  of record — commit it, never edit it. `vibemathed_latest.json` is the working copy.
  Site content is CC BY 4.0; keep the attribution in README.md.
- Commit messages: short summary line; no secrets in repo (`.gitignore` covers
  `__pycache__`).
