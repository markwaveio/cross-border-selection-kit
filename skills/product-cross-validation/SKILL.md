---
name: product-cross-validation
description: Use when validating ecommerce or cross-border product ideas after initial trend discovery. Covers cross-checking product concepts across Amazon evidence, Facebook Ads Library, TikTok/YouTube content demand, Google Trends, 1688/AliExpress/CJ/Doba supplier structure, logistics/compliance risk, differentiation space, and producing a scored HTML selection dashboard. Trigger for Chinese requests about 选品交叉验证, 广告库验证, Google Trends验证, 1688货源验证, 物流货源结构, 产品是否值得打样, or 跨境选品验证报告.
---

# Product Cross Validation

> **这是五步链路的第 5 步(最后一步),不是起点。** 如果用户说的是「跑一轮跨境选品」这种**整轮**请求,**不要从这里开始**——要先回到第 1 步 `amazon-trend-signal` 发现真实候选品,按 kit 根目录 `RUNBOOK.md` 顺序跑。
> **绝不要因为"还没有候选品"就自己凭空编几个品来跑这一步。** 候选品必须来自 Amazon 实抓 / 用户提供 / 明确标注的推导。无来源的品不许进这一步。

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

### 输出位置(必须读 config,不要写进 kit 目录或当前目录)

这是部署后常见的出错点。**报告必须落进用户配置的工作区,而不是 kit 仓库目录、也不是当前工作目录。** 渲染前先确定输出目录:

1. 找到 `pipeline.config`(通常在 kit 根目录的 `config/pipeline.config`),读出 `WORKSPACE_DIR` 的值(展开 `~`)。
2. 报告输出目录 = `<WORKSPACE_DIR>/最终看板/`。源 JSON 也放这里。
3. 用 shell 解析后再传给渲染脚本,例如:
   ```bash
   source "$KIT_DIR/scripts/load_config.sh"          # 拿到 $WORKSPACE_DIR
   OUT_DIR="$WORKSPACE_DIR/最终看板"; mkdir -p "$OUT_DIR"
   python3 "$SKILLS_DIR/product-cross-validation/scripts/render_cross_validation_report.py" \
     "$OUT_DIR/cross-validation-product-report-<date>-v<N>.json" \
     -o "$OUT_DIR/cross-validation-product-report-<date>-v<N>.html"
   ```
   如果拿不到 config(用户没装 installer 或单独调用本 skill),**先问用户报告存哪**,不要默默存进 kit 目录或 `reports/`。

用版本号后缀文件名(`cross-validation-product-report-<date>-v<N>.html`),**绝不覆盖旧版本** —— 每个版本是一次快照,记录补了新证据后排名怎么变。

报告内容包含:

- Final ranking table.
- Product validation cards with six scoring dimensions.
- Direct links to Amazon, Facebook Ads Library, Google Trends, 1688, and optional TikTok/YouTube/AliExpress.
- Clear distinction between verified evidence, inferred judgment, and manual confirmation needed.
- Recommended product angle, risks, and next actions.
- A short method note warning against fake ad counts, fake trend indexes, or invented supplier quotes.

Keep the report actionable: the user should know which product to sample first and what exact checks remain.

