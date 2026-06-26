#!/usr/bin/env python3
"""Render an Amazon trend-signal JSON report as a standalone HTML dashboard."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from urllib.parse import quote_plus


AMAZON_LINKS = [
    ("Movers & Shakers", "https://www.amazon.com/gp/movers-and-shakers"),
    ("Best Sellers", "https://www.amazon.com/Best-Sellers/zgbs"),
    ("New Releases", "https://www.amazon.com/gp/new-releases"),
]


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def amazon_search_url(item: dict) -> str:
    query = item.get("generalized_concept") or item.get("product_name") or item.get("category") or "amazon product"
    return f"https://www.amazon.com/s?k={quote_plus(str(query))}"


def item_links(item: dict) -> list[dict]:
    links = list(item.get("amazon_links") or [])
    if item.get("product_url"):
        links.insert(0, {"label": "Product", "url": item["product_url"]})
    if not links:
        links.append({"label": "Amazon Search", "url": amazon_search_url(item)})
    return links[:3]


def tier(item: dict) -> str:
    if item.get("recommendation_tier"):
        return str(item["recommendation_tier"])
    if item.get("brand_locked") or not item.get("suitable_for_cross_platform_validation", True):
        return "watch"
    score = int(item.get("selection_score") or 0)
    return "priority" if score >= 75 else "watch"


def score(item: dict) -> int:
    explicit = item.get("selection_score")
    if isinstance(explicit, (int, float)):
        return max(0, min(100, int(explicit)))
    base = 55
    if item.get("signal_type") == "mover":
        base += 15
    elif item.get("signal_type") == "best_seller":
        base += 10
    elif item.get("signal_type") == "new_release":
        base += 5
    if item.get("brand_locked"):
        base -= 20
    if item.get("suitable_for_cross_platform_validation", True):
        base += 10
    return max(0, min(100, base))


def list_html(values) -> str:
    values = [v for v in (values or []) if v]
    if not values:
        return "<p class=\"muted\">No notes provided.</p>"
    return "<ul>" + "".join(f"<li>{esc(value)}</li>" for value in values) + "</ul>"


def link_buttons(item: dict) -> str:
    buttons = []
    for link in item_links(item):
        label = esc(link.get("label") or "Open")
        url = esc(link.get("url") or amazon_search_url(item))
        buttons.append(f"<a class=\"mini-link\" href=\"{url}\" target=\"_blank\" rel=\"noreferrer\">{label}</a>")
    return "".join(buttons)


def card(item: dict) -> str:
    item_score = score(item)
    item_tier = tier(item)
    badge_class = {"priority": "good", "avoid": "bad"}.get(item_tier, "warn")
    title = item.get("generalized_concept") or item.get("product_name") or "Untitled concept"
    subtitle = item.get("product_name") if item.get("product_name") != title else item.get("category")
    notes = item.get("notes") or []
    risk_notes = item.get("risk_notes") or []
    if risk_notes:
        notes = list(notes) + [f"Risk: {risk_notes[0]}"]
    return f"""
      <article class="product-card">
        <div class="product-top">
          <h3>{esc(title)}</h3>
          <span class="badge {badge_class}">{esc(item_tier)}</span>
        </div>
        <p class="concept">{esc(subtitle or item.get("category") or "Amazon trend-signal concept")}</p>
        <div class="score-row">
          <div class="score-label"><span>Selection score</span><span>{item_score}/100</span></div>
          <div class="bar"><span style="width:{item_score}%"></span></div>
        </div>
        {list_html(notes)}
        <div class="links">{link_buttons(item)}</div>
      </article>
    """


def table_rows(items: list[dict]) -> str:
    rows = []
    for item in items:
        title = item.get("generalized_concept") or item.get("product_name") or "Untitled concept"
        reasons = "; ".join(str(v) for v in item.get("notes") or []) or item.get("signal_type") or ""
        risks = "; ".join(str(v) for v in item.get("risk_notes") or [])
        next_steps = "; ".join(str(v) for v in item.get("next_steps") or [])
        rows.append(
            "<tr>"
            f"<td><strong>{esc(title)}</strong></td>"
            f"<td>{esc(reasons)}</td>"
            f"<td>{esc(risks or 'Review brand, logistics, compliance, and saturation risk.')}</td>"
            f"<td>{esc(next_steps or 'Validate on TikTok, ads, search trends, and suppliers.')}</td>"
            f"<td><a href=\"{esc(amazon_search_url(item))}\" target=\"_blank\" rel=\"noreferrer\">Amazon</a></td>"
            "</tr>"
        )
    return "".join(rows)


def render(report: dict) -> str:
    items = list(report.get("items") or [])
    priority = [item for item in items if tier(item) == "priority"]
    watch = [item for item in items if tier(item) == "watch"]
    avoid = [item for item in items if tier(item) == "avoid"]
    if not priority:
        priority = sorted(items, key=score, reverse=True)[:4]
        watch = [item for item in items if item not in priority]

    source_buttons = "".join(
        f"<a class=\"btn\" href=\"{url}\" target=\"_blank\" rel=\"noreferrer\">{label}</a>"
        for label, url in AMAZON_LINKS
    )
    validation = report.get("next_validation_platforms") or [
        "TikTok",
        "Facebook Ads Library",
        "YouTube",
        "Google Trends",
        "AliExpress/1688",
    ]

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Amazon Trend Signal 选品看板</title>
  <style>
    :root {{
      --bg:#f6f7f8; --panel:#fff; --ink:#17202a; --muted:#65717f; --line:#dfe5eb;
      --accent:#1463ff; --accent-soft:#e9f0ff; --good:#0b7a4b; --warn:#a15c00; --bad:#b42318;
      --shadow:0 10px 28px rgba(20,31,43,.08);
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; color:var(--ink); background:var(--bg); font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; line-height:1.55; }}
    a {{ color:var(--accent); text-decoration:none; }} a:hover {{ text-decoration:underline; }}
    .shell {{ width:min(1180px,calc(100% - 32px)); margin:0 auto; padding:28px 0 44px; }}
    .hero {{ display:grid; grid-template-columns:1.6fr .9fr; gap:20px; align-items:stretch; margin-bottom:20px; }}
    .hero-main,.panel,.product-card,table,.metric {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow); }}
    .hero-main {{ padding:28px; display:grid; gap:18px; }}
    .eyebrow {{ margin:0; color:var(--accent); font-size:13px; font-weight:750; letter-spacing:.02em; text-transform:uppercase; }}
    h1 {{ margin:0; font-size:clamp(30px,4vw,52px); line-height:1.03; letter-spacing:0; }}
    h2 {{ margin:0; font-size:22px; letter-spacing:0; }} h3 {{ margin:0; font-size:17px; line-height:1.25; }}
    .lead {{ margin:0; max-width:780px; color:#344150; font-size:17px; }}
    .hero-actions {{ display:flex; flex-wrap:wrap; gap:10px; }}
    .btn,.mini-link {{ display:inline-flex; align-items:center; justify-content:center; border:1px solid var(--line); border-radius:8px; background:#fff; color:var(--ink); font-weight:750; }}
    .btn {{ min-height:40px; padding:9px 14px; font-size:14px; }} .btn.primary {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
    .hero-side {{ display:grid; gap:12px; }} .metric {{ padding:18px; }} .metric .num {{ display:block; font-size:34px; font-weight:850; line-height:1; }} .metric .label {{ display:block; margin-top:8px; color:var(--muted); font-size:13px; }}
    .notice {{ margin-bottom:20px; padding:14px 16px; border:1px solid #f0d29b; border-radius:8px; background:#fff8ea; color:#684000; font-size:14px; }}
    .section {{ margin-top:24px; }} .section-head {{ display:flex; justify-content:space-between; align-items:end; gap:16px; margin-bottom:12px; }} .hint,.muted {{ margin:0; color:var(--muted); font-size:14px; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; }}
    .product-card {{ display:grid; gap:13px; padding:16px; min-height:100%; }} .product-top {{ display:flex; justify-content:space-between; align-items:start; gap:12px; }}
    .badge {{ display:inline-flex; white-space:nowrap; align-items:center; border-radius:999px; padding:4px 8px; font-size:12px; font-weight:800; background:var(--accent-soft); color:#0b46bb; }}
    .badge.good {{ background:#e8f7ef; color:var(--good); }} .badge.warn {{ background:#fff1db; color:var(--warn); }} .badge.bad {{ background:#fee9e7; color:var(--bad); }}
    .concept {{ margin:0; color:#344150; font-size:14px; }} .score-row {{ display:grid; gap:7px; }} .score-label {{ display:flex; justify-content:space-between; gap:10px; color:var(--muted); font-size:12px; font-weight:750; }}
    .bar {{ height:9px; overflow:hidden; border-radius:999px; background:#e8edf2; }} .bar span {{ display:block; height:100%; border-radius:inherit; background:linear-gradient(90deg,#0b7a4b,#1463ff); }}
    ul {{ margin:0; padding-left:18px; color:#445160; font-size:13px; }} li {{ margin:5px 0; }}
    .links {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:auto; }} .mini-link {{ min-height:34px; padding:7px 8px; background:#fbfcfd; font-size:13px; }}
    .matrix {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }} .panel {{ padding:18px; }}
    table {{ width:100%; border-collapse:collapse; overflow:hidden; }} th,td {{ padding:12px 13px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:14px; }} th {{ background:#eef3f8; color:#344150; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }} tr:last-child td {{ border-bottom:0; }}
    .footer {{ margin-top:26px; color:var(--muted); font-size:12px; }}
    @media (max-width:980px) {{ .hero,.matrix {{ grid-template-columns:1fr; }} .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
    @media (max-width:640px) {{ .shell {{ width:min(100% - 20px,1180px); padding-top:16px; }} .hero-main {{ padding:20px; }} .grid {{ grid-template-columns:1fr; }} .links {{ grid-template-columns:1fr; }} th,td {{ font-size:13px; }} }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="hero-main">
        <p class="eyebrow">Amazon Trend Signal / Cross-border Product Selection</p>
        <h1>亚马逊趋势选品看板</h1>
        <p class="lead">把 Amazon 当作趋势信号源，而不是最终选品结论。优先推荐可演示、低品牌锁定、供应链容易验证、物流风险可控的产品概念。</p>
        <div class="hero-actions"><a class="btn primary" href="#recommendations">查看推荐</a>{source_buttons}</div>
      </div>
      <aside class="hero-side">
        <div class="metric"><span class="num">{len(items)}</span><span class="label">候选概念</span></div>
        <div class="metric"><span class="num">{len(priority)}</span><span class="label">优先建议验证</span></div>
        <div class="metric"><span class="num">{esc(report.get("risk_signal_seen") or "OK")}</span><span class="label">采集风险信号</span></div>
      </aside>
    </section>
    <div class="notice">采集说明：如果 Amazon 出现 CAPTCHA、WAF、503、登录墙或异常流量页，本 skill 会停止直接抓取并记录风险，不绕过限制。</div>
    <section id="recommendations" class="section">
      <div class="section-head"><div><h2>建议优先做的产品</h2><p class="hint">分数综合 Amazon 信号强度、内容可演示性、供应链可得性、品牌/IP 风险和物流售后风险。</p></div></div>
      <div class="grid">{''.join(card(item) for item in priority)}</div>
    </section>
    <section class="section">
      <div class="section-head"><div><h2>可观察但需谨慎的方向</h2><p class="hint">有需求信号，但需要先处理物流、退货、合规或品牌锁定问题。</p></div></div>
      <table><thead><tr><th>产品概念</th><th>为什么有信号</th><th>主要风险</th><th>建议动作</th><th>Amazon</th></tr></thead><tbody>{table_rows(watch) or '<tr><td colspan="5">No watchlist items.</td></tr>'}</tbody></table>
    </section>
    <section class="section matrix">
      <div class="panel"><h2>选品判断逻辑</h2><ul><li><strong>Amazon 信号：</strong>Movers &amp; Shakers 代表增长，Best Sellers 代表稳定需求，New Releases 只代表早期方向。</li><li><strong>去品牌化：</strong>把品牌货转成配件、耗材、周边或场景工具。</li><li><strong>内容可演示：</strong>优先 10-30 秒能讲清痛点和前后差异的产品。</li><li><strong>风险先行：</strong>医疗、安全认证、无线、隐私摄像、电池、液体、大件默认降权。</li></ul></div>
      <div class="panel"><h2>下一步验证清单</h2>{list_html(validation)}</div>
    </section>
    <section class="section">
      <div class="section-head"><div><h2>本轮不建议直接做</h2><p class="hint">可以提供趋势方向，但不适合直接作为跨境私牌切入。</p></div></div>
      <table><thead><tr><th>产品概念</th><th>为什么有信号</th><th>主要风险</th><th>建议动作</th><th>Amazon</th></tr></thead><tbody>{table_rows(avoid) or '<tr><td colspan="5">No avoid items marked in this report.</td></tr>'}</tbody></table>
    </section>
    <p class="footer">Captured at {esc(report.get("captured_at"))}. This is a signal report, not a final purchase or inventory decision.</p>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Amazon trend-signal JSON into a visual HTML dashboard.")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.json_file.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
