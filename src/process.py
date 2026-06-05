#!/usr/bin/env python3
"""Fetch and process Google's Schema.org usage statistics.

Data source: https://schema.org/docs/usage_stats.html
Buckets are domain-count tiers (how many distinct domains use a term),
NOT exact usage counts. A higher bucket means wider adoption.
"""
import csv
import json
import os
import urllib.request
from collections import defaultdict

PERIOD = "2026_05"
RAW = "https://raw.githubusercontent.com/schemaorg/schemaorg/main/data/public_stats/google"
FILES = {
    "csv": f"{RAW}/{PERIOD}.csv",
    "json": f"{RAW}/{PERIOD}.json",
    "summary": f"{RAW}/summary_{PERIOD}.json",
}

# Ordered from least to most adopted.
BUCKETS = ["< 1K", "1K - 10K", "10K - 100K", "100K - 1M", "1M - 10M", "10M+"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DIST_DIR = os.path.join(ROOT, "dist")


def fetch():
    os.makedirs(DATA_DIR, exist_ok=True)
    for kind, url in FILES.items():
        ext = "json" if kind != "csv" else "csv"
        name = f"summary_{PERIOD}.json" if kind == "summary" else f"{PERIOD}.{ext}"
        dest = os.path.join(DATA_DIR, name)
        print(f"fetch {url} -> {dest}")
        urllib.request.urlretrieve(url, dest)


def short(name):
    return name.rstrip("/").split("/")[-1]


def process():
    csv_path = os.path.join(DATA_DIR, f"{PERIOD}.csv")
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    # by[class][bucket] = [term, ...]
    by = defaultdict(lambda: defaultdict(list))
    tidy = []
    for r in rows:
        cls, bucket = r["Class"], r["Domain Bucket"]
        term = short(r["Name"])
        by[cls][bucket].append(term)
        tidy.append({"class": cls, "term": term, "url": r["Name"], "bucket": bucket})

    os.makedirs(DIST_DIR, exist_ok=True)

    # Tidy CSV.
    with open(os.path.join(DIST_DIR, "processed.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["class", "term", "url", "bucket"])
        w.writeheader()
        w.writerows(tidy)

    # Chart data the dashboard consumes.
    chart = {"period": PERIOD, "buckets": BUCKETS, "classes": {}}
    for cls in ("Itemtype", "Predicate"):
        counts = [len(by[cls].get(b, [])) for b in BUCKETS]
        chart["classes"][cls] = {
            "counts_per_bucket": counts,
            "total": sum(counts),
            "top_10M": sorted(by[cls].get("10M+", [])),
            "top_1M_10M": sorted(by[cls].get("1M - 10M", [])),
            "long_tail": len(by[cls].get("< 1K", [])),
        }
    with open(os.path.join(DIST_DIR, "chart_data.json"), "w") as f:
        json.dump(chart, f, indent=2)

    print(f"rows: {len(rows)}")
    for cls, d in chart["classes"].items():
        print(f"  {cls}: total={d['total']} 10M+={len(d['top_10M'])} long_tail={d['long_tail']}")
    print(f"wrote {DIST_DIR}/processed.csv and chart_data.json")


if __name__ == "__main__":
    import sys
    if "--no-fetch" not in sys.argv:
        fetch()
    process()
