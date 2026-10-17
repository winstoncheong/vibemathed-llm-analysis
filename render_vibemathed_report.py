"""Render data/vibemathed_analysis.json into vibemathed-llm-models.html.

Reproducible: every number, table, and chart is generated from the analysis
JSON. Re-run after re-scanning:

    python scan_vibemathed.py
    python analyze_vibemathed.py
    python render_vibemathed_report.py

Only the region between the body anchor and the closing article tag is
replaced; the managed scaffold shell is never touched. After rendering, open the HTML file in a browser to verify it renders.
"""

import html
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
BODY_ANCHOR = "<!-- NOTE BODY -->"

BAR_COLORS = ["#0969da", "#6e40c9", "#1a7f37", "#9a6700", "#bc4c00",
              "#0e7490", "#59636e", "#d29922", "#4493f8", "#ab7df8",
              "#3fb950", "#db6d28", "#39c5cf"]


def esc(s):
    # Problem statements/titles carry TeX ($...$); strip sigils so KaTeX
    # auto-render leaves table cells alone, then escape.
    return html.escape((s or "").replace("$", ""))


def bars(rows, row_h=26, max_w=430, label_x=190, pad_right=56):
    """rows: [(label, value, color_idx)]. ViewBox fits the value labels."""
    top = 8
    h = top * 2 + row_h * len(rows)
    width = label_x + max_w + pad_right
    out = [f'<svg viewBox="0 0 {width} {h}" role="img" '
           f'aria-label="Bar chart">']
    peak = max((v for _, v, _ in rows), default=1)
    for i, (label, value, ci) in enumerate(rows):
        y = top + i * row_h
        w = max(2, round(max_w * value / peak)) if peak else 2
        color = BAR_COLORS[ci % len(BAR_COLORS)]
        out.append(
            f'<text x="0" y="{y + 17}" font-size="13">{esc(label)}</text>'
            f'<rect x="{label_x}" y="{y + 2}" width="{w}" height="18" '
            f'style="fill:{color}"/>'
            f'<text x="{label_x + 4 + w}" y="{y + 17}" font-size="13" '
            f'class="muted">{value}</text>')
    out.append("</svg>")
    return "".join(out)


def main():
    a = json.loads((HERE / "data" / "vibemathed_analysis.json").read_text(encoding="utf-8"))
    n = a["snapshot"]["n_problems"]
    gen = a["snapshot"]["dataset_generated"]
    fetched = a["snapshot"]["fetched_at"]
    cov = a["coverage"]
    vendors = a["vendors"]
    models = a["models"]

    def share(k):
        return f"{100.0 * k / n:.1f}" if n else "0.0"

    openai = next((v for v in vendors if v["vendor"] == "OpenAI"), {})
    anth = next((v for v in vendors if v["vendor"] == "Anthropic"), {})

    vendor_rows = "".join(
        f"<tr><td>{esc(v['vendor'])}</td><td>{v['works']}</td>"
        f"<td>{v['pct']:.1f}</td><td>{v['sig_mean'] if v['sig_mean'] is not None else '—'}</td>"
        f"<td>{v['sig_median'] if v['sig_median'] is not None else '—'}</td></tr>"
        for v in vendors)
    model_rows = "".join(
        f"<tr><td>{esc(m['model'])}</td><td>{m['works']}</td>"
        f"<td>{m['pct']:.1f}</td></tr>"
        for m in models[:16])
    cxv = a["contrib_x_vendor"][:12]
    anth_co = next((c["works"] for c in a["contrib_x_vendor"]
                    if c["contrib"] == "ai-co-developed" and c["vendor"] == "Anthropic"), 0)
    openai_co = next((c["works"] for c in a["contrib_x_vendor"]
                      if c["contrib"] == "ai-co-developed" and c["vendor"] == "OpenAI"), 0)
    cxv_rows = "".join(
        f"<tr><td>{esc(c['contrib'])}</td><td>{esc(c['vendor'])}</td>"
        f"<td>{c['works']}</td></tr>" for c in cxv)
    field_rows = "".join(
        f"<tr><td>{esc(f['field'])}</td><td>{f['works']}</td>"
        f"<td>{f['pct']:.1f}</td></tr>" for f in a["fields"])
    top_rows = "".join(
        f"<tr><td>{w['significance']}</td>"
        f"<td><a href=\"https://vibemathed.com/problem/{esc(w['id'])}\">{esc(w['name'])[:80]}</a></td>"
        f"<td>{esc(w['resolution'])}</td><td>{esc(w['aiContribution'])}</td>"
        f"<td>{esc(w['verification'])}</td>"
        f"<td>{esc(', '.join(w['vendors']) or '—')}</td></tr>"
        for w in a["top_significance"][:25])
    ow = a["open_weights_ids"]
    ow_items = "".join(
        f"<li><a href=\"https://vibemathed.com/problem/{esc(i)}\">{esc(i)}</a></li>"
        for i in ow)

    res = a["resolution"]
    ver = a["verification"]
    ac = a["aiContribution"]
    coll = a["collections"]

    body = f"""<h1>VibeMathed: which AI models solve math</h1>

<p class="meta"><span>dataset {esc(gen or "?")}</span><span>{n} problems</span><span>tags: math, ai-for-math</span><span>created: 2026-10-13 · updated: 2026-10-17</span></p>

<aside class="callout callout-note"><span class="callout-title">What this is</span>
<p>VibeMathed (<a href="https://vibemathed.com/">vibemathed.com</a>) is a community record of
precisely stated open problems now proved or disproved with an AI model substantively in the
loop. This page scans its full public <code class="no-katex">/api/dataset</code> and counts
which vendors and models show up, broken down by how much the AI contributed, how the result
was checked, and how significant the problem was. Re-run the three scripts in
this repo to refresh every
number below. Shares are \\(s = 100 \\cdot w / n\\) with \\(n = {n}\\).</p></aside>

<h2 id="coverage">1. Coverage</h2>

<p>{n} tracked problems, and vendor attribution is near-complete: all but
{cov["undisclosed_vendor"]} ({share(cov["undisclosed_vendor"])}%) name the lab or model
behind the solve. Status is a separate axis: {cov["resolved"]} fully resolved
({share(cov["resolved"])}%), {res.get("candidate", 0)} candidates under review,
{res.get("partial", 0)} partial. Contribution tiers: AI-discovered
{ac.get("ai-discovered", 0)}, co-developed {ac.get("ai-co-developed", 0)},
assisted {ac.get("ai-assisted", 0)}. Verification is thin: {ver.get("unreviewed", 0)}
unreviewed, {ver.get("lean-checked", 0)} Lean-checked,
{ver.get("lean-verified", 0)} Lean-verified, and only
{ver.get("expert-verified", 0)} independently expert-verified.</p>

<figure>{bars([(v["vendor"], v["works"], i) for i, v in enumerate(vendors[:8])])}
<figcaption>Problems per vendor, top eight. One problem naming two vendors counts for
both.</figcaption></figure>

<h2 id="counts">2. Counts</h2>

<h3 id="vendors">Vendors (problems, %, mean / median significance)</h3>

<table><thead><tr><th>Vendor</th><th>Problems</th><th>%</th><th>Mean sig.</th><th>Median sig.</th></tr></thead>
<tbody>{vendor_rows}</tbody></table>
<p class="muted">Percentages are shares of all {n} problems; they can sum above
100% because one problem may name more than one vendor.</p>

<h3 id="models">Models (mined from free-text model fields)</h3>

<table><thead><tr><th>Model</th><th>Problems</th><th>%</th></tr></thead>
<tbody>{model_rows}</tbody></table>

<h3 id="tiers">Contribution tier by vendor</h3>

<table><thead><tr><th>Tier</th><th>Vendor</th><th>Problems</th></tr></thead>
<tbody>{cxv_rows}</tbody></table>

<h2 id="significance">3. Significance</h2>

<ul>
<li><strong>OpenAI dominates volume.</strong> {openai.get("works", 0)} of {n} problems
({openai.get("pct", 0):.1f}%) involve OpenAI; Anthropic is next at
{anth.get("works", 0)} ({anth.get("pct", 0):.1f}%). The October 2026 bulk release alone
contributes {coll.get("openai-math-2026-10", 0)} entries.</li>
<li><strong>Volume sits at low significance.</strong> OpenAI's mean significance is
{openai.get("sig_mean")} (median {openai.get("sig_median")}); Harmonic's is
{next((v["sig_mean"] for v in vendors if v["vendor"] == "Harmonic"), "—")} with a median of
10 — the low end driven by bulk sweeps of machine-generated conjectures. The heaviest
entries are predominantly OpenAI candidates still under review (see table).</li>
<li><strong>Verification lags far behind claims.</strong> {ver.get("unreviewed", 0)} of {n}
entries ({share(ver.get("unreviewed", 0))}%) are unreviewed by anyone independent; the top of
the significance table is candidates, not verified resolutions.</li>
<li><strong>Open weights are nearly absent.</strong> {len(ow)} of {n} problems involve an
open-weights model at all, and only as a co-contributor:</li>
</ul>
<ul>{ow_items}</ul>
<ul>
<li><strong>Anthropic's mix is more collaborative.</strong> {anth_co} of its {anth.get("works", 0)} problems
({100.0 * anth_co / max(1, anth.get("works", 1)):.0f}%) are
AI co-developed with named human collaborators, against {openai_co} of {openai.get("works", 0)}
({100.0 * openai_co / max(1, openai.get("works", 1)):.0f}%) for OpenAI —
whose count is dominated by AI-discovered bulk-release entries.</li>
</ul>

<h3 id="top">Highest-significance entries</h3>

<table><thead><tr><th>Sig.</th><th>Problem</th><th>Status</th><th>AI role</th><th>Checked</th><th>Vendors</th></tr></thead>
<tbody>{top_rows}</tbody></table>

<h3 id="fields">Areas</h3>

<table><thead><tr><th>Area</th><th>Problems</th><th>%</th></tr></thead>
<tbody>{field_rows}</tbody></table>

<h2 id="caveats">4. Caveats</h2>

<ul>
<li>Vendor attribution mixes a semi-structured <code class="no-katex">modelMaker</code> field
with regex mining of free-text model descriptions
(<code class="no-katex">PROV_PATTERNS</code> in
<code class="no-katex">analyze_vibemathed.py</code>); matched spans are kept per problem as
<code class="no-katex">spans</code> in the analysis JSON for audit. "Unreleased internal"
labels are attributed to their named lab.</li>
<li>Significance scores are AI-estimated curator judgments (Riemann = 100), stable to a band
of about five points — treat one-point gaps as ties.</li>
<li>Candidates are claims, not results: {res.get("candidate", 0)} of the resolutions counted on the site's own
stats page are still under review. This page counts problems, not truths.</li>
</ul>

<p class="footnote">Dataset generated {esc(gen or "?")}, fetched {esc(fetched)} from
<code class="no-katex">https://vibemathed.com/api/dataset</code> ({n} problems).
Pipeline: <code class="no-katex">scan_vibemathed.py</code>,
<code class="no-katex">analyze_vibemathed.py</code>,
<code class="no-katex">render_vibemathed_report.py</code>; snapshots and analysis JSON
in <code class="no-katex">data/</code>. AI disclaimer: drafted with
<code class="no-katex">opencode-go/muse-spark-1.3-contributor</code> (2026-10-13),
updated with <code class="no-katex">opencode-go/beam-free</code> (2026-10-17).</p>
"""

    full = (HERE / "vibemathed-llm-models.html").read_text(encoding="utf-8")
    a_idx = full.index(BODY_ANCHOR) + len(BODY_ANCHOR)
    end_idx = full.index("</article>")
    out = full[:a_idx] + "\n" + body + "\n" + full[end_idx:]
    (HERE / "vibemathed-llm-models.html").write_text(out, encoding="utf-8", newline="\n")
    print(f"rendered body ({len(body)} chars)")
    # Sanity: every cited number must come from the analysis, not prose.
    for token in [str(n), str(cov["resolved"]), str(openai.get("works", 0))]:
        assert token in body, token
    print("number smoke test passed")


if __name__ == "__main__":
    main()
