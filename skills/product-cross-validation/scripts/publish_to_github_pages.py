#!/usr/bin/env python3
"""Publish a cross-border selection run to GitHub Pages.

Copies a run's artifacts (cross-validation HTML, Amazon-signal HTML, INDEX.md)
into a local publish repo, regenerates a landing index.html that lists every
round, commits, and pushes. First invocation creates the repo + enables Pages;
later invocations just add the new round and push.

Design notes / guardrails:
- This is an OUTWARD-FACING action (publishes to the public internet). The
  pipeline's "unattended" automation runs everything else without prompts, but
  the agent should confirm once before the first publish so the user knows
  reports go public. After the repo exists, pushes are routine.
- Visibility is controlled by --visibility (public|private), read from
  pipeline.config (GITHUB_VISIBILITY). Defaults to private when unset.
- Uses `gh` (must already be authenticated). Does not embed any secret.

Defaults for --repo / --owner / --visibility are read from pipeline.config.

Usage:
  publish_to_github_pages.py \
      --run-dir <$WORKSPACE_DIR> \
      --run-date <YYYY-MM-DD> \
      --cross-html <...-vN.html> \
      --amazon-html <...amazon...html> \
      --index-md <INDEX-<date>.md> \
      [--repo <from config>] \
      [--owner <your-github-username>] \
      [--visibility private|public] \
      [--publish-root <$PUBLISH_DIR>] \
      [--dry-run]
"""
from __future__ import annotations
import argparse, subprocess, shutil, sys, json, datetime, re
from pathlib import Path

# Load shared config (kit/scripts/pipeline_config.py). Defaults for owner/repo/
# visibility/publish-root come from pipeline.config so nothing is hardcoded to
# any one user's GitHub account. CLI flags still override.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
try:
    import pipeline_config as _cfg
except Exception:
    class _cfg:  # config not present -> fall back to CLI args only
        @staticmethod
        def get(k, d=None): return d


def run(cmd, cwd=None, check=True, capture=False):
    print("  $", " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, cwd=cwd, text=True,
                       capture_output=capture)
    if check and r.returncode != 0:
        sys.stderr.write((r.stderr or "") + "\n")
        raise SystemExit(f"command failed ({r.returncode}): {' '.join(map(str,cmd))}")
    return r


def repo_exists(owner, repo):
    r = subprocess.run(["gh", "repo", "view", f"{owner}/{repo}"],
                       text=True, capture_output=True)
    return r.returncode == 0


def md_to_html_fragment(md_path: Path) -> str:
    """Tiny markdown→HTML for the INDEX (headings/links/lists/tables/bold).
    Avoids a markdown dependency; good enough for our generated INDEX shape."""
    import html as _h
    out, in_table, in_list = [], False, False
    for raw in md_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\n")
        # tables
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if re.match(r"^\s*-{2,}", cells[0]) or all(re.match(r"^:?-+:?$", c or "-") for c in cells):
                continue  # separator row
            if not in_table:
                out.append("<table>"); in_table = True
            tag = "td"
            out.append("<tr>" + "".join(f"<{tag}>{inline_md(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        elif in_table:
            out.append("</table>"); in_table = False
        # lists
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{inline_md(line[2:])}</li>")
            continue
        elif in_list:
            out.append("</ul>"); in_list = False
        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline_md(m.group(2))}</h{lvl}>")
            continue
        if line.startswith(">"):
            out.append(f"<blockquote>{inline_md(line.lstrip('> '))}</blockquote>")
            continue
        if line.strip() == "---":
            out.append("<hr>")
            continue
        if line.strip() == "":
            out.append("")
            continue
        out.append(f"<p>{inline_md(line)}</p>")
    if in_table: out.append("</table>")
    if in_list: out.append("</ul>")
    return "\n".join(out)


def inline_md(s: str) -> str:
    import html as _h
    s = _h.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    # links [text](url)  (url already relative; keep as-is)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
    return s


LANDING_TEMPLATE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>跨境选品报告库</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:880px;margin:2rem auto;padding:0 1rem;color:#1a1a1a;line-height:1.6}}
 h1{{border-bottom:2px solid #eee;padding-bottom:.4rem}}
 .round{{border:1px solid #e5e5e5;border-radius:10px;padding:1rem 1.2rem;margin:1rem 0;background:#fafafa}}
 .round h2{{margin:.2rem 0 .6rem}}
 .links a{{display:inline-block;margin-right:1rem;color:#0a66c2;text-decoration:none}}
 .links a:hover{{text-decoration:underline}}
 .meta{{color:#777;font-size:.9rem}}
 footer{{color:#999;font-size:.85rem;margin-top:2rem;border-top:1px solid #eee;padding-top:.6rem}}
</style></head><body>
<h1>🛒 跨境选品报告库</h1>
<p class="meta">每一轮选品链路(Amazon信号→Ad Library→Trends→1688→交叉验证)的可视化结果。最新在最上面。</p>
{rounds}
<footer>自动发布 · 最后更新 {updated}</footer>
</body></html>
"""

ROUND_BLOCK = """<div class="round">
  <h2>{date} · {n_products} 个候选品</h2>
  <p class="meta">{summary}</p>
  <div class="links">
    <a href="{date}/index.html">📄 总入口 INDEX</a>
    <a href="{date}/cross-validation.html">🖥️ 交叉验证看板</a>
    {amazon_link}
  </div>
</div>"""


def build_landing(publish_root: Path) -> str:
    rounds = []
    # each round is a dated subdir with a meta.json
    dated = sorted([p for p in publish_root.iterdir()
                    if p.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", p.name)],
                   reverse=True)
    for d in dated:
        meta = {}
        mp = d / "meta.json"
        if mp.exists():
            meta = json.loads(mp.read_text(encoding="utf-8"))
        amazon_link = (f'<a href="{d.name}/amazon-signal.html">📈 Amazon信号</a>'
                       if (d / "amazon-signal.html").exists() else "")
        rounds.append(ROUND_BLOCK.format(
            date=d.name,
            n_products=meta.get("n_products", "?"),
            summary=meta.get("summary", ""),
            amazon_link=amazon_link,
        ))
    return LANDING_TEMPLATE.format(
        rounds="\n".join(rounds) or "<p>(暂无报告)</p>",
        updated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-date", required=True)
    ap.add_argument("--cross-html", required=True)
    ap.add_argument("--amazon-html", default=None)
    ap.add_argument("--index-md", required=True)
    ap.add_argument("--cross-json", default=None, help="用于读取候选品数/摘要写入 meta.json")
    ap.add_argument("--repo", default=_cfg.get("GITHUB_REPO", "cross-border-selection-reports"))
    ap.add_argument("--owner", default=_cfg.get("GITHUB_OWNER"))
    ap.add_argument("--visibility", default=_cfg.get("GITHUB_VISIBILITY", "private"),
                    choices=["public", "private"])
    ap.add_argument("--publish-root",
                    default=_cfg.get("PUBLISH_DIR", str(Path.home() / "cross-border-selection/pages")))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.owner:
        sys.exit("❌ 未设置 GitHub 用户名。在 pipeline.config 填 GITHUB_OWNER,或用 --owner 指定。")

    publish_root = Path(args.publish_root).resolve()
    round_dir = publish_root / args.run_date
    round_dir.mkdir(parents=True, exist_ok=True)

    # 1) copy artifacts into round dir with stable names
    shutil.copy(args.cross_html, round_dir / "cross-validation.html")
    if args.amazon_html and Path(args.amazon_html).exists():
        shutil.copy(args.amazon_html, round_dir / "amazon-signal.html")
    # INDEX.md → index.html (rendered, with rewritten links to local copies)
    (round_dir / "index.html").write_text(
        f"<!doctype html><meta charset='utf-8'><title>INDEX {args.run_date}</title>"
        "<style>body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:880px;margin:2rem auto;padding:0 1rem;line-height:1.6}"
        "table{border-collapse:collapse}td{border:1px solid #ddd;padding:.3rem .6rem}code{background:#f4f4f4;padding:.1rem .3rem;border-radius:3px}"
        "a{color:#0a66c2}</style>\n"
        + md_to_html_fragment(Path(args.index_md)),
        encoding="utf-8")

    # meta.json for landing page
    meta = {"n_products": "?", "summary": ""}
    if args.cross_json and Path(args.cross_json).exists():
        d = json.load(open(args.cross_json, encoding="utf-8"))
        prods = d.get("products", [])
        meta["n_products"] = len(prods)
        top = sorted(prods, key=lambda x: x.get("total_score", 0), reverse=True)
        meta["summary"] = " / ".join(f"{p.get('concept','?').split('/')[0].strip()}({p.get('total_score','?')})"
                                     for p in top[:3])
    (round_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) regenerate landing index.html
    (publish_root / "index.html").write_text(build_landing(publish_root), encoding="utf-8")

    # 3) git init / repo create / push
    if args.dry_run:
        print(f"[dry-run] prepared {round_dir}; landing at {publish_root/'index.html'}")
        print("[dry-run] skipped git/gh operations")
        return

    if not (publish_root / ".git").exists():
        run(["git", "init"], cwd=publish_root)
        run(["git", "branch", "-M", "main"], cwd=publish_root)
    # .nojekyll so GitHub Pages serves raw HTML dirs
    (publish_root / ".nojekyll").write_text("", encoding="utf-8")
    run(["git", "add", "-A"], cwd=publish_root)
    # commit (skip if nothing changed)
    c = subprocess.run(["git", "commit", "-m", f"选品报告 {args.run_date}"],
                       cwd=publish_root, text=True, capture_output=True)
    print(c.stdout or c.stderr)

    if not repo_exists(args.owner, args.repo):
        print(f"creating repo {args.owner}/{args.repo} ({args.visibility}) ...")
        run(["gh", "repo", "create", f"{args.owner}/{args.repo}",
             f"--{args.visibility}", "--source", str(publish_root),
             "--remote", "origin", "--push"], cwd=publish_root)
        # enable Pages from main / root
        run(["gh", "api", "-X", "POST", f"repos/{args.owner}/{args.repo}/pages",
             "-f", "source[branch]=main", "-f", "source[path]=/"],
            cwd=publish_root, check=False)
    else:
        run(["git", "push", "origin", "main"], cwd=publish_root, check=False)

    print(f"\n✅ Published. Pages URL (give it ~1min on first deploy):")
    print(f"   https://{args.owner}.github.io/{args.repo}/")
    print(f"   This round: https://{args.owner}.github.io/{args.repo}/{args.run_date}/")


if __name__ == "__main__":
    main()
