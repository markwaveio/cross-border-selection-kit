---
name: product-cross-validation
description: Use when validating ecommerce or cross-border product ideas after initial trend discovery. Covers cross-checking product concepts across Amazon evidence, Facebook Ads Library, TikTok/YouTube content demand, Google Trends, 1688/AliExpress/CJ/Doba supplier structure, logistics/compliance risk, differentiation space, and producing a scored HTML selection dashboard. Trigger for Chinese requests about 选品交叉验证, 广告库验证, Google Trends验证, 1688货源验证, 物流货源结构, 产品是否值得打样, or 跨境选品验证报告.
---

# Product Cross Validation

## Purpose

Validate whether trend-sourced product concepts deserve sampling, supplier outreach, or small-batch testing. Treat this skill as the step after trend discovery, not the trend discovery step itself.

Use it to answer:

- Is demand real beyond one platform?
- Are advertisers already spending money on this product or use case?
- Is search/content interest stable, seasonal, or fading?
- Is the supplier structure easy to build?
- Are logistics, compliance, support, or return risks acceptable?
- Which product should be sampled first?

## Inputs

Accept one or more product concepts. Each concept may include:

- product name or generalized concept
- source signal, such as Amazon, TikTok, marketplace, or manual idea
- known product URL or search URL
- target market, default `US`
- optional notes, risks, and suspected keywords

If the input is loose prose, normalize it into product concepts and keyword sets before validating.

## Keyword Consistency 铁律 (read before scoring)

The single most common way this pipeline produces a misleading report is **keyword-aperture drift**: one upstream step narrows its keyword (because the broad word was polluted or ambiguous) while the other steps keep using the broad word, so the three evidence sources are no longer describing the same product. The scores then look comparable but aren't.

Rules, enforced at scoring time:

1. **One keyword of record per concept.** Each product concept resolves to ONE narrowed English keyword (and its matching Chinese 1688 keyword). When `ad-library-product-validator` or `google-trends-product-validator` narrows a keyword to escape pollution/ambiguity, that narrowed keyword becomes the keyword of record and **must propagate to every other source** — re-run the lagging source on it. Do not mix a broad-word capture with a narrow-word capture in the same concept's evidence.
2. **Alignment gate before scoring.** Before assigning scores, list the actual keyword each of the three machine sources (Ad Library / Google Trends / 1688) used. If they are not the same aperture (allowing for English↔Chinese translation of the *same* product form), the concept's cross-validation is not aligned.
3. **If you cannot re-run to align them** (e.g. user wants the report now), do not silently score it as if aligned. **Cap the affected dimension and flag it red**: mark the mismatched dimension `manual_confirmation_needed`, state plainly in `evidence` which sources used which keywords, and lower confidence in the `risks` array. A concept whose three sources used different apertures must not outrank a concept whose three sources are fully aligned, on the strength of the mismatched evidence alone.
4. **Record the resolution in `method_notes`**: for each concept, the keyword of record, and whether all three sources are aligned on it or which one lags and why.

## Validation Workflow

1. Normalize keywords:
   - English demand keywords for Amazon, Google Trends, TikTok, YouTube, and Facebook Ads Library.
   - Chinese supplier keywords for 1688, such as material, use case, and category variants.
   - These are *starting* keywords. Expect Ad Library / Google Trends to narrow them when broad words are polluted (see those skills' pollution self-checks). Carry the narrowed keyword of record across all sources per the Keyword Consistency 铁律 above.
2. Demand validation:
   - Check Amazon search/category context, public shopping articles, reviews/rank when available.
   - Check TikTok/YouTube for recent usage content, comments asking where to buy, and demonstrability.
   - Check Google Trends for 12-month and 5-year direction, seasonality, and spike decay.
3. Advertising validation:
   - Use Facebook Ads Library direct keyword links.
   - Record active advertiser count, oldest active ad date, repeated creative angles, and landing-page type when visible.
   - If the live interface cannot be read, provide direct links and mark the evidence as needing manual confirmation.
4. Supplier validation:
   - Use 1688/AliExpress/CJ/Doba direct keyword links.
   - Look for supplier count, factory vs trader mix, MOQ, customization, packaging, sample availability, and price band.
   - Do not invent quotes or supplier counts; mark unknowns explicitly.
5. Logistics and compliance validation:
   - Penalize batteries, liquids, food/medical claims, child safety, surveillance/privacy, wireless devices, oversized goods, fragile glass, heavy items, and high-return apparel sizing.
6. Score and decide:
   - Use the scoring rubric in `references/scoring-rubric.md`.
   - Assign one of: `sample_now`, `validate_more`, `watch`, `avoid`, or `convert_to_accessory`.
7. Produce outputs:
   - A structured JSON report.
   - For user-facing reports, a standalone HTML dashboard with scores, evidence, direct links, and recommended next actions.

## Tool Guidance

- Use web search or browser tools for current public evidence when available.
- Use official platform links for manual verification when platforms are not machine-readable.
- Use `scripts/render_cross_validation_report.py report.json -o report.html` to render the JSON into a visual dashboard.
- Read `references/scoring-rubric.md` when assigning scores or explaining final decisions.
- Do not bypass platform anti-bot controls, login walls, CAPTCHAs, or abnormal traffic pages. Record the limitation instead.

## Output Contract

Return JSON shaped like:

```json
{
  "report_type": "product_cross_validation",
  "captured_at": "ISO-8601 timestamp",
  "target_market": "US",
  "method_notes": ["What could and could not be verified"],
  "products": [
    {
      "concept": "Compression packing cubes",
      "decision": "sample_now",
      "total_score": 87,
      "scores": {
        "demand": 24,
        "ads": 16,
        "content": 13,
        "supplier": 18,
        "logistics": 9,
        "differentiation": 7
      },
      "keywords": {
        "english": ["compression packing cubes", "packing cubes"],
        "chinese": ["压缩收纳袋", "旅行收纳袋"],
        "keyword_of_record": "compression packing cubes",
        "aperture_alignment": "aligned",
        "alignment_note": "Ad Library / Google Trends / 1688 all run on the same product form (EN: compression packing cubes / ZH: 压缩收纳袋). If a source lagged on a broader word, set this to 'misaligned', name the source + keyword it used, and cap that dimension."
      },
      "evidence": {
        "demand": "Demand summary",
        "ads": "Ads Library summary or manual confirmation needed",
        "content": "TikTok/YouTube content summary",
        "supplier": "1688/supplier structure summary",
        "logistics": "Logistics and compliance summary",
        "differentiation": "Differentiation summary"
      },
      "risks": ["Main risks"],
      "recommended_product": "Specific product angle to test",
      "next_actions": ["Supplier outreach", "Samples to order"],
      "links": {
        "amazon": "https://www.amazon.com/s?k=...",
        "facebook_ads_library": "https://www.facebook.com/ads/library/?...",
        "google_trends": "https://trends.google.com/trends/explore?...",
        "1688": "https://s.1688.com/selloffer/offer_search.htm?keywords=..."
      }
    }
  ]
}
```

## HTML Dashboard Requirements

For Chinese "报告", "看板", or "可视化" requests, create a local HTML file under `reports/` unless the user specifies another path. If this run is part of the cross-border product-selection pipeline, put both the HTML and its source JSON into the workspace's dashboard folder (`$WORKSPACE_DIR/最终看板/`, from `pipeline.config`) instead, using a version-suffixed filename (`cross-validation-product-report-<date>-v<N>.html`) and never overwriting a prior version — each version is a checkpoint showing how the ranking changed as new evidence layers were added. Include:

- Final ranking table.
- Product validation cards with six scoring dimensions.
- Direct links to Amazon, Facebook Ads Library, Google Trends, 1688, and optional TikTok/YouTube/AliExpress.
- Clear distinction between verified evidence, inferred judgment, and manual confirmation needed.
- Recommended product angle, risks, and next actions.
- A short method note warning against fake ad counts, fake trend indexes, or invented supplier quotes.

Keep the report actionable: the user should know which product to sample first and what exact checks remain.

