---
name: google-trends-product-validator
description: Validate ecommerce product candidates against Google Trends search-interest data. Use when the user wants 5-year interest-over-time curves and related-searches breakout terms for two comparable product keywords, as part of cross-validating a product-selection candidate.
---

# Google Trends Product Validator

Use this skill to turn two comparable product keywords (e.g. a broad term and a specific variant) into a Google Trends interest-over-time curve plus related-searches breakout terms.

This skill is keyword-quality-aware: a high interest index is worthless if it comes from an ambiguous word pulling in unrelated traffic. After fetching, it **self-checks for semantic ambiguity** and, when the main keyword is ambiguous or a sub-segment word returns no data, it **automatically narrows the keyword and re-fetches** before reporting. This keeps the pipeline general — it rescues real demand (or correctly kills a false signal) for any product, not just pre-vetted ones.

This skill has **no standalone script** — Google Trends' internal widget API requires a session-specific `token` minted by a prior `POST /trends/api/explore` call, which only exists inside a live browser session. It cannot be replicated with a bare `curl`/script. Always drive it through chrome-devtools MCP.

## Workflow

1. Confirm or infer two keywords to compare, for example `meat thermometer` and `wireless meat thermometer` (a broad term plus a specific variant works well — it surfaces both general demand and a sub-segment's breakout terms in one page).

2. Navigate to the explore page (chrome-devtools MCP `new_page` or `navigate_page`):

```
https://trends.google.com/trends/explore?date=today%205-y&geo=US&q=<term1>,<term2>&hl=en
```

   URL-encode terms with spaces as `%20` or `+`; comma-separate the two terms in `q`.

3. `wait_for` text like `["Related queries", "Related topics", "Oops"]` to let the page finish rendering all widgets (multiline trend chart, subregion breakdown, related queries x2).

4. Use `list_network_requests` (filter `resourceTypes: ["xhr","fetch"]`) to find the underlying widget calls:
   - `GET /trends/api/widgetdata/multiline?...` — the 5-year interest-over-time curve for both terms
   - `GET /trends/api/widgetdata/relatedsearches?...` — appears **twice**, once per compared term (check the `complexKeywordsRestriction.keyword[0].value` in the request URL to tell them apart)
   - `GET /trends/api/widgetdata/comparedgeo?...` — subregion breakdown (usually not needed for product validation, can skip)

5. For each request of interest, check status:
   - **200**: use `get_network_request` with `responseFilePath` to save the raw body directly to disk (do not paste large JSON inline). Response bodies are prefixed with `)]}'\n` (a JSONP-style XSS-protection prefix) — strip the first line before parsing as JSON.
   - **429**: rate-limited. Do not retry immediately — see Rate-Limit Handling below.

6. Parse the saved `relatedsearches` response. Structure: `{"default":{"rankedList":[{"rankedKeyword":[...top terms...]}, {"rankedKeyword":[...rising/breakout terms...]}]}}`. Take the top 8 of each list, mapping `query` and `formattedValue` (the latter is either a percentage like `"+600%"` or the literal string `"Breakout"` for terms with no prior baseline).
   - **A genuine zero-result** looks like `{"default":{"rankedList":[{"rankedKeyword":[]},{"rankedKeyword":[]}]}}` — this is a valid 200 response, not a failure. It means Google doesn't have enough search volume to report related terms for that keyword. Record it as `{"top": [], "rising": [], "note": "<term> 在Google Trends上无足够搜索量数据(genuine empty result)"}` — do NOT treat this as something to keep retrying for the *same* term. But it IS a trigger for the narrow-and-retry loop below (a more specific term may have data, or the concept may genuinely lack demand — narrowing tells you which).

7. **Semantic-ambiguity self-check (mandatory).** Read `../product-cross-validation/references/keyword-pollution-blacklist.md` to fast-match known ambiguity (e.g. `oil sprayer` → `paint sprayer`). Then, for each term's `top` related list:
   - Look at the **#1 top related query**. If it is a clearly cross-category term — i.e. it would not sit on the same retail shelf as the target product (`oil sprayer`'s #1 being `paint sprayer`; a kitchen tool's #1 being a hardware/automotive word) — the main keyword is **semantically ambiguous**: its interest index is partly unrelated traffic and cannot be trusted as demand for the target product.
   - Treat an ambiguity hit, or a genuine empty result on the **more specific** of the two compared terms, as a signal to narrow (step 8).

8. **Narrow-and-retry loop (automatic, when step 7 flags ambiguity or the specific term is empty).** Replace the ambiguous/empty keyword with a more specific one that removes the cross-category traffic — add a category qualifier (`oil sprayer` → `olive oil mister` / `kitchen oil mister`), or move to the exact product-form word used by Ad Library/1688. Re-navigate, re-capture `multiline` + `relatedsearches`, and re-run the ambiguity self-check. Repeat at most **twice**. Interpreting the outcome:
   - Narrowed term now has a clean interest curve + relevant related terms → that is the keyword of record; the broad word's inflated index was noise.
   - Narrowed term is *also* a genuine empty result → the specific demand does not exist yet; report the concept as **demand not validated at this granularity** (this is a real finding, not a failure — e.g. `air fryer oil sprayer` had genuine zero data, meaning the "air-fryer-specific" angle had no measurable demand).
   - Still ambiguous after two narrowings → stop and surface to the user the terms you tried and their #1 related queries; a human decides. This is the only hand-off case.
   - **The keyword that finally passes is the keyword of record** and must be reported back so Ad Library and 1688 re-run on the same narrowed word (see the `product-cross-validation` skill's 口径对齐铁律). Never report a 5-year index from an ambiguous word as validated demand.

9. Summarize for the user:
   - the **keyword of record** for each compared term (and, if narrowed, the original term + why it was rejected: ambiguity hit / empty result)
   - 5-year average interest index for each term (which term has more sustained demand) — explicitly noting if any index was discarded as ambiguous
   - recent 6-12 week trend direction (rising/falling/seasonal spike)
   - breakout-term names — these are often specific competitor product names or sub-features worth checking against Ad Library/1688 findings (feed into the `product-cross-validation` step)

## Rate-Limit Handling

> ⛔ **429 是临时限流,不是失败。绝不能因为遇到 429 就放弃这一步、把 Trends 数据标成拿不到。** 429 的正确处理是**退避后重试**——用 `ScheduleWakeup` 错开等待窗口再回来重抓,至少重试到拿到数据或确认是真空结果为止。**直接放弃 = 处理错误。** 上一轮就出现过"Trends 429 后直接放弃、没退避重试"的错误,务必避免。
>
> 唯一例外:连续退避重试 **3 次以上**仍持续 429(说明会话被深度风控),才停下来如实告诉用户"Trends 当前持续限流,建议稍后单独重跑这一步",并在报告里把该品的 Trends 维度标 `manual_confirmation_needed`(而不是悄悄当无数据)。

Google Trends aggressively rate-limits (HTTP 429) under rapid repeated requests, and fires a `captcha-ready` Google Analytics beacon as an early warning sign right before/after a 429 — if you see this beacon in `list_network_requests`, treat the session as already under suspicion.

**退避重试的具体做法**:
- **不要立刻重试。** 短间隔重试(<~15s)会越限越狠——实测一次过早重试后,三个 widget 同时报 "Oops! Something went wrong"。
- **用 `ScheduleWakeup`,不要用 `sleep`** 来等限流窗口过去。传一个自包含的 prompt 描述重试动作(重载页面、重查目标 widget 请求、成功就保存、再遇 429 就加长退避)。
- **从 ~150 秒退避起步**,连续 429 就**逐次加长**(150s→300s→…),而不是固定间隔硬刷。
- **区分 429 和真空结果**:429 的 UI 是 "Oops! Something went wrong. Please try again in a bit."(要退避重试);真空结果是 "Hmm, your search doesn't have enough data to show here."(直接采纳,不重试)。两者长得像但处理相反。

> 给执行者的提醒:`ScheduleWakeup` 退避会让本轮链路在这一步**等待并稍后自动续跑**,这是正常的、设计内的——不是卡死。如果当前模型/环境不支持 ScheduleWakeup 这类定时唤醒,就退而求其次:明确告诉用户"需要等约 N 分钟避开 Trends 限流",并把这一步挂起,等用户回来或稍后手动续跑,**仍然不要直接放弃**。

## Output Locations

Default to `generated/ad-library-product-validator/` (shared with the Ad Library validator for the same pipeline run) unless the user asks for another location.

If this run is part of the cross-border product-selection pipeline, put the raw captures and aggregated summary into the workspace (`$WORKSPACE_DIR/原始数据/google-trends/`, from `pipeline.config`) instead.

- Raw network captures: `trends-<slug>-multiline.network-response`, `trends-<slug>-related.network-response`
- Aggregated summary: `trends-summary-all-products.json`, keyed by product slug, each entry containing `keywords` (the two compared terms), `multiline` (curve summary), `related_keyword_1`/`related_keyword_2` (top/rising arrays matching the two compared keywords by position)
