#!/usr/bin/env python3
"""Signal normalizer — merge pluggable source adapters into one candidate list.

Takes one or more source-adapter JSON files (each conforming to the §统一候选品
schema in SKILL.md) and produces a single normalized-candidates.json that the
downstream four-step validation consumes. The normalizer is the ONLY place that
needs editing when a new source is added — register its metric in
SOURCE_METRIC_MAP below.

What it does:
  1. Load every source file; collect all CandidateSignal entries.
  2. Score each candidate's source_metric into a 0-100 "signal strength" via the
     per-source rule in SOURCE_METRIC_MAP.
  3. Dedupe by a normalized generalized_concept key. Multi-source hits on the
     same concept are a STRONGER signal -> their strengths combine (capped).
  4. Apply hard filters (brand-locked / gift cards / services / Amazon devices).
  5. Assign recommendation_tier: priority / watch / avoid.
  6. Emit normalized-candidates.json (+ a short human summary to stdout).

Usage:
  normalize_signals.py source-amazon.json [source-tiktok.json ...] \
      --out normalized-candidates.json [--top 8]
"""
from __future__ import annotations
import argparse, json, re, sys, datetime
from pathlib import Path

# ── Registration point for new sources ──────────────────────────────────────
# Each entry: source_id -> function(source_metric: dict) -> strength 0..100.
# When you add a new adapter, add ONE line here describing how its metric maps
# to a comparable strength. Everything else downstream is untouched.
def _amazon_rank(m):
    # smaller rank = stronger. rank 1 -> ~100, rank 100 -> ~10.
    r = m.get("rank")
    if not r: return 40.0
    return max(5.0, min(100.0, 105.0 - float(r)))

def _views(m):
    v = m.get("views") or m.get("play_count") or 0
    # log-ish buckets for short-video play counts
    for thr, s in [(5_000_000,100),(1_000_000,85),(300_000,70),(50_000,55),(10_000,40)]:
        if v >= thr: return float(s)
    return 25.0

def _search_volume(m):
    sv = m.get("search_volume") or 0
    for thr, s in [(100_000,100),(30_000,85),(10_000,70),(3_000,55),(500,40)]:
        if sv >= thr: return float(s)
    return 25.0

SOURCE_METRIC_MAP = {
    "amazon-bestsellers": _amazon_rank,
    "amazon-movers": _amazon_rank,
    "tiktok-creative": _views,
    "sellersprite-api": _search_volume,
    # add new sources here, e.g. "independent-sites": _some_rule,
}
DEFAULT_STRENGTH = 35.0  # unknown source -> neutral-ish

# ── Hard filters (reject as directly-sellable) ──────────────────────────────
REJECT_PATTERNS = re.compile(
    r"\b(gift\s?card|pharmacy|prescription|subscription|streaming|service|warranty plan)\b", re.I)
AMAZON_DEVICE = re.compile(r"\b(echo|fire tv|kindle|alexa|ring|blink|eero)\b", re.I)


def norm_key(concept: str) -> str:
    s = (concept or "").lower().strip()
    s = re.sub(r"[^a-z0-9一-鿿 ]+", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def strength_for(c: dict) -> float:
    fn = SOURCE_METRIC_MAP.get(c.get("source", ""))
    try:
        return fn(c.get("source_metric") or {}) if fn else DEFAULT_STRENGTH
    except Exception:
        return DEFAULT_STRENGTH


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+", help="一个或多个 source-adapter JSON")
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=8, help="输出多少个候选品(按分排序)")
    args = ap.parse_args()

    merged = {}  # norm_key -> aggregated candidate
    src_files = []
    for sp in args.sources:
        d = json.load(open(sp, encoding="utf-8"))
        src_files.append({"source": d.get("source", Path(sp).stem),
                          "captured_at": d.get("captured_at")})
        for c in d.get("candidates", []):
            concept = c.get("generalized_concept") or c.get("raw_name")
            if not concept:
                continue
            key = norm_key(concept)
            st = strength_for(c)
            if key not in merged:
                merged[key] = {
                    "generalized_concept": concept,
                    "sources": [],
                    "signal_types": set(),
                    "brand_locked": bool(c.get("brand_locked")),
                    "raw_names": [],
                    "raw_urls": [],
                    "categories": set(),
                    "risk_notes": [],
                    "notes": [],
                    "_strength": 0.0,
                    "_hits": 0,
                }
            e = merged[key]
            e["sources"].append(c.get("source"))
            if c.get("signal_type"): e["signal_types"].add(c["signal_type"])
            e["brand_locked"] = e["brand_locked"] or bool(c.get("brand_locked"))
            if c.get("raw_name"): e["raw_names"].append(c["raw_name"])
            if c.get("raw_url"): e["raw_urls"].append(c["raw_url"])
            if c.get("category"): e["categories"].add(c["category"])
            e["risk_notes"] += c.get("risk_notes", []) or []
            e["notes"] += c.get("notes", []) or []
            # multi-source: combine strengths with diminishing returns
            e["_hits"] += 1
            e["_strength"] = min(100.0, e["_strength"] + st * (1.0 if e["_hits"] == 1 else 0.5))

    # build final candidates with filters + tier
    out_candidates = []
    for key, e in merged.items():
        concept = e["generalized_concept"]
        rejected = None
        if REJECT_PATTERNS.search(concept) or any(REJECT_PATTERNS.search(n) for n in e["raw_names"]):
            rejected = "service/giftcard/subscription"
        elif e["brand_locked"] or AMAZON_DEVICE.search(concept) or any(AMAZON_DEVICE.search(n) for n in e["raw_names"]):
            # brand-locked stays as a trend direction / accessory idea, not direct private-label
            rejected = "brand_locked"
        # multi-source bonus already in strength; tier by strength + reject status
        strength = round(e["_strength"], 1)
        if rejected == "service/giftcard/subscription":
            tier = "avoid"
        elif rejected == "brand_locked":
            tier = "watch"  # convert-to-accessory candidate
        elif strength >= 70:
            tier = "priority"
        elif strength >= 45:
            tier = "watch"
        else:
            tier = "avoid"
        out_candidates.append({
            "generalized_concept": concept,
            "recommendation_tier": tier,
            "signal_strength": strength,
            "source_hits": e["_hits"],
            "sources": sorted(set(s for s in e["sources"] if s)),
            "signal_types": sorted(e["signal_types"]),
            "brand_locked": e["brand_locked"],
            "reject_reason": rejected,
            "categories": sorted(e["categories"]),
            "raw_urls": e["raw_urls"][:3],
            "risk_notes": sorted(set(e["risk_notes"])),
            "notes": sorted(set(e["notes"]))[:4],
        })

    out_candidates.sort(key=lambda x: (x["recommendation_tier"] != "priority",
                                       -x["signal_strength"]))
    result = {
        "schema": "normalized-candidates/v1",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "input_sources": src_files,
        "candidate_count": len(out_candidates),
        "candidates": out_candidates[:args.top] if args.top else out_candidates,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # human summary
    print(f"归一化完成: {len(src_files)} 个源 -> {len(out_candidates)} 个候选(去重后), 输出 top {min(args.top,len(out_candidates))}")
    for c in result["candidates"]:
        tag = {"priority":"🟢","watch":"🟡","avoid":"🔴"}.get(c["recommendation_tier"],"·")
        multi = f" [{c['source_hits']}源命中]" if c["source_hits"] > 1 else ""
        rej = f" (拒:{c['reject_reason']})" if c["reject_reason"] else ""
        print(f"  {tag} {c['signal_strength']:>5}  {c['generalized_concept']}{multi}{rej}")
    print(f"\n写入: {args.out}")


if __name__ == "__main__":
    main()
