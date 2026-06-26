---
name: product-signal-sources
description: 跨境选品链路的"信号采集层"——把任意数据源(Amazon榜单、TikTok、卖家精灵API、独立站等)统一抽象成可插拔的候选品适配器。每个数据源是一个独立 source adapter,输出符合统一 schema 的候选品信号;下游归一化器(normalizer)汇总、去重、去品牌、打tier,再交给四步验证。当用户要新增一个选品数据源、或要跑选品初筛、或问"怎么加新的信号源"时使用。
---

# Product Signal Sources（信号采集层 / 可插拔数据源）

## 这一层解决什么

旧链路把"抓 Amazon"和"判断候选品"焊死在 `amazon-trend-signal` 一个 skill 里,加新数据源就得改它本体。这一层把数据源**抽象成可插拔适配器**:

```
                  ┌─ amazon-bestsellers  (现有,见 references/source-amazon.md)
   信号采集层      ├─ amazon-movers       (现有变体)
 (source adapters) ├─ tiktok-creative     (留口待加)
                  ├─ sellersprite-api    (留口待加)
                  └─ <任意新源>           ← 加新源 = 加一个适配器,不碰下游
                          │ 各自输出 §统一候选品 schema
                          ▼
                   signal-normalizer       ← scripts/normalize_signals.py
                   (合并 / 去重 / 去品牌 / 过滤 / 打tier)
                          │ 统一候选品清单 (normalized-candidates.json)
                          ▼
                   下游四步验证 (Ad Library→Trends→1688→交叉验证, 不变)
```

**核心契约**:适配器只负责"从某个源拿到原始候选并吐成统一 schema";归一化、去重、打分阈值由 normalizer 统一做。这样下游永远只看到一种格式,与数据源数量无关。

## §统一候选品 Schema（所有适配器必须输出）

每个适配器输出一个 JSON:`{ "source": "<adapter-id>", "captured_at": "...", "candidates": [ <CandidateSignal>... ] }`。

每个 `CandidateSignal`:

```json
{
  "raw_name": "源上看到的原始标题(可含品牌)",
  "generalized_concept": "去品牌后的通用品类概念(下游关键词的起点)",
  "source": "amazon-bestsellers | tiktok-creative | sellersprite-api | ...",
  "signal_type": "best_seller | mover | new_release | trending_video | search_volume | ...",
  "source_metric": { "自由键值: 该源特有的强度指标,如 rank/sales/views/search_volume": null },
  "brand_locked": true,
  "raw_url": "源上的商品/视频/listing URL (可空)",
  "category": "源给的类目 (可空)",
  "risk_notes": ["IP/合规/物流等初步风险"],
  "notes": ["为什么这是个有用的信号"]
}
```

**只有 `generalized_concept` + `source` + `signal_type` + `brand_locked` 是必填**,其余尽力而为。`source_metric` 是自由 schema,容纳各源不同的强度信号(Amazon是rank、TikTok是播放量、API是搜索量)——normalizer 会把它们折算成统一可比的初筛分。

## 加一个新数据源的步骤（维护入口）

这就是你要的"后续数据源入口"。加 TikTok / 卖家精灵API / 任意新源,**只需三步,完全不碰下游**:

1. **写一个适配器**:在 `references/source-<name>.md` 写清这个源怎么抓(URL/API/反爬注意),产出符合 §统一候选品 schema 的 JSON。抓取脚本(若需要)放 `scripts/source-<name>.*`。
2. **注册到 normalizer**:在 `scripts/normalize_signals.py` 的 `SOURCE_METRIC_MAP` 里加一行,告诉它这个源的 `source_metric` 怎么折算成初筛分(例:Amazon rank 越小越好、TikTok 播放量越大越好)。
3. **跑**:`normalize_signals.py source-a.json source-b.json ... --out normalized-candidates.json`,它合并所有源、按 `generalized_concept` 去重(同概念多源命中=更强信号,加权)、过滤品牌锁定/礼品卡/服务类、打 `recommendation_tier`(priority/watch/avoid)。下游四步验证吃 `normalized-candidates.json`,不知道也不关心数据来自几个源。

**关键:下游验证四步 + 交叉验证 + INDEX + 发布,全都不用改。** 加源的改动被完全限制在这一层。

## 现有数据源

- **amazon-bestsellers / amazon-movers**:见 `references/source-amazon.md`。当前主力源,用 chrome-devtools MCP 抓 Best Sellers/Movers&Shakers。`amazon-trend-signal` skill 的抓取与去品牌逻辑等价于这个适配器 + normalizer 的组合;两者产出兼容,过渡期可并存。

## 待接入(留口)

- **tiktok-creative**:TikTok Creative Center 热门视频/商品。注意未登录常返回空(见验证log),需登录态。
- **sellersprite-api**:卖家精灵 MCP/API(见备忘log,https://open.sellersprite.com/pricing/mcp)。API 源最干净——直接吐结构化搜索量/竞品数,`source_metric` 可放 `search_volume`/`competitor_count`。
- **independent-sites / CJ / Doba**:独立站爆款、一件代发平台选品。

## 与旧 skill 的关系

`amazon-trend-signal` 仍可独立使用(单源快速跑)。这一层是它的"多源可插拔超集":当你只用 Amazon 时两者等价;当你要多源融合时走这一层。归一化后的 `normalized-candidates.json` 即下游 `product-cross-validation` 的候选品输入。
