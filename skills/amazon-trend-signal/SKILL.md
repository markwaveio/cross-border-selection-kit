---
name: amazon-trend-signal
description: Use when building or running a cross-border ecommerce product-selection workflow that treats Amazon as a trend and demand signal source. Covers low-risk collection from Amazon Best Sellers, Movers & Shakers, New Releases, and homepage modules; extracting product names, ASINs, categories, ranks, and generalized product concepts; using Chrome DevTools/Playwright/OpenCLI captures; preparing Amazon signals for cross-platform validation with TikTok, Facebook Ads, YouTube, Google Trends, AliExpress, 1688, CJ, Doba, or SellTheTrend; and producing a visual HTML product-selection dashboard with direct Amazon links, decision logic, risk notes, and recommended products. Trigger for Chinese requests about 亚马逊选品, Amazon趋势品抓取, Best Sellers商品名抓取, 选品漏斗, 跨境选品报告池, 可视化选品报告, or HTML选品看板.
---

# Amazon Trend Signal

## Purpose

Use Amazon as a market signal, not as the whole product decision engine. Prefer extracting product concepts and demand evidence from Amazon, then validate the same concepts on content, ad, search, and supplier platforms.

## Workflow

1. Choose the Amazon signal source:
   - `Best Sellers`: stable demand and mature categories.
   - `Movers & Shakers`: short-term growth and trend acceleration.
   - `New Releases`: emerging product directions.
   - Homepage modules: seasonal, event, and Amazon merchandising themes only.
2. Collect low-frequency evidence:
   - Do not batch-open many detail pages.
   - Prefer list pages and saved HTML over repeated navigation.
   - Stop if CAPTCHA, WAF loops, abnormal traffic pages, login walls, or repeated `202` challenges appear.
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
  "items": [
    {
      "signal_type": "best_seller",
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
