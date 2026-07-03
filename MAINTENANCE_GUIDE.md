# cross-border-selection-kit 手动修改维护说明

这份文档用于后续维护选品系统时快速定位：数据入口在哪里加、归一化器在哪里改、新验证标准在哪里接入、发布通道怎么扩展。

## 0. 先理解模块边界

这套系统的维护边界分成四层：

```text
数据源适配器
  ├─ Amazon 榜单
  ├─ TikTok 热门
  ├─ 卖家精灵 API
  ├─ 独立站爆款
  └─ 任意新源
        │
        ▼
product-signal-sources
归一化器：合并、去重、去品牌、过滤、打优先级
        │
        ▼
Ad Library / Google Trends / 1688 / 其它验证器
        │
        ▼
product-cross-validation
打分、决策、生成报告
        │
        ▼
发布通道：GitHub Pages / 邮件 / 飞书 / 群消息
```

维护原则：

```text
加数据源：只动 product-signal-sources
改评分标准：只动 product-cross-validation/references/scoring-rubric.md
加验证步骤：新增 validator，并同步 RUNBOOK.md
加发布通道：仿 publish_to_github_pages.py 新增脚本
不要为了加源或加维度去改报告渲染脚本
```

## 1. 新增数据源

对应模块：

```text
skills/product-signal-sources/
```

归一化器位置：

```text
skills/product-signal-sources/scripts/normalize_signals.py
```

为什么能随便加源：

```text
每个数据源都是一个独立适配器。
适配器负责把各自的数据吐成同一种候选品 schema。
归一化器只吃这种统一 schema。
下游验证完全不知道、也不关心数据来自几个源。
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

现成样板：

```text
skills/product-signal-sources/references/source-amazon.md
```

推荐优先接入：

```text
TikTok 热门视频/商品：注意登录态，不登录常返回空
卖家精灵 API：直接输出搜索量、竞品数，结构化程度最高
独立站爆款 / CJ / Doba：适合做非 Amazon 初筛源
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

常见调整方向：

```text
转化导向：提高 Demand strength 和 Ads validation
内容种草导向：提高 Content spread
供应链导向：提高 Supplier structure
高复购耗材：新增 Repurchase / Profit 维度
稳健型打样：提高 Logistics/compliance 权重
```

示例：加入利润维度后重新分配 100 分：

```text
Demand strength        20
Ads validation         15
Content spread         10
Supplier structure     15
Logistics/compliance   10
Differentiation space  10
Profit estimate        20
```

## 4. 修改决策门槛

位置：

```text
skills/product-cross-validation/references/scoring-rubric.md
```

默认门槛：

```text
80+    sample_now：立即打样
70-79  validate_more：继续验证
60-69  watch：观察
<60    avoid：放弃
特殊   convert_to_accessory：主品被品牌/生态/风险锁死，转做配件
```

如果你想更严格，可以改成：

```text
85+    sample_now
75-84  validate_more
65-74  watch
<65    avoid
```

改门槛适合这些情况：

```text
库存风险高：提高 sample_now 门槛
现金流紧：提高 sample_now 和 validate_more 门槛
快速测品：降低 sample_now 门槛，但必须保留合规/IP硬伤一票否决
```

## 5. 新增验证维度

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

如果 report JSON 不声明 `dimensions`，渲染器会自动回退到默认六维，向后兼容。

## 6. 维护口径对齐规则

位置：

```text
skills/product-cross-validation/references/scoring-rubric.md
skills/product-cross-validation/SKILL.md
RUNBOOK.md
```

核心规则：

```text
打分前，必须确认 Ad Library / Google Trends / 1688 用的是同一个产品形态关键词。
英文和中文翻译可以不同，但产品形态必须一致。
```

如果没有对齐：

```text
1. 受影响维度最高只能给 60% 分数
2. evidence 里写清楚哪个源用了哪个关键词
3. 标记 manual_confirmation_needed
4. 不能让未对齐品靠虚高数据排到已对齐品前面
```

示例：

```text
Ad Library：olive oil mister
Google Trends：oil sprayer
1688：厨房喷油壶

问题：Google Trends 仍是宽泛词，可能混入 paint sprayer / pesticide sprayer。
处理：需求维度封顶，标 manual_confirmation_needed。
```

## 7. 修改执行链路

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

## 8. 修改关键词污染规则

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

## 9. 扩展发布通道

默认发布脚本：

```text
skills/product-cross-validation/scripts/publish_to_github_pages.py
```

如果要新增发布通道，例如邮件、飞书、Telegram、企业微信群：

1. 新建发布脚本：

```text
skills/product-cross-validation/scripts/publish_to_<channel>.py
```

2. 输入同一份最终报告：

```text
$WORKSPACE_DIR/最终看板/cross-validation-product-report-<date>-v<N>.html
$WORKSPACE_DIR/最终看板/cross-validation-product-report-<date>-v<N>.json
```

3. 只处理“送达方式”，不要改选品链路。

示例：

```text
publish_to_email.py：读取 HTML，发送到指定邮箱
publish_to_feishu.py：读取摘要，发送到飞书群或文档
publish_to_telegram.py：发送报告链接和前三名品
```

原则：

```text
报告怎么生成，和报告发到哪里，是两件事。
新增发布通道不要影响数据源、验证器、打分规则。
```

## 10. 修改配置项

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

## 11. 维护纪律

每次修改都建议记录：

```text
改了什么：数据源 / 权重 / 门槛 / 新维度 / 发布通道
为什么改：业务目标或历史误判原因
影响什么：候选品排序、打样门槛、报告展示、发布方式
是否需要重新跑历史样本：是 / 否
```

建议新增维护日志：

```text
CHANGELOG.md
```

不同客户或不同品类，不要直接共用一套评分规则。可以复制规则文件：

```text
skills/product-cross-validation/references/scoring-rubric-client-a.md
skills/product-cross-validation/references/scoring-rubric-beauty.md
skills/product-cross-validation/references/scoring-rubric-consumables.md
```

三条硬纪律：

```text
1. 加数据源，优先只动 product-signal-sources
2. 改验证标准，优先只动 scoring-rubric.md 和 report JSON
3. 加源、加维度、加发布通道时，通常不需要改渲染脚本
```

## 12. 更新已安装 skill

改完仓库后执行：

```bash
cd /Users/mark/Documents/Cursor/cross-border-selection-kit
bash scripts/install.sh --update
```

然后重启 AI 助手。

注意：不带 `--update` 时，已存在的 skill 会跳过，不会覆盖更新。

## 13. 推荐修改顺序

```text
1. 先改 source adapter 或 validator
2. 再改 normalizer 或 scoring-rubric
3. 再改 RUNBOOK.md
4. 跑一个小样本测试
5. 执行 bash scripts/install.sh --update
6. 重启 AI 助手
```

## 14. 最小测试命令

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
