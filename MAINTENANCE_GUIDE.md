# cross-border-selection-kit 手动修改说明

这份文档用于后续维护选品系统时快速定位：归一化器在哪里改、新验证标准在哪里加、执行链路怎么同步更新。

## 1. 新增数据源

归一化器位置：

```text
skills/product-signal-sources/scripts/normalize_signals.py
```

新增数据源时，按这个顺序改：

1. 新建数据源说明：

```text
skills/product-signal-sources/references/source-<name>.md
```

2. 如需抓取脚本，新建：

```text
skills/product-signal-sources/scripts/source-<name>.*
```

3. 让新数据源输出统一 schema：

```json
{
  "source": "your-source-id",
  "captured_at": "2026-07-03T10:00:00",
  "candidates": [
    {
      "raw_name": "原始标题",
      "generalized_concept": "去品牌后的通用品类",
      "source": "your-source-id",
      "signal_type": "search_volume",
      "source_metric": {
        "your_metric": 12345
      },
      "brand_locked": false,
      "raw_url": "",
      "category": "",
      "risk_notes": [],
      "notes": []
    }
  ]
}
```

4. 在 `normalize_signals.py` 添加评分函数：

```python
def _your_source_score(m):
    value = m.get("your_metric") or 0
    if value >= 100000:
        return 100.0
    if value >= 30000:
        return 85.0
    if value >= 10000:
        return 70.0
    if value >= 3000:
        return 55.0
    return 25.0
```

5. 注册到 `SOURCE_METRIC_MAP`：

```python
SOURCE_METRIC_MAP = {
    "amazon-bestsellers": _amazon_rank,
    "amazon-movers": _amazon_rank,
    "tiktok-creative": _views,
    "sellersprite-api": _search_volume,
    "your-source-id": _your_source_score,
}
```

6. 测试归一化：

```bash
python3 skills/product-signal-sources/scripts/normalize_signals.py \
  source-a.json source-your-source.json \
  --out normalized-candidates.json \
  --top 8
```

## 2. 修改硬过滤规则

位置：

```text
skills/product-signal-sources/scripts/normalize_signals.py
```

修改点：

```python
REJECT_PATTERNS = re.compile(
    r"\b(gift\s?card|pharmacy|prescription|subscription|streaming|service|warranty plan)\b",
    re.I
)
```

示例：新增食品、补剂、医疗宣称过滤：

```python
REJECT_PATTERNS = re.compile(
    r"\b(gift\s?card|pharmacy|prescription|subscription|streaming|service|warranty plan|food|supplement|medical)\b",
    re.I
)
```

## 3. 修改六维打分标准

位置：

```text
skills/product-cross-validation/references/scoring-rubric.md
```

默认六维：

```text
Demand strength        25
Ads validation         20
Content spread         15
Supplier structure     20
Logistics/compliance   10
Differentiation space  10
```

如果只调整权重，直接改表格即可。建议总分仍保持 100。

## 4. 新增验证维度

入口：

```text
skills/product-cross-validation/references/scoring-rubric.md
```

步骤：

1. 在评分表里新增维度，例如：

```md
| Profit estimate | 20 | Clear margin after cost, shipping, platform fee, and ad cost |
```

2. 如需采集数据，新建独立 validator：

```text
skills/profit-estimate-validator/
```

3. 最终报告 JSON 顶层添加 `dimensions`：

```json
"dimensions": [
  {"key": "demand", "label": "需求强度", "max": 20, "evidence_label": "需求判断"},
  {"key": "ads", "label": "广告验证", "max": 15, "evidence_label": "广告判断"},
  {"key": "content", "label": "内容传播", "max": 10, "evidence_label": "内容判断"},
  {"key": "supplier", "label": "供应链", "max": 15, "evidence_label": "货源判断"},
  {"key": "logistics", "label": "物流合规", "max": 10, "evidence_label": "物流判断"},
  {"key": "differentiation", "label": "差异化", "max": 10, "evidence_label": "差异化判断"},
  {"key": "profit", "label": "利润测算", "max": 20, "evidence_label": "利润判断"}
]
```

4. 每个产品的 `scores` 添加同名 key：

```json
"scores": {
  "demand": 18,
  "ads": 12,
  "content": 8,
  "supplier": 13,
  "logistics": 8,
  "differentiation": 7,
  "profit": 16
}
```

5. 每个产品的 `evidence` 添加同名 key：

```json
"evidence": {
  "profit": "Estimated margin is acceptable after product cost, shipping, platform fee, and ad cost."
}
```

说明：`skills/product-cross-validation/scripts/render_cross_validation_report.py` 不需要改。它会根据 report JSON 的 `dimensions` 自动渲染新维度。

## 5. 修改执行链路

位置：

```text
RUNBOOK.md
```

如果新增一个验证步骤，例如利润测算，在第 4 步和第 5 步之间插入：

```md
## 第 4.5 步 · profit-estimate-validator —— 验证利润空间

目标：根据 1688 成本、物流、平台佣金、广告成本，估算利润空间。

产出：
- `$WORKSPACE_DIR/原始数据/profit/<品类slug>.json`
- 每个产品的 `profit` 分数
- 每个产品的 `profit` evidence
```

然后在第 5 步说明：`product-cross-validation` 需要读取新 validator 的结果，并写入 report JSON 的 `scores` 和 `evidence`。

## 6. 修改关键词污染规则

位置：

```text
skills/product-cross-validation/references/keyword-pollution-blacklist.md
```

适合添加：

```md
| 宽泛词 | 污染类型 | 典型错误召回 | 推荐收窄词 |
| --- | --- | --- | --- |
| oil sprayer | 跨品类歧义 | paint sprayer / pesticide sprayer | olive oil mister / kitchen oil sprayer |
```

Ad Library 和 Google Trends validator 会参考这个黑名单做自动收窄。

## 7. 修改配置项

配置模板位置：

```text
config/pipeline.config.example
```

如果新增运行参数，例如：

```bash
PROFIT_MIN_MARGIN=0.35
PROFIT_TARGET_PRICE_MULTIPLIER=3
```

需要同步检查这些文件是否要读取新配置：

```text
scripts/load_config.sh
scripts/pipeline_config.py
```

## 8. 更新已安装 skill

改完仓库后执行：

```bash
cd /Users/mark/Documents/Cursor/cross-border-selection-kit
bash scripts/install.sh --update
```

然后重启 AI 助手。

注意：不带 `--update` 时，已存在的 skill 会跳过，不会覆盖更新。

## 9. 推荐修改顺序

```text
1. 先改 source adapter 或 validator
2. 再改 normalizer 或 scoring-rubric
3. 再改 RUNBOOK.md
4. 跑一个小样本测试
5. 执行 bash scripts/install.sh --update
6. 重启 AI 助手
```

## 10. 最小测试命令

测试归一化：

```bash
python3 skills/product-signal-sources/scripts/normalize_signals.py \
  test-source.json \
  --out normalized-candidates.json \
  --top 8
```

测试报告渲染：

```bash
python3 skills/product-cross-validation/scripts/render_cross_validation_report.py \
  test-report.json \
  -o test-report.html
```

检查重点：

```text
- 新数据源是否进入 candidates
- signal_strength 是否合理
- recommendation_tier 是否符合预期
- 新维度是否出现在 HTML 报告
- scores 总分是否正确
- manual_confirmation_needed 是否正确标注
```
