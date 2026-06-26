# Source Adapter: amazon-bestsellers / amazon-movers

> 现有主力数据源的适配器规范。这是"参照实现"——加新源时照这个结构写一份 `source-<name>.md`。

## adapter id
- `amazon-bestsellers`（Best Sellers 榜,成熟需求）
- `amazon-movers`（Movers & Shakers,最强趋势信号）

## 怎么抓
用 chrome-devtools MCP（已在 settings 免授权白名单）:
1. `navigate_page` 到类目榜单 URL,例:
   - Best Sellers Home&Kitchen: `https://www.amazon.com/Best-Sellers-Home-Kitchen/zgbs/home-garden`
   - Kitchen&Dining: `https://www.amazon.com/Best-Sellers-Kitchen-Dining/zgbs/kitchen`
   - Movers&Shakers: `https://www.amazon.com/gp/movers-and-shakers`（注意:Any Department 落地页常空,M&S 网格懒加载经常对自动化隐藏;用具体类目 zgbs 页更稳）
2. `wait_for` 榜单文案;`evaluate_script` 提取 `div[id^="gridItemRoot"]` 里的 `.zg-bdg-text`(rank)、`a[href*="/dp/"]`(ASIN)、`img[alt]`(标题)、`.a-price .a-offscreen`(价格)。
3. 反爬:不并行开页、不逐个点详情页、遇 503/CAPTCHA 立即停并记 `risk_signal_seen`（详见 amazon-trend-signal/references/amazon-sources.md 的 Anti-Blocking Guardrails）。

## 去品牌（生成 generalized_concept）
把榜单标题去掉品牌/型号,留通用品类。例(见 amazon-trend-signal/references/amazon-sources.md 的 Generalization Examples):
- `STANLEY Quencher H2.0 Tumbler` → `insulated tumbler with handle and straw`（但 STANLEY 是强品牌 → `brand_locked: true`）
- `Air Fryer Paper Liners 125Pcs` → `air fryer disposable paper liners`（无品牌 → `brand_locked: false`）

## 输出（§统一候选品 schema）
```json
{
  "source": "amazon-bestsellers",
  "captured_at": "2026-06-26",
  "candidates": [
    {
      "raw_name": "Air Fryer Paper Liners, 125Pcs ...",
      "generalized_concept": "air fryer disposable paper liners",
      "source": "amazon-bestsellers",
      "signal_type": "best_seller",
      "source_metric": {"rank": 15},
      "brand_locked": false,
      "raw_url": "https://www.amazon.com/dp/B0C6Y8NYK1",
      "category": "Kitchen & Dining",
      "risk_notes": ["纯耗材单价低,利润靠复购"],
      "notes": ["空气炸锅装机量大,纸垫是高复购耗材"]
    }
  ]
}
```

## normalizer 折算规则
已在 `scripts/normalize_signals.py` 的 `SOURCE_METRIC_MAP` 注册:
```python
"amazon-bestsellers": _amazon_rank,   # rank 越小越强: rank1→~100, rank100→~10
"amazon-movers": _amazon_rank,
```

## 与旧 amazon-trend-signal 的关系
旧 skill 把"抓+去品牌+打分+出报告"一条龙做完,适合单源快速跑。本适配器只做"抓+去品牌+吐统一schema"那部分;打分阈值/去重/tier 交给 normalizer。两者产出兼容——单 Amazon 源时,旧 skill 的 items 数组 ≈ 本适配器 candidates 经 normalizer 处理后的结果。
