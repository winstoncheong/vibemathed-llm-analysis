"""Analyse a VibeMathed snapshot: which LLM/AI models solve math, counts, significance.

Reads:  data/vibemathed_latest.json  (from scan_vibemathed.py)
Writes: data/vibemathed_analysis.json

Stdlib only. Run:  python analyze_vibemathed.py

Two vendor signals, both reported. `modelMaker` is semi-structured
("OpenAI / Anthropic", "OpenAI; Anthropic; Zhipu AI", None when undisclosed).
`model` is free text ("Anthropic Fable 5.1 and OpenAI GPT-5.6 Sol Pro",
"Unreleased internal OpenAI model") and is mined with PROV_PATTERNS — regexes over free-text model/vendor fields (a sibling Hexagon pipeline
uses the same approach), extended here
for open-weights systems (DeepSeek, GLM, Kimi, Qwen) and unreleased-internal
labels. Matched spans are kept per problem as model_spans for audit.
"""

import argparse
import collections
import json
import pathlib
import re
import statistics

HERE = pathlib.Path(__file__).resolve().parent

# (kind, family, pattern). Case-insensitive; (?-i:...) pins case-sensitive
# alternatives. Bare "opus"/"sage" are ordinary words, so those need context.
PROV_PATTERNS = [
    ("llm", "OpenAI ChatGPT", r"chatgpt|gpt[\s-]*[56](?:[\s.]*\d)?(?:[\s-]*(?:astra|sol|luna|pro))?|astra[\s-]*6|gpt[\s-]*astra"),
    ("llm", "OpenAI Codex", r"(?-i:\bCodex\b)|\bcodex\b"),
    ("llm", "Anthropic Claude Opus", r"claude(?![\w\s-]*?(?:fable|sonnet))|opus[\s-]*5\.5|opus[\s-]*4\.8"),
    ("llm", "Anthropic Claude Fable", r"fable"),
    ("llm", "Anthropic Claude Sonnet", r"sonnet"),
    ("llm", "Anthropic Claude Code", r"claude[\s-]*code"),
    ("llm", "Google", r"gemini|deepmind"),
    ("llm", "xAI", r"grok"),
    ("llm", "Harmonic", r"aristotle|harmonic"),
    ("llm", "AxiomMath", r"axiom[\s-]*(?:math|prover)"),
    ("llm", "Frenzy Math", r"frenzy|rethlas"),
    ("llm", "Zhipu", r"zhipu|(?-i:\bZ\.ai\b)|glm|kimi"),
    ("llm", "Open-weights", r"deepseek|qwen|llama|mistral|(?-i:\bGLM\b)|(?-i:\bKimi\b)"),
    ("llm", "Meta", r"muse[\s-]*spark"),
    ("llm", "Quora Poe (aggregator)", r"(?-i:\bPoe\b)"),
    ("undisclosed", "Undisclosed", r"unreleased internal|not disclosed"),
]
PROV_RES = [(k, f, re.compile(p, re.IGNORECASE)) for k, f, p in PROV_PATTERNS]

MAKER_SPLIT = re.compile(r"\s*(?:/|;|,|\band\b)\s*", re.IGNORECASE)
UNRELEASED_RE = re.compile(r"unreleased internal ([\w][\w .+-]*?) model", re.IGNORECASE)

# Mined model families roll up to these vendors for vendor-level counts.
VENDOR_OF = {
    "OpenAI ChatGPT": "OpenAI", "OpenAI Codex": "OpenAI",
    "Anthropic Claude Opus": "Anthropic", "Anthropic Claude Fable": "Anthropic",
    "Anthropic Claude Sonnet": "Anthropic", "Anthropic Claude Code": "Anthropic",
    "Google": "Google DeepMind", "Quora Poe (aggregator)": "Quora Poe",
    "Zhipu": "Zhipu", "AxiomMath": "Axiom Math",
}


def chunk_to_vendor(chunk):
    c = re.sub(r"\s*\(.*?\)\s*", "", chunk).strip().lower()
    if not c or c in ("not disclosed",):
        return None
    if "openai" in c:
        return "OpenAI"
    if "anthropic" in c:
        return "Anthropic"
    if "deepmind" in c or c == "google":
        return "Google DeepMind"
    if "harmonic" in c:
        return "Harmonic"
    if "xai" in c or "x ai" in c:
        return "xAI"
    if "axiom" in c:
        return "Axiom Math"
    if "frenzy" in c:
        return "Frenzy Math"
    if "zhipu" in c or "z.ai" in c:
        return "Zhipu"
    if "deepseek" in c:
        return "Open-weights"
    return "Other: " + chunk.strip()[:40]


def maker_families(maker):
    """Split a modelMaker string into canonical vendor families."""
    fams = set()
    if not maker:
        return fams
    for chunk in MAKER_SPLIT.split(maker):
        v = chunk_to_vendor(chunk)
        if v:
            fams.add(v)
    return fams


def mine(text):
    fams, spans = set(), []
    for kind, fam, rx in PROV_RES:
        for m in rx.finditer(text or ""):
            fams.add((kind, fam))
            if len(spans) < 8:
                spans.append(m.group(0))
    return fams, spans


def sig_band(s):
    if s is None:
        return "unscored"
    if s >= 50:
        return "50+"
    if s >= 30:
        return "30-49"
    if s >= 10:
        return "10-29"
    if s >= 5:
        return "5-9"
    return "0-4"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/vibemathed_latest.json")
    ap.add_argument("--out", default="data/vibemathed_analysis.json")
    args = ap.parse_args()

    snap = json.loads((HERE / args.inp).read_text(encoding="utf-8"))
    ps = snap["problems"]
    n = len(ps)

    def pct(x, base=n):
        return round(100.0 * x / base, 1) if base else 0.0

    vendor_works = collections.Counter()
    mined_works = collections.Counter()
    contrib = collections.Counter()
    resolution = collections.Counter()
    verification = collections.Counter()
    method = collections.Counter()
    stype = collections.Counter()
    pub = collections.Counter()
    fields = collections.Counter()
    collection = collections.Counter()
    contrib_x_vendor = collections.Counter()
    verif_x_vendor = collections.Counter()
    resol_x_vendor = collections.Counter()
    band_x_contrib = collections.Counter()
    sig_by_vendor = collections.defaultdict(list)
    open_weights_ids = []
    undisclosed_ids = []
    per_prob = []
    resolved = 0

    for p in ps:
        pid = p.get("slug")
        makers = maker_families(p.get("modelMaker"))
        text = " ".join(str(p.get(k) or "") for k in ("model", "aiRole"))
        hits, spans = mine(text)
        mined = {f for k, f in hits if k == "llm"}
        unreleased = None
        m = UNRELEASED_RE.search(text)
        if m:
            unreleased = chunk_to_vendor(m.group(1)) or "Undisclosed"
            makers = makers | ({unreleased} if unreleased != "Undisclosed" else set())
        vendors = set(makers) | {VENDOR_OF.get(f, f) for f in mined}
        for f in vendors:
            vendor_works[f] += 1
        for f in mined:
            mined_works[f] += 1
        if any(f == "Open-weights" for f in mined) or "Open-weights" in vendors:
            open_weights_ids.append(pid)
        if not vendors:
            undisclosed_ids.append(pid)

        ac = p.get("aiContribution") or "unclassified"
        rs = p.get("resolution") or "?"
        vf = p.get("verification") or "?"
        contrib[ac] += 1
        resolution[rs] += 1
        verification[vf] += 1
        method[p.get("resolutionMethod") or "?"] += 1
        stype[p.get("solveType") or "?"] += 1
        pub[p.get("publication") or "?"] += 1
        fields[p.get("fieldGroup") or "?"] += 1
        collection[p.get("collection") or "curated"] += 1
        sig = p.get("significance")
        if isinstance(sig, (int, float)):
            for f in vendors:
                sig_by_vendor[f].append(sig)
        band_x_contrib[(sig_band(sig), ac)] += 1
        primary = sorted(vendors)[0] if vendors else "Undisclosed"
        contrib_x_vendor[(ac, primary)] += 1
        verif_x_vendor[(vf, primary)] += 1
        resol_x_vendor[(rs, primary)] += 1
        if rs == "resolved":
            resolved += 1
        per_prob.append({
            "id": pid,
            "name": p.get("shortName") or p.get("name"),
            "subject": p.get("fieldGroup"),
            "solveType": p.get("solveType"),
            "resolution": rs,
            "aiContribution": ac,
            "verification": vf,
            "method": p.get("resolutionMethod"),
            "significance": sig,
            "makers": sorted(makers),
            "vendors": sorted(vendors),
            "mined": sorted(mined),
            "unreleased": bool(unreleased),
            "spans": spans,
            "solveDate": p.get("solveDate"),
        })

    vendor_list = sorted(set(vendor_works), key=lambda f: -vendor_works[f])
    analysis = {
        "snapshot": {"fetched_at": snap.get("fetched_at"),
                     "dataset_generated": snap.get("dataset_generated"),
                     "count_reported": snap.get("count_reported"),
                     "n_problems": n},
        "coverage": {
            "n_problems": n,
            "resolved": resolved,
            "pct_resolved": pct(resolved),
            "undisclosed_vendor": len(undisclosed_ids),
            "pct_undisclosed": pct(len(undisclosed_ids)),
            "open_weights_involved": len(open_weights_ids),
        },
        "vendors": [{"vendor": v,
                     "works": vendor_works[v],
                     "pct": pct(vendor_works[v]),
                     "sig_mean": round(statistics.mean(sig_by_vendor[v]), 1) if sig_by_vendor.get(v) else None,
                     "sig_median": statistics.median(sig_by_vendor[v]) if sig_by_vendor.get(v) else None}
                    for v in vendor_list],
        "models": [{"model": m, "works": c, "pct": pct(c)}
                   for m, c in mined_works.most_common(20)],
        "open_weights_ids": sorted(open_weights_ids),
        "undisclosed_sample": sorted(undisclosed_ids)[:25],
        "aiContribution": dict(contrib),
        "resolution": dict(resolution),
        "verification": dict(verification),
        "method": dict(method),
        "solveType": dict(stype),
        "publication": dict(pub),
        "fields": [{"field": f, "works": c, "pct": pct(c)}
                   for f, c in fields.most_common(12)],
        "collections": dict(collection),
        "contrib_x_vendor": [{"contrib": c, "vendor": v, "works": k}
                             for (c, v), k in contrib_x_vendor.most_common(20)],
        "verif_x_vendor": [{"verification": c, "vendor": v, "works": k}
                           for (c, v), k in verif_x_vendor.most_common(20)],
        "resol_x_vendor": [{"resolution": c, "vendor": v, "works": k}
                           for (c, v), k in resol_x_vendor.most_common(20)],
        "bands": [{"band": b, "contrib": c, "works": k}
                  for (b, c), k in sorted(band_x_contrib.items())],
        "top_significance": sorted(
            [w for w in per_prob if isinstance(w["significance"], (int, float))],
            key=lambda w: -w["significance"])[:50],
        "per_prob": per_prob,
    }
    out = HERE / args.out
    out.write_text(json.dumps(analysis, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"problems={n} resolved={resolved} vendors={len(vendor_list)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
