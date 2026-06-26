---
name: 1688-supplier-validator
description: Validate ecommerce product candidates against 1688 supply-chain data. Use when the user wants to check Chinese-market supplier count, price range, MOQ pattern, and export/cross-border readiness for a product keyword before sourcing or further validation.
---

# 1688 Supplier Validator

Use this skill to turn a Chinese product keyword into a 1688 supply-chain snapshot: total result pages, price range, MOQ pattern, and a sampled supplier list.

## Workflow

> ⛔ **被验证码/风控拦截时,绝不能直接判失败放弃这一步。** 这是部署后最常见的退缩。`offer_search.htm` 搜索页**本身不需要登录**,但全新自动化浏览器 profile 容易触发风控验证码——遇到时**必须按下面的升级阶梯兜底**,一直到拿到数据或穷尽手段为止:
>
> 1. **换会话**:不要在全新 puppeteer profile 上反复重试。改用 **chrome-devtools MCP 的浏览器标签页**(已有正常浏览历史、被信任),`navigate_page` 到 GBK 编码的搜索 URL,再 `evaluate_script` 提取页面文本/offer 卡片。这条通常就能绕过。
> 2. **若换会话后仍被拦/仍要求登录**:**主动停下来引导用户在这个浏览器里登录一次**——明确告诉用户:"1688 当前被验证码拦截,请在弹出的浏览器窗口扫码登录你的 1688/淘宝账号,登录后我继续抓取。" 用户扫码登录后,该会话变为可信,重试抓取。**这一步要主动引导,不要因为'搜索页理论上不需要登录'就跳过引导、直接判失败。**
> 3. **唯有上述都试过仍拿不到**(比如用户无账号、或登录后仍被风控),才停下如实告诉用户,并把该品的供应链维度标 `manual_confirmation_needed` + 附 1688 搜索直达链接(而不是悄悄当无数据)。
>
> 上一轮就出现过"1688 被登录/验证码拦截后,没引导扫码登录就直接失败"的错误——务必改为按上面阶梯兜底。

1. Confirm or infer:
   - `keyword_cn`, the Chinese search term, for example `烧烤温度计`. If the user only gives an English product name, translate/narrow it to the specific Chinese term actually used by sellers (check against the matching Ad Library English keyword from the same pipeline run for consistency — keep both validators on the same keyword of record).
   - Avoid overly broad mother-category terms; if the product is a sub-category branch (e.g. "小户型收纳组件" is too broad), narrow to the specific sub-keyword first (e.g. "门后挂袋") or the supplier sample will be polluted with unrelated sibling categories.

2. **No login is required** for `offer_search.htm` search results — it is a public page. Do not block on a login check. Prefer driving an **existing, already-used browser session** (e.g. via chrome-devtools MCP against a tab/profile with real browsing history) rather than launching a brand-new automated browser profile — see Implementation Notes below for why.

3. Build the search URL with the GBK-encoding helper (see Implementation Notes — this is mandatory, not optional):

```bash
node $SKILLS_DIR/1688-supplier-validator/scripts/1688-supplier-scrape.mjs \
  --keyword '烧烤温度计' \
  --headless false \
  --out generated/1688-supplier-validator/meat-thermometer.json
```

   If the script reports `login_required` or hits a `Captcha Interception` page, **走 Workflow 顶部的升级阶梯**(换 chrome-devtools MCP 会话 → 仍被拦就引导用户扫码登录 → 都不行才标 manual_confirmation_needed)。**不要停在"换会话"这一档就放弃**——换会话后若仍被拦,必须继续到"引导用户登录"那一档。

4. Extract from the rendered page (manually via `evaluate_script`, or via the script's `extractSearchResults` when it works):
   - total result pages (`共\s*(\d+)\s*页`)
   - price range across sampled offers (¥ values)
   - MOQ pattern (e.g. "多为1件起购" vs bulk-only)
   - distinct supplier count in the first-page sample
   - any "亚马逊"/"跨境"/"亚马逊跨境电商专供" labels — these indicate sellers already serving the export/cross-border channel, a strong supply-readiness signal

5. Summarize for the user in their preferred language:
   - total pages and what that implies about supply depth
   - price band and whether it splits into distinct tiers (e.g. basic vs premium/smart variants)
   - MOQ friendliness for small-batch sourcing
   - industrial-belt concentration if visible (e.g. 义乌/深圳/衡水) — this often signals product-tier segmentation
   - explicit cross-border/export readiness signals
   - flag any field that was only sampled from page 1 of N as `manual_confirmation_needed` per the Evidence Integrity Rules in the `product-cross-validation` skill's `references/scoring-rubric.md`

## Implementation Notes

- **GBK encoding is mandatory.** The `keywords` query param on `offer_search.htm` is parsed as GBK server-side, not UTF-8. Standard `encodeURIComponent()` on Chinese text produces mojibake titles and empty/irrelevant results. The script's `gbkPercentEncode()` (via `iconv-lite`) handles this correctly — never bypass it.
- **Search results do not require login.** Do not treat `login_required` from the script's `detectLoginWall()` heuristic as a hard blocker for basic supplier/price/MOQ data — that heuristic over-triggers on incidental login-related DOM elements. Login only matters for account-gated actions (viewing full contact details, placing orders), which this skill does not need.
- **Fresh Puppeteer profiles get risk-flagged.** A brand-new `userDataDir` profile can trigger a `Captcha Interception` redirect (`_____tmd_____/punish`) even with `headless: false` and `--disable-blink-features=AutomationControlled`. Worse, even a confirmed QR-code login scan from the user's phone may not result in an identity cookie (`unb`/`lgc`) landing in that profile — the risk system can silently withhold session sync to a flagged browser instance. If this happens, do not keep generating new QR codes; switch to an already-trusted session (chrome-devtools MCP tab) instead.
- Always run with `headless: false` regardless of login status — headless mode alone is a strong anti-bot trigger independent of the login/captcha issue above.
- `userDataDir` defaults to `generated/1688-supplier-validator/.browser-profile` to persist cookies/session across runs, but treat this as best-effort, not guaranteed.

## Output Locations

Default to `generated/1688-supplier-validator/` for generated JSON unless the user asks for another location.

If this run is part of the cross-border product-selection pipeline, put the final JSON into the workspace (`$WORKSPACE_DIR/原始数据/1688/`, from `pipeline.config`) instead.

Use filename slugs based on the product, for example:

```text
compression-packing-cubes.json
oil-sprayer.json
meat-thermometer.json
over-door-organizer.json
```

Each JSON should include: `product`, `product_en`, `search_keyword_cn`, `search_url`, `captured_at`, `total_result_pages`, `price_range_cny`, `moq_pattern`, `suppliers_sampled_page1` (array with company/price/notable signals), `distinct_supplier_count_page1`, `manual_confirmation_needed` (array of caveats), `notes`.
