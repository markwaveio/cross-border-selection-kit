---
name: ad-library-product-validator
description: Validate ecommerce product keywords with Meta Ad Library. Use when the user wants to search Facebook/Instagram ads for a product keyword, estimate active ad volume, scrape sampled active ads, classify creative hooks, inspect advertiser/landing-domain patterns, and generate a product-selection analysis report.
---

# Ad Library Product Validator

Use this skill to turn a product keyword into a Meta Ad Library demand/competition report.

This skill is keyword-quality-aware: it does not blindly trust whatever keyword it is handed. After scraping, it **self-checks for keyword pollution** and, when the sample is polluted, **automatically narrows the keyword and re-scrapes** before reporting. This keeps the pipeline general — it corrects bad keywords for any product, not just ones a human pre-vetted.

## Workflow

1. Confirm or infer:
   - `keyword`, for example `Compression Packing Cubes`. Prefer an **English category keyword already narrowed to a specific product form** — broad/ambiguous words get polluted (see step 4).
   - `country`, default `US`
   - sample size, default `50`; use `20-30` for a quick probe and `80-100` for deeper analysis

2. Run the scraper:

```bash
node $SKILLS_DIR/ad-library-product-validator/scripts/meta-ad-library-scrape.mjs \
  --keyword 'Compression Packing Cubes' \
  --country US \
  --max-ads 80 \
  --scrolls 70 \
  --wait-ms 1600 \
  --out generated/ad-library-product-validator/compression-packing-cubes.json \
  --screenshot generated/ad-library-product-validator/compression-packing-cubes.png
```

3. Run the analyzer:

```bash
node $SKILLS_DIR/ad-library-product-validator/scripts/ad-library-product-validator.mjs \
  --input generated/ad-library-product-validator/compression-packing-cubes.json \
  --out generated/ad-library-product-validator/compression-packing-cubes.report.md
```

4. **Pollution self-check (mandatory — do this before trusting any count).** A high `reportedResultCount` does NOT mean real demand; broad/ambiguous keywords get hijacked. Read `../product-cross-validation/references/keyword-pollution-blacklist.md` first to fast-match known hijack patterns, then:
   - Deduplicate the sampled ads by `pageName` first (one advertiser mass-posting near-identical creatives inflates apparent advertiser count — e.g. a single advertiser once accounted for 22 of 29 sampled ads). Compute unique advertisers on the deduped set.
   - On the deduped sample, classify each ad by whether its copy / landing domain actually belongs to the target product category. Compute the **relevant share** = relevant ads ÷ sampled ads.
   - **If relevant share < 60%** (or the blacklist flags an obvious hijack like养生/保健品 affiliates packing home-organizer scene words, or paint/pesticide sprayers under `oil sprayer`): the keyword is polluted. Do NOT report the polluted numbers as the result.

5. **Narrow-and-retry loop (automatic, when step 4 flags pollution).** Pick a more specific keyword that removes the ambiguity — add a category qualifier (`oil sprayer` → `olive oil mister`), or move to the exact product-form word (`over door organizer` → `over door hanging bag`). Use the blacklist's "收窄建议方向" column. Re-run the scraper + analyzer + pollution self-check on the narrowed keyword. Repeat at most **twice**; if still polluted after two narrowings, stop and surface the issue to the user with the candidate narrowed keywords you tried and their relevant shares — this is the only case where a human decides. **Whatever keyword finally passes the self-check is the keyword of record** — it must be reported back so Google Trends and 1688 re-run on the same narrowed word (see the `product-cross-validation` skill's 口径对齐铁律).

6. Summarize the report for the user in their preferred language. Include:
   - the **keyword of record** (and, if it was narrowed, the original keyword + why it was rejected + the relevant share before/after)
   - active result count (with the caveat that it is a raw platform figure, not validated demand)
   - sampled ad count and **relevant share** after dedup
   - unique advertiser count (deduped by `pageName`)
   - 30/90/180-day active ad counts
   - top hooks
   - advertiser and landing-domain patterns
   - final decision: avoid / monitor / test / scale research
   - recommended creative test angles and risks

## Implementation Notes

- The scraper uses Puppeteer with local Chrome. If sandboxed Chrome launch fails, rerun the scraper with escalated permission and explain that the action is read-only browser automation against Meta Ad Library public pages.
- Default Chrome path is `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. Override with `--chrome-path` if needed.
- Meta Ad Library is dynamically rendered and may stop returning more cards under headless automation. Treat the scrape as a sampled read, not a complete archive export.
- The parser reads visible page text. Some video ads may have empty copy; report text coverage so the user understands confidence.
- Do not claim spend, impressions, or exact performance unless the collected data actually contains those fields. For ordinary commercial ads, this workflow infers demand from ad volume, advertiser diversity, and ad longevity.

## Scoring Heuristics

- **Always interpret counts on the post-pollution-check, deduped sample — never on raw `reportedResultCount`.** A polluted or un-deduped count is meaningless.
- `200-800` active ads usually means validated demand with manageable competition.
- Many `30+ day` active ads means advertisers are not just briefly testing.
- `90+ day` and `180+ day` ads are stronger long-running signals.
- High advertiser diversity (deduped by `pageName`) means market demand is broad, but it also means more competitive pressure.
- Repeated hooks show market-proven angles; they also reveal sameness risk.
- A keyword that only passes after narrowing is a useful finding in itself: it tells you the broad concept is not a clean market and the real opportunity sits at the narrowed product form.

## Output Locations

Default to `generated/ad-library-product-validator/` for generated JSON, screenshots, and reports unless the user asks for another location.

If this run is part of the cross-border product-selection pipeline, put the final JSON and `.report.md` into the workspace (`$WORKSPACE_DIR/原始数据/ad-library/` and `$WORKSPACE_DIR/单品报告/`, from `pipeline.config`) instead — keep debug/intermediate artifacts (`.deep`/`.live`/`.sample`/`.skill-test` suffixes, probe screenshots) in `generated/` and only promote the final version.

Use filename slugs based on the keyword, for example:

```text
compression-packing-cubes.json
compression-packing-cubes.report.md
compression-packing-cubes.png
```
