"""Fetch the public VibeMathed dataset and save a timestamped snapshot.

Reads:  GET https://vibemathed.com/api/dataset (one JSON document).
Writes: data/vibemathed_<UTC date>.json  +  data/vibemathed_latest.json

Stdlib only. Run:  python scan_vibemathed.py [--out data]
"""

import argparse
import datetime
import json
import pathlib
import urllib.request

URL = "https://vibemathed.com/api/dataset"
UA = "notes-research/1.0 (reproducible archive scan; contact via repo)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    here = pathlib.Path(__file__).resolve().parent
    outdir = here / args.out
    outdir.mkdir(parents=True, exist_ok=True)

    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dataset = json.load(resp)

    stamp = datetime.datetime.now(datetime.timezone.utc)
    snapshot = {
        "fetched_at": stamp.isoformat(timespec="seconds"),
        "source": URL,
        "dataset_generated": dataset.get("generated"),
        "count_reported": dataset.get("count"),
        "n_problems": len(dataset.get("problems", [])),
        "problems": dataset.get("problems", []),
    }
    day = stamp.strftime("%Y%m%d")
    dated = outdir / f"vibemathed_{day}.json"
    latest = outdir / "vibemathed_latest.json"
    dated.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    latest.write_text(json.dumps(snapshot, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"wrote {dated} ({snapshot['n_problems']} problems)")
    print(f"wrote {latest}")


if __name__ == "__main__":
    main()
