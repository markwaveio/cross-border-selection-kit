#!/usr/bin/env python3
"""Render a product cross-validation JSON report as a standalone HTML dashboard."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from urllib.parse import quote_plus


DECISION_LABELS = {
    "sample_now": "优先打样",
    "validate_more": "继续验证",
    "watch": "观察",
    "avoid": "放弃",
    "convert_to_accessory": "转配件/周边",
}

# Built-in default dimensions (used when the report JSON does not declare its own).
# To ADD A NEW VALIDATION DIMENSION without touching this script, put a "dimensions"
# block in the report JSON (see references/scoring-rubric.md "扩展维度"):
#   "dimensions": [ {"key":"reviews","label":"评论情感","max":10,"evidence_label":"评论判断"}, ... ]
# The renderer then draws exactly those dimensions, in order — count-agnostic.
DEFAULT_DIMENSIONS = [
    {"key": "demand", "label": "需求强度", "max": 25, "evidence_label": "需求判断"},
    {"key": "ads", "label": "广告验证", "max": 20, "evidence_label": "广告判断"},
    {"key": "content", "label": "内容传播", "max": 15, "evidence_label": "内容判断"},
    {"key": "supplier", "label": "供应链", "max": 20, "evidence_label": "货源判断"},
    {"key": "logistics", "label": "物流合规", "max": 10, "evidence_label": "物流合规"},
    {"key": "differentiation", "label": "差异化", "max": 10, "evidence_label": "差异化"},
]


def dimensions_for(report: dict) -> list[dict]:
    """Dimensions to render. Report-declared 'dimensions' wins; else built-in six.
    Each dim: {key, label, max, evidence_label?}. evidence_label defaults to label."""
    dims = report.get("dimensions")
    if not dims:
        return DEFAULT_DIMENSIONS
    out = []
    for d in dims:
        if not d.get("key"):
            continue
        out.append({
            "key": d["key"],
            "label": d.get("label", d["key"]),
            "max": d.get("max", 0),
            "evidence_label": d.get("evidence_label", d.get("label", d["key"])),
        })
    return out or DEFAULT_DIMENSIONS


def dimensions_caption(dims: list[dict]) -> str:
    total = sum(d["max"] for d in dims)
    parts = "，".join(f"{d['label']} {d['max']}" for d in dims)
    return f"{total} 分制：{parts}。"


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def search_url(platform: str, concept: str, keywords: dict | None = None) -> str:
    english = (keywords or {}).get("english") or [concept]
    chinese = (keywords or {}).get("chinese") or [concept]
    if platform == "amazon":
        return "https://www.amazon.com/s?k=" + quote_plus(english[0])
    if platform == "facebook_ads_library":
        return (
            "https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
            f"&country=US&q={quote_plus(english[0])}&search_type=keyword_unordered"
        )
    if platform == "google_trends":
        terms = ",".join(quote_plus(term) for term in english[:2])
        return f"https://trends.google.com/trends/explore?date=today%205-y&geo=US&q={terms}"
    if platform == "1688":
        return "https://s.1688.com/selloffer/offer_search.htm?keywords=" + quote_plus(chinese[0])
    return "#"


def product_links(product: dict) -> dict:
    concept = product.get("concept") or product.get("product") or "product"
    keywords = product.get("keywords") or {}
    links = dict(product.get("links") or {})
    for platform in ["amazon", "facebook_ads_library", "google_trends", "1688"]:
        links.setdefault(platform, search_url(platform, concept, keywords))
    return links


def decision_class(decision: str) -> str:
    if decision == "sample_now":
        return "good"
    if decision in {"avoid", "convert_to_accessory"}:
        return "bad"
    return "warn"


def total_score(product: dict) -> int:
    if isinstance(product.get("total_score"), (int, float)):
        return max(0, min(100, int(product["total_score"])))
    scores = product.get("scores") or {}
    return max(0, min(100, int(sum(v for v in scores.values() if isinstance(v, (int, float))))))


def score_rows(product: dict, dims: list[dict]) -> str:
    scores = product.get("scores") or {}
    rows = []
    for d in dims:
        value = int(scores.get(d["key"]) or 0)
        max_value = d["max"]
        width = 0 if not max_value else round((value / max_value) * 100)
        rows.append(
            f"<div class=\"score-row\"><span>{esc(d['label'])}</span>"
            f"<div class=\"bar\"><span style=\"width:{width}%\"></span></div>"
            f"<b>{value}/{max_value}</b></div>"
        )
    return "".join(rows)


def evidence_boxes(product: dict, dims: list[dict]) -> str:
    evidence = product.get("evidence") or {}
    boxes = []
    for d in dims:
        boxes.append(
            f"<div class=\"logic-box\"><strong>{esc(d['evidence_label'])}</strong>"
            f"<p>{esc(evidence.get(d['key']) or 'Manual confirmation needed.')}</p></div>"
        )
    return "".join(boxes)


def list_items(values) -> str:
    values = [value for value in (values or []) if value]
    if not values:
        return "<p class=\"muted\">No items provided.</p>"
    return "<ul>" + "".join(f"<li>{esc(value)}</li>" for value in values) + "</ul>"


def link_buttons(product: dict) -> str:
    links = product_links(product)
    labels = {
        "amazon": "Amazon",
        "facebook_ads_library": "Ads Library",
        "google_trends": "Google Trends",
        "1688": "1688",
        "tiktok": "TikTok",
        "youtube": "YouTube",
        "aliexpress": "AliExpress",
    }
    buttons = []
    for key, url in links.items():
        buttons.append(
            f"<a class=\"link-btn\" href=\"{esc(url)}\" target=\"_blank\" rel=\"noreferrer\">"
            f"{esc(labels.get(key, key))}</a>"
        )
    return "".join(buttons)


def ranking_rows(products: list[dict]) -> str:
    rows = []
    for index, product in enumerate(sorted(products, key=total_score, reverse=True), start=1):
        decision = product.get("decision") or "validate_more"
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td><strong>{esc(product.get('concept') or 'Untitled product')}</strong></td>"
            f"<td><strong>{total_score(product)}</strong></td>"
            f"<td><span class=\"badge {decision_class(decision)}\">{esc(DECISION_LABELS.get(decision, decision))}</span></td>"
            f"<td>{esc(product.get('recommended_product') or '')}</td>"
            "</tr>"
        )
    return "".join(rows)


def product_card(product: dict, dims: list[dict]) -> str:
    decision = product.get("decision") or "validate_more"
    return f"""
      <article class="card">
        <div class="card-top">
          <h3>{esc(product.get("concept") or "Untitled product")}</h3>
          <span class="badge {decision_class(decision)}">{total_score(product)} / {esc(DECISION_LABELS.get(decision, decision))}</span>
        </div>
        <div class="score">{score_rows(product, dims)}</div>
        <div class="logic">{evidence_boxes(product, dims)}</div>
        <div class="panel-lite">
          <strong>建议产品</strong>
          <p>{esc(product.get("recommended_product") or "Define a specific testable product angle before sampling.")}</p>
        </div>
        <div class="panel-lite">
          <strong>主要风险</strong>
          {list_items(product.get("risks"))}
        </div>
        <div class="panel-lite">
          <strong>下一步</strong>
          {list_items(product.get("next_actions"))}
        </div>
        <div class="links">{link_buttons(product)}</div>
      </article>
    """


def render(report: dict) -> str:
    products = list(report.get("products") or [])
    dims = dimensions_for(report)
    caption = dimensions_caption(dims)
    sample_count = sum(1 for product in products if product.get("decision") == "sample_now")
    validate_count = sum(1 for product in products if product.get("decision") == "validate_more")
    watch_count = sum(1 for product in products if product.get("decision") in {"watch", "convert_to_accessory"})
    avoid_count = sum(1 for product in products if product.get("decision") == "avoid")
    method_notes = report.get("method_notes") or [
        "Use direct platform links for manual verification when live platform data cannot be read."
    ]

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>选品交叉验证报告</title>
  <style>
    :root {{ --bg:#f6f7f8; --panel:#fff; --ink:#17202a; --muted:#65717f; --line:#dde4eb; --blue:#1463ff; --blue-soft:#e9f0ff; --green:#0b7a4b; --green-soft:#e8f7ef; --amber:#a15c00; --amber-soft:#fff1db; --red:#b42318; --red-soft:#fee9e7; --shadow:0 10px 28px rgba(20,31,43,.08); }}
    * {{ box-sizing:border-box; }} body {{ margin:0; color:var(--ink); background:var(--bg); font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; line-height:1.55; }}
    a {{ color:var(--blue); text-decoration:none; }} a:hover {{ text-decoration:underline; }}
    .shell {{ width:min(1200px,calc(100% - 32px)); margin:0 auto; padding:28px 0 44px; }}
    .hero,.panel,.card,table,.panel-lite {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow); }}
    .hero {{ padding:28px; display:grid; gap:18px; margin-bottom:18px; }} .eyebrow {{ margin:0; color:var(--blue); font-size:13px; font-weight:800; letter-spacing:.02em; text-transform:uppercase; }}
    h1 {{ margin:0; font-size:clamp(30px,4vw,50px); line-height:1.04; }} h2 {{ margin:0; font-size:22px; }} h3 {{ margin:0; font-size:18px; line-height:1.25; }}
    .lead {{ margin:0; max-width:900px; color:#344150; font-size:17px; }} .notice {{ padding:14px 16px; border:1px solid #f0d29b; border-radius:8px; background:#fff8ea; color:#684000; font-size:14px; margin-bottom:20px; }}
    .section {{ margin-top:24px; }} .section-head {{ display:flex; justify-content:space-between; align-items:end; gap:16px; margin-bottom:12px; }} .hint,.muted {{ margin:0; color:var(--muted); font-size:14px; }}
    .summary {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }} .metric {{ padding:16px; border:1px solid var(--line); border-radius:8px; background:#fff; }} .metric strong {{ display:block; font-size:30px; line-height:1; }} .metric span {{ display:block; margin-top:8px; color:var(--muted); font-size:13px; }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }} .card {{ padding:18px; display:grid; gap:14px; }} .card-top {{ display:flex; justify-content:space-between; gap:14px; align-items:start; }}
    .badge {{ display:inline-flex; white-space:nowrap; border-radius:999px; padding:4px 9px; font-size:12px; font-weight:800; background:var(--blue-soft); color:#0b46bb; }} .badge.good {{ background:var(--green-soft); color:var(--green); }} .badge.warn {{ background:var(--amber-soft); color:var(--amber); }} .badge.bad {{ background:var(--red-soft); color:var(--red); }}
    .score {{ display:grid; gap:8px; }} .score-row {{ display:grid; grid-template-columns:132px 1fr 52px; gap:10px; align-items:center; font-size:13px; color:#445160; }} .bar {{ height:9px; overflow:hidden; border-radius:999px; background:#e8edf2; }} .bar span {{ display:block; height:100%; border-radius:inherit; background:linear-gradient(90deg,var(--green),var(--blue)); }}
    .logic {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }} .logic-box,.panel-lite {{ border:1px solid var(--line); border-radius:8px; padding:11px; background:#fbfcfd; box-shadow:none; }} .logic-box strong,.panel-lite strong {{ display:block; margin-bottom:4px; font-size:13px; }} .logic-box p,.panel-lite p {{ margin:0; color:#445160; font-size:13px; }}
    ul {{ margin:0; padding-left:18px; color:#445160; font-size:13px; }} li {{ margin:5px 0; }} .links {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; }} .link-btn {{ display:inline-flex; align-items:center; justify-content:center; min-height:36px; padding:7px 8px; border:1px solid var(--line); border-radius:8px; background:#fff; color:var(--ink); font-size:13px; font-weight:750; text-align:center; }}
    table {{ width:100%; border-collapse:collapse; overflow:hidden; }} th,td {{ padding:12px 13px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:14px; }} th {{ background:#eef3f8; color:#344150; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }} tr:last-child td {{ border-bottom:0; }}
    .panel {{ padding:18px; }} .footer {{ margin-top:26px; color:var(--muted); font-size:12px; }}
    @media (max-width:980px) {{ .summary,.grid {{ grid-template-columns:1fr 1fr; }} .links {{ grid-template-columns:1fr 1fr; }} }}
    @media (max-width:700px) {{ .shell {{ width:min(100% - 20px,1200px); padding-top:16px; }} .hero {{ padding:20px; }} .summary,.grid,.logic,.links {{ grid-template-columns:1fr; }} .score-row {{ grid-template-columns:112px 1fr 48px; }} }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">Product Cross Validation</p>
      <h1>选品交叉验证报告</h1>
      <p class="lead">跨平台验证趋势品是否值得打样：需求、广告、内容、货源、物流合规和差异化。</p>
      <div class="summary">
        <div class="metric"><strong>{len(products)}</strong><span>验证产品</span></div>
        <div class="metric"><strong>{sample_count}</strong><span>优先打样</span></div>
        <div class="metric"><strong>{validate_count}</strong><span>继续验证</span></div>
        <div class="metric"><strong>{watch_count + avoid_count}</strong><span>观察/放弃/转向</span></div>
      </div>
    </section>
    <div class="notice">{list_items(method_notes)}</div>
    <section class="section">
      <div class="section-head"><div><h2>最终排序</h2><p class="hint">{caption}</p></div></div>
      <table><thead><tr><th>排序</th><th>产品</th><th>总分</th><th>结论</th><th>建议产品</th></tr></thead><tbody>{ranking_rows(products)}</tbody></table>
    </section>
    <section class="section">
      <div class="section-head"><div><h2>单品验证卡</h2><p class="hint">每张卡包含评分、证据、风险、下一步和平台直达链接。</p></div></div>
      <div class="grid">{''.join(product_card(product, dims) for product in sorted(products, key=total_score, reverse=True))}</div>
    </section>
    <p class="footer">Captured at {esc(report.get("captured_at"))}. Do not treat this report as inventory commitment; verify live ads, trend curves, supplier quotes, sample quality, landed cost, and return risk.</p>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render product cross-validation JSON as HTML.")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.json_file.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
