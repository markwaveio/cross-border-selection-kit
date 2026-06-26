# Product Cross Validation Scoring Rubric

Use 100 points across six dimensions:

| Dimension | Points | Strong signal |
| --- | ---: | --- |
| Demand strength | 25 | Multiple public demand signals, Amazon/category evidence, stable or rising search interest |
| Ads validation | 20 | Multiple active advertisers, repeated angles, long-running ads, conversion-oriented landing pages |
| Content spread | 15 | Recent TikTok/YouTube content, clear demonstrations, comments asking where to buy |
| Supplier structure | 20 | Many suppliers, likely factories, friendly MOQ, customization, packaging, sample availability |
| Logistics/compliance | 10 | Small, light, non-fragile, no battery/liquid/medical/child/privacy/wireless complexity |
| Differentiation space | 10 | Clear ways to improve bundle, material, packaging, positioning, or use-case focus |

Decision thresholds:

- `sample_now`: 80+ with no severe logistics/compliance blocker.
- `validate_more`: 70-79, promising but one or two important unknowns remain.
- `watch`: 60-69, useful trend but not ready for sampling.
- `avoid`: below 60 or severe compliance/IP/logistics/brand-lock problem.
- `convert_to_accessory`: strong demand signal belongs to a brand-locked, ecosystem-locked, electronic, or high-risk core product; pursue accessories, consumables, storage, replacement parts, or bundles instead.

Evidence integrity rules:

- Do not invent live Facebook Ads Library counts, Google Trends index values, supplier counts, prices, MOQ, or quotes.
- If a platform cannot be read programmatically, provide direct links and mark the field `manual_confirmation_needed`.
- Separate public evidence from inference. Use phrases like "public evidence suggests" or "manual verification needed" when appropriate.
- Prefer exact keyword links over vague platform homepage links.

## 扩展验证维度（维护入口）

六维（需求25/广告20/内容15/供应链20/物流10/差异化10）是默认,但渲染脚本已改成**维度数量无关**——加新维度(如"竞品listing数""利润测算""评论情感")**只需三步,不改任何脚本**:

1. **rubric 加一行**:在本文件顶部的维度表里加该维度的定义(名称/满分/强信号判据),并相应调整其它维度满分让总分仍=100(或你接受非100总分)。
2. **写一个证据采集器**:跟 Ad Library/Trends/1688 平级,新建一个独立 skill 或脚本去抓该维度的证据,产出一个分数 + 一段 evidence 文字。
3. **report JSON 里多一个键 + 声明 dimensions**:
   - 每个 product 的 `scores` 加该维度键(如 `"reviews": 7`)、`evidence` 加同名键的文字。
   - 在 report 顶层加 `dimensions` 块声明全部维度(含新维度),renderer 按它动态画:
   ```json
   "dimensions": [
     {"key":"demand","label":"需求强度","max":25,"evidence_label":"需求判断"},
     {"key":"reviews","label":"评论情感","max":10,"evidence_label":"评论判断"}
   ]
   ```
   若不写 `dimensions`,renderer 回退到内置六维(向后兼容)。`render_cross_validation_report.py` 的 `DEFAULT_DIMENSIONS` 是回退定义。

**关键:维度数量、标签、满分全由 JSON 的 `dimensions` 驱动,报告会自动多/少一栏。** 不用碰渲染逻辑。

Keyword-aperture integrity (enforces the Keyword Consistency 铁律 in SKILL.md):

- Before scoring a concept, confirm Ad Library / Google Trends / 1688 evidence all came from the **same product-form keyword** (the keyword of record; EN↔ZH translation of the same form is fine). Record this as `aperture_alignment: "aligned" | "misaligned"`.
- If `misaligned` (a source still used a broader/ambiguous word while another narrowed): **cap each affected dimension at 60% of its max** (Demand ≤15, Ads ≤12, Supplier ≤12 for the source(s) that drifted), mark that dimension `manual_confirmation_needed`, and name in `evidence` which source used which keyword. Do not award full points to mismatched evidence.
- A `misaligned` concept must not outrank an `aligned` concept on the strength of the mismatched dimension. When two concepts are within a few points, the aligned one ranks higher.
- A keyword that only became clean **after** narrowing is itself a signal: the broad concept is not a clean market. Note it; do not treat the pre-narrow numbers as if they validated the concept.

Common risk downgrades:

- Batteries, especially lithium or button cells.
- Liquids, powders, food, supplements, medical claims, or skin-contact claims.
- Children's products, safety equipment, wireless devices, surveillance/privacy products.
- Glass, ceramics, oversized goods, heavy metal frames, high-return apparel sizing.
- Brand/IP-locked products, platform ecosystem devices, or trademark-dependent demand.

