# 跨境选品链路 · 执行手册(RUNBOOK)

> 这份文档给**正在执行链路的 AI 助手**看(Claude / Codex / OpenCLAW 任意模型)。
> 用户说「跑一轮跨境选品」时,**严格按本手册顺序执行**,不要跳步、不要自行发挥。
> 每一步都写清了:做什么、用哪个 skill、产出什么、存哪、什么情况下停下来问人。

---

## 0. 执行前先确认两件事

1. **读 config**:找到 kit 根目录的 `config/pipeline.config`,`source scripts/load_config.sh` 拿到这些变量(后文都用):
   - `$SKILLS_DIR`(skill 装哪)、`$WORKSPACE_DIR`(产出存哪)、`$TARGET_MARKET`(验证哪个市场)、`$GITHUB_OWNER`(空=不发布)。
2. **产出根目录**:本轮所有文件都写进 `$WORKSPACE_DIR` 下的固定子目录(下面每步会标),**不要写进 kit 仓库目录、也不要写进当前工作目录**。先建好:
   ```bash
   mkdir -p "$WORKSPACE_DIR"/{原始数据/{ad-library,google-trends,1688},单品报告,最终看板}
   ```

> ⚠️ **贯穿全程的两条铁律**(违反任意一条 = 本轮作废):
> - **绝不编造数据。** 读不到的广告数/搜索指数/供应商数/价格/MOQ,一律标 `manual_confirmation_needed` 并附直达链接,不许填一个看起来合理的数字。
> - **绝不编造候选品。** 候选品只能来自:Amazon 实抓 / 用户提供 / 明确标注的推导。说不清来源的品不许进报告。

---

## 第 1 步 · amazon-trend-signal —— 发现候选品(链路起点)

**目标**:从 Amazon 榜单拿到一批真实候选品概念(去品牌、可跨平台验证)。

**怎么做**:用 `amazon-trend-signal` skill,通过 chrome-devtools MCP 抓 Best Sellers / Movers & Shakers。市场用 `$TARGET_MARKET`。

**⛔ 抓不到时怎么办**(这是部署后最常见的坑,务必照做):
Amazon 经常 503/验证码/反爬,**全新环境命中率更高**。抓不到时**绝不能自己编几个"低风险品"硬往下跑**。按顺序:
1. 停下,如实告诉用户"Amazon 实时抓取被拦,没拿到真实候选品"。
2. 给用户三选一:**(a)** 换已有正常历史的浏览器会话/稍后重试;**(b)** 用户直接给想验证的品/关键词;**(c)** 基于公开信息推导候选品——但每个品必须标 `candidate_source: "derived_not_scraped"`,报告顶部红字写明"本轮为推导非实抓,需人工复核"。
3. JSON 的 `risk_signal_seen` 如实填(如 `"amazon_503_blocked"`),不许填 `null`。

**产出**:
- JSON:`$WORKSPACE_DIR/最终看板/amazon-trend-signal-<date>.json`(每个 item 带 `candidate_source` 字段)
- HTML 看板:`$WORKSPACE_DIR/最终看板/amazon-trend-signal-<date>.html`(用 `render_visual_report.py`)

**交付给下一步的是什么**:看板里 `recommendation_tier: "priority"` 的候选品 —— 这些**直接进第 2 步**,不用每轮问用户选哪几个。每个 priority 品要带:去品牌后的概念、对应的**英文关键词**(给 Ad Library/Trends 用)、对应的**中文关键词**(给 1688 用)。

---

## 第 2 步 · ad-library-product-validator —— 验证广告投放强度

**目标**:每个 priority 品,用 Meta Ad Library 公开页实抓广告数据,判断真实投放热度。

**怎么做**:用 `ad-library-product-validator` skill(内含 puppeteer 抓取脚本)。关键词用第 1 步给的**英文词**(中文词在美区 Ad Library 搜不到)。市场 `$TARGET_MARKET`。

**自带的关键词纪律(skill 已内置,会自动执行,你不用额外提醒)**:
- **污染自检**:按 `pageName` 去重后看相关占比,**< 60% 判污染**;`reportedResultCount` 顶到平台上限(5万)不等于需求大。
- **自动收窄重抓**:判定污染就自动换更精确的词重抓,最多两次;两次还不干净才停下问人。
- **收窄出的"关键词 of record" 必须回传**,让第 3、4 步用同一个词(口径对齐)。

**产出**:
- 原始抓取:`$WORKSPACE_DIR/原始数据/ad-library/<品类slug>.json`
- 单品分析:`$WORKSPACE_DIR/单品报告/<品类slug>.report.md`

---

## 第 3 步 · google-trends-product-validator —— 验证搜索需求趋势

**目标**:每个 priority 品,跑 Google Trends 5 年趋势曲线 + related searches 突破词。

**怎么做**:用 `google-trends-product-validator` skill。**必须用 chrome-devtools MCP 拦截 Trends widget API**(token 要浏览器现场拿,裸 curl 不行)。关键词用第 2 步对齐后的词,地区 `$TARGET_MARKET`。

**自带纪律(skill 已内置)**:
- **429 限流 ≠ 空结果**:限流 UI 显示 "Oops! Something went wrong"(要退避重试,从~150秒起步,别短间隔硬刷);真空结果显示 "doesn't have enough data"(直接采纳)。
- **语义歧义自检**:看 related searches top 第 1 名,若是跨品类词(如 oil sprayer→paint sprayer)即判主词歧义,自动收窄重抓。

**产出**:
- 原始响应:`$WORKSPACE_DIR/原始数据/google-trends/trends-<slug>-*.network-response`
- 汇总:`$WORKSPACE_DIR/原始数据/google-trends/trends-summary-all-products.json`

---

## 第 4 步 · 1688-supplier-validator —— 验证供应链深度

**目标**:每个 priority 品,搜 1688 拿总结果页数、价格区间、MOQ、首页供应商样本、有无"亚马逊/跨境专供"标注。

**怎么做**:用 `1688-supplier-validator` skill。关键词用对应**中文词**。
- **中文关键词必须 GBK 编码**(脚本已处理好,别绕过 `gbkPercentEncode`)。
- **搜索页不需要登录**,别被 `login_required` 误判吓到。若一定要登录又被风控,换已有正常历史的浏览器会话(chrome-devtools MCP),别死磕新 profile 扫码。

**产出**:`$WORKSPACE_DIR/原始数据/1688/<品类slug>.json`

---

## 第 5 步 · product-cross-validation —— 六维打分定结论

**目标**:把前四步证据汇总进六维打分,排序,给决策,出可视化看板。

**怎么做**:用 `product-cross-validation` skill。
- 六维:需求25 / 广告20 / 内容15 / 供应链20 / 物流合规10 / 差异化10(满分100),阈值见 `references/scoring-rubric.md`。
- **口径对齐铁律**:打分前先列出 Ad Library / Trends / 1688 各自实际用的关键词,**口径不齐就把受影响维度封顶 60% 并标红 `manual_confirmation_needed`**。JSON 填 `keyword_of_record`/`aperture_alignment`/`alignment_note`。
- **读不到的数据全标 `manual_confirmation_needed`,严禁编造。**

**输出位置(再次强调,别写错地方)**:
```bash
source "$KIT_DIR/scripts/load_config.sh"
OUT="$WORKSPACE_DIR/最终看板"; mkdir -p "$OUT"
python3 "$SKILLS_DIR/product-cross-validation/scripts/render_cross_validation_report.py" \
  "$OUT/cross-validation-product-report-<date>-v<N>.json" \
  -o "$OUT/cross-validation-product-report-<date>-v<N>.html"
```
版本号递增(v1→v2→…),**绝不覆盖旧版**。

**产出**:
- HTML 看板 + 源 JSON:`$WORKSPACE_DIR/最终看板/cross-validation-product-report-<date>-v<N>.{html,json}`
- (可选)一页纸索引:`generate_index.py` 出 `$WORKSPACE_DIR/INDEX-<date>.md`

---

## 第 6 步(可选)· 发布到 GitHub Pages

仅当 `$GITHUB_OWNER` 非空且用户开启了发布时执行。
- **这是外发动作(内容上公网)**:除非用户明确要"完全无人值守",**第一次发布前必须问一次用户确认**。
- 用 `product-cross-validation/scripts/publish_to_github_pages.py`,可见性读 config 的 `GITHUB_VISIBILITY`(默认 private)。

---

## 跑完后告诉用户什么

1. **本轮候选品来源**:实抓 / 用户提供 / 推导(如果是推导,明确提示需人工复核)。
2. **排名 + 决策**:每个品的分数、决策(优先打样/继续验证/观察/放弃/转配件)、最该先打样的是哪个。
3. **存哪**:`$WORKSPACE_DIR/最终看板/` 的 HTML 看板路径。
4. **哪些数据是 `manual_confirmation_needed`**:让用户知道哪些数字还需人工核实,附了直达链接。
