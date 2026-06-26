---
name: amazon-trend-signal
description: Use when building or running a cross-border ecommerce product-selection workflow that treats Amazon as a trend and demand signal source. Covers low-risk collection from Amazon Best Sellers, Movers & Shakers, New Releases, and homepage modules; extracting product names, ASINs, categories, ranks, and generalized product concepts; using Chrome DevTools/Playwright/OpenCLI captures; preparing Amazon signals for cross-platform validation with TikTok, Facebook Ads, YouTube, Google Trends, AliExpress, 1688, CJ, Doba, or SellTheTrend; and producing a visual HTML product-selection dashboard with direct Amazon links, decision logic, risk notes, and recommended products. Trigger for Chinese requests about 亚马逊选品, Amazon趋势品抓取, Best Sellers商品名抓取, 选品漏斗, 跨境选品报告池, 可视化选品报告, or HTML选品看板.
---

# Amazon Trend Signal

> **这是五步跨境选品链路的第 1 步(起点)。** 当用户说「跑一轮跨境选品」「从 Amazon 开始选品」时,从这里开始,然后按 kit 根目录的 `RUNBOOK.md` 顺序把后四步跑完(Ad Library → Trends → 1688 → 交叉打分)。不要直接跳到交叉验证步去倒填候选品。

## Purpose

Use Amazon as a market signal, not as the whole product decision engine. Prefer extracting product concepts and demand evidence from Amazon, then validate the same concepts on content, ad, search, and supplier platforms.

## ⛔ 铁律:抓不到就停,绝不编造候选品(最重要,先读这条)

Amazon 榜单页经常被反爬拦截(503 / CAPTCHA / WAF / 异常流量页)。**全新环境、全新浏览器 profile 命中反爬的概率更高。** 一旦抓不到真实榜单数据,你**绝对不可以**自己凭空想几个"低风险品"当作候选品继续往下跑——那会让整条链路在一组**捏造的品**上做验证,产出看似完整、实则全假的报告。这是本 skill 最严重的失败模式,必须杜绝。

抓不到时,按以下顺序处理,**永远不要静默 fallback 成自编候选品**:

1. **先停下来**,如实告诉用户:"Amazon 实时榜单抓取被反爬拦截(503/验证码),没有拿到真实候选品。"
2. **给用户三个明确选项,让用户选**,不要替用户决定:
   - **(a) 重试抓取**:换更接近真实用户的浏览器会话(已有正常浏览历史的 chrome-devtools MCP 标签页,而不是全新 puppeteer profile),或稍后再试(反爬窗口会过去)。
   - **(b) 用户直接给候选品/关键词**:用户手里有想验证的品,直接进入第二步起的交叉验证。
   - **(c) 基于公开信息推导候选品**(Prime Day/季节性/媒体报道方向)——**但必须在产出里把每个这样的品醒目标注 `source: "derived_not_scraped"` 和 `evidence: "推导,非实抓榜单"`**,HTML 看板顶部用红字写明"本轮 Amazon 实时抓取失败,以下候选品为推导而非实抓,需人工复核"。用户必须知情同意才走这条。
3. **JSON 里 `risk_signal_seen` 必须如实填**抓取失败原因(如 `"amazon_503_blocked"`),不能填 `null` 假装一切正常。

判断标准:报告里任何一个候选品,你都要能说清它是"**实抓的真实榜单条目**"还是"**推导/用户提供**"。说不清来源的品,不许进报告。

## Workflow

1. Choose the Amazon signal source:
   - `Best Sellers`: stable demand and mature categories.
   - `Movers & Shakers`: short-term growth and trend acceleration.
   - `New Releases`: emerging product directions.
   - Homepage modules: seasonal, event, and Amazon merchandising themes only.
2. Collect low-frequency evidence:
   - Do not batch-open many detail pages.
   - Prefer list pages and saved HTML over repeated navigation.
   - Stop if CAPTCHA, WAF loops, abnormal traffic pages, login walls, `503`, or repeated `202` challenges appear — then follow the ⛔ 铁律 above (stop, tell the user, offer retry / user-supplied / clearly-labelled-derived; never silently fabricate).
3. Extract only trend-useful fields:
   - source, category, rank, product name, ASIN, URL, image URL, captured_at.
   - signal_type: `best_seller`, `mover`, `new_release`, or `homepage_module`.
   - generalized_concept: remove brand/ecosystem lock-in.
   - brand_locked and risk notes.
4. Filter before cross-platform validation:
   - Reject gift cards, pharmacy/services, Amazon ecosystem devices as sellable products.
   - Keep brand-locked products only as trend directions or accessory ideas.
   - Prioritize reusable concepts: pet wellness, smart-home accessories, sleep clocks, hydration bottles, summer footwear, kitchen consumables, etc.
5. Output a lightweight JSON report for the broader product-selection funnel.
6. When the user asks for a report, dashboard, visual result, or Chinese "选品报告", also produce a standalone HTML dashboard:
   - Put recommended products first, with scores, rationale, risks, and direct Amazon links.
   - Include a short explanation of the selection logic and cross-platform validation steps.
   - Separate directly actionable product concepts from brand-locked or high-risk directions.
   - Record any anti-bot or access risk seen during collection instead of hiding it.

## Tool Guidance

- If Chrome DevTools MCP is available, use it to capture page HTML, network requests, screenshots, and WAF/bot signals.
- If only Playwright MCP is available, use `browser_navigate`, `browser_network_requests`, and saved response bodies.
- Use `scripts/parse_amazon_homepage.py` on a saved homepage HTML file to extract module headings, image alt product names, and carousel ASIN/title/url rows.
- Use `scripts/render_visual_report.py report.json -o report.html` to turn the JSON report into a standalone visual dashboard.
- Read `references/amazon-sources.md` when deciding fields, score meaning, source priority, or anti-blocking guardrails.

## Output Contract

Return JSON shaped like this, and render it to HTML when the requested deliverable is a report/dashboard:

```json
{
  "source": "amazon",
  "crawl_mode": "low_frequency_signal_collection",
  "captured_at": "ISO-8601 timestamp",
  "risk_signal_seen": null,
  "_risk_signal_seen_note": "如实填抓取中遇到的反爬,如 'amazon_503_blocked' / 'captcha'。抓取失败时禁止填 null 假装正常。",
  "items": [
    {
      "signal_type": "best_seller",
      "candidate_source": "scraped",
      "_candidate_source_values": "scraped(实抓榜单) | user_supplied(用户提供) | derived_not_scraped(推导,非实抓——抓取失败时唯一允许且必须醒目标注的来源)",
      "category": "Home & Kitchen",
      "rank": 1,
      "asin": "B000000000",
      "product_name": "Product title from Amazon",
      "product_url": "https://www.amazon.com/dp/B000000000",
      "image_url": "https://...",
      "generalized_concept": "brand-free product concept",
      "brand_locked": false,
      "recommendation_tier": "priority | watch | avoid",
      "selection_score": 84,
      "suitable_for_cross_platform_validation": true,
      "notes": ["Why this is useful as a trend signal"],
      "risk_notes": ["IP, compliance, logistics, or platform risks"],
      "amazon_links": [
        {
          "label": "Amazon Search",
          "url": "https://www.amazon.com/s?k=brand-free+product+concept"
        }
      ],
      "next_steps": ["Validate TikTok demand", "Check 1688 supplier price band"]
    }
  ],
  "next_validation_platforms": ["TikTok", "Facebook Ads Library", "Google Trends", "AliExpress/1688"]
}
```

## Visual Dashboard Contract

For user-facing product-selection reports, produce a local HTML file, usually under `reports/`, using the JSON as source data. If this run is part of the cross-border product-selection pipeline, put it into the workspace's dashboard folder (`$WORKSPACE_DIR/最终看板/`, from `pipeline.config`) instead — this skill is the entry point of the five-step chain. The dashboard should include:

- Summary metrics: candidate count, priority recommendations, risk signal, capture time.
- Top recommendation cards: product concept, selection score, tier, why it is attractive, risks, next steps, and direct Amazon links.
- Watchlist table: concepts with demand signal but material risk.
- Avoid/convert table: brand-locked, ecosystem-locked, medical, certification-heavy, oversized, battery-heavy, or service products, with accessory/concept conversion ideas.
- Selection logic: Amazon signal interpretation, de-branding rule, content demonstrability, supplier validation, and risk filters.
- Next validation checklist: TikTok, Facebook Ads Library, YouTube, Google Trends, AliExpress/1688/CJ/Doba.

If an item lacks a canonical `product_url`, add an Amazon search URL derived from `generalized_concept` or `product_name`; do not invent ASINs.

## Interpretation Rules

- Treat Amazon homepage products as merchandising hints, not proof of broad demand.
- Treat Best Sellers as demand validation, but watch for saturated or brand-dominated categories.
- Treat Movers & Shakers as the strongest Amazon trend signal.
- Treat New Releases as weak-to-medium trend signal until supported by reviews, rank, or off-Amazon traction.
- Never score an Amazon-owned device as a directly sellable private-label product; convert it into accessory or generalized concept ideas.
