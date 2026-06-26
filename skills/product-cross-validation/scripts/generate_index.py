#!/usr/bin/env python3
"""Generate a one-page INDEX.md for a cross-border product-selection run.

Reads the cross-validation report JSON (source of truth for products/scores/
decisions) and links every per-step artifact (Amazon signal, Ad Library single
reports, Trends raw, 1688 raw, the HTML dashboard) into a single navigable page.

Usage:
  generate_index.py <cross-validation.json> \
      --out <INDEX.md> \
      [--base-dir <$WORKSPACE_DIR>] \
      [--html <cross-validation-...-v4.html>] \
      [--amazon-html <amazon-trend-signal-...html>] \
      [--run-date 2026-06-26]

The script is data-driven: it lists whatever products are in the JSON, in
score order, and only links artifacts that actually exist on disk — so it works
for any run, any number of products, any keyword.
"""
from __future__ import annotations
import argparse, json, os, datetime
from pathlib import Path

DECISION_LABEL = {
    "sample_now": "🟢 优先打样",
    "validate_more": "🟡 继续验证",
    "watch": "⚪ 观察",
    "avoid": "🔴 放弃",
    "convert_to_accessory": "🔵 转配件",
}


def rel(target: Path, start: Path) -> str:
    try:
        return os.path.relpath(target, start)
    except Exception:
        return str(target)


def first_existing(*paths: Path):
    for p in paths:
        if p and p.exists():
            return p
    return None


def slug_candidates(concept: str, keywords: dict):
    """Best-effort slugs to locate per-product artifacts by filename."""
    cands = []
    kor = (keywords or {}).get("keyword_of_record")
    if kor:
        cands.append(kor.split("(")[0].strip().lower().replace(" ", "-"))
    for k in (keywords or {}).get("english", []) or []:
        cands.append(k.strip().lower().replace(" ", "-"))
    # de-dup, keep order
    seen, out = set(), []
    for c in cands:
        if c and c not in seen:
            seen.add(c); out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-dir", default=None,
                    help="选品链路验证根目录;默认取 json 文件向上找到的 02_选品链路验证")
    ap.add_argument("--html", default=None, help="交叉验证 HTML 看板路径")
    ap.add_argument("--amazon-html", default=None, help="第一步 Amazon 信号 HTML 路径")
    ap.add_argument("--run-date", default=None)
    args = ap.parse_args()

    data = json.load(open(args.json, encoding="utf-8"))
    out_path = Path(args.out).resolve()
    out_dir = out_path.parent

    base = Path(args.base_dir).resolve() if args.base_dir else None
    if base is None:
        p = Path(args.json).resolve()
        for parent in p.parents:
            if parent.name == "02_选品链路验证":
                base = parent; break
        base = base or out_dir

    run_date = args.run_date or data.get("captured_at", "")[:10] or datetime.date.today().isoformat()
    products = data.get("products", [])
    products_sorted = sorted(products, key=lambda x: x.get("total_score", 0), reverse=True)

    L = []
    L.append(f"# 跨境选品报告总入口 · {run_date}")
    L.append("")
    L.append(f"> 本轮共 **{len(products)}** 个候选品。这一页是总入口——从这里下钻到每一步的原始数据与单品分析。")
    L.append(f"> 数据采集:{data.get('captured_at','')} | 市场:{data.get('target_market','US')}")
    if data.get("run_label"):
        L.append(f">")
        L.append(f"> {data['run_label']}")
    L.append("")

    # 顶部:最终排名表
    L.append("## 📊 最终排名")
    L.append("")
    L.append("| 排名 | 候选品 | 总分 | 决策 | 关键词口径 |")
    L.append("|---:|---|---:|---|---|")
    for i, p in enumerate(products_sorted, 1):
        concept = p.get("concept", "?")
        score = p.get("total_score", "?")
        dec = DECISION_LABEL.get(p.get("decision", ""), p.get("decision", ""))
        align = (p.get("keywords", {}) or {}).get("aperture_alignment", "")
        align_mark = {"aligned": "✅ 对齐", "misaligned": "⚠️ 口径不齐(已封顶)"}.get(align, align or "—")
        L.append(f"| {i} | {concept} | {score} | {dec} | {align_mark} |")
    L.append("")

    # 看板入口
    L.append("## 🖥️ 可视化看板")
    L.append("")
    html = first_existing(Path(args.html).resolve() if args.html else None)
    if html:
        L.append(f"- 交叉验证看板(六维打分+决策): [{html.name}]({rel(html, out_dir)})")
    amz = first_existing(Path(args.amazon_html).resolve() if args.amazon_html else None)
    if amz:
        L.append(f"- 第一步 Amazon 信号看板: [{amz.name}]({rel(amz, out_dir)})")
    if not html and not amz:
        L.append("- (本轮未生成 HTML 看板)")
    L.append("")

    # 逐品下钻
    L.append("## 🔎 逐品下钻(每步原始数据 + 单品分析)")
    L.append("")
    reports_dir = base / "单品报告"
    ad_raw = base / "原始数据" / "ad-library"
    trends_raw = base / "原始数据" / "google-trends"
    s1688_raw = base / "原始数据" / "1688"

    for i, p in enumerate(products_sorted, 1):
        concept = p.get("concept", "?")
        kw = p.get("keywords", {})
        L.append(f"### {i}. {concept}")
        kor = kw.get("keyword_of_record")
        if kor:
            L.append(f"- **keyword of record**: `{kor}`")
        align_note = kw.get("alignment_note")
        if align_note:
            L.append(f"- 口径说明: {align_note}")
        # locate artifacts by slug
        links = []
        for slug in slug_candidates(concept, kw):
            r = first_existing(reports_dir / f"{slug}.report.md")
            if r:
                links.append(f"[单品报告]({rel(r, out_dir)})"); break
        for slug in slug_candidates(concept, kw):
            a = first_existing(ad_raw / f"{slug}.json")
            if a:
                links.append(f"[Ad Library原始]({rel(a, out_dir)})"); break
        # trends/1688 raw are dated subdirs or flat — link the dir if file not pinpointable
        if trends_raw.exists():
            links.append(f"[Trends原始目录]({rel(trends_raw, out_dir)})")
        if s1688_raw.exists():
            for slug in slug_candidates(concept, kw):
                s = first_existing(s1688_raw / f"{slug}.json")
                if s:
                    links.append(f"[1688原始]({rel(s, out_dir)})"); break
        if links:
            L.append("- 证据: " + " · ".join(links))
        # 决策摘要
        ev = p.get("evidence", {})
        rec = p.get("recommended_product")
        if rec:
            L.append(f"- 建议: {rec}")
        L.append("")

    # 方法 & 待办
    notes = data.get("method_notes", [])
    if notes:
        L.append("## 📝 方法说明 & 关键发现")
        L.append("")
        for n in notes:
            L.append(f"- {n}")
        L.append("")

    L.append("---")
    L.append(f"*由 generate_index.py 自动生成 · {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    L.append("")

    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"INDEX written: {out_path}")


if __name__ == "__main__":
    main()
