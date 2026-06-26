# 免授权清单模板(让链路无人值守)

把这些"只读抓取 + 本地写文件 + 本地渲染"的命令加进允许列表,链路全程不打断。
**`{SKILLS_DIR}` 和 `{WORKSPACE_DIR}` 必须替换成用户 config 里的实际值**,不要照抄开发者路径。

## Claude Code（加到 settings.json 的 permissions.allow）

```json
"permissions": {
  "allow": [
    "Bash(node {SKILLS_DIR}/1688-supplier-validator/scripts/1688-supplier-scrape.mjs *)",
    "Bash(node {SKILLS_DIR}/ad-library-product-validator/scripts/meta-ad-library-scrape.mjs *)",
    "Bash(node {SKILLS_DIR}/ad-library-product-validator/scripts/ad-library-product-validator.mjs *)",
    "Bash(python3 {SKILLS_DIR}/amazon-trend-signal/scripts/render_visual_report.py *)",
    "Bash(python3 {SKILLS_DIR}/amazon-trend-signal/scripts/parse_amazon_homepage.py *)",
    "Bash(python3 {SKILLS_DIR}/product-cross-validation/scripts/render_cross_validation_report.py *)",
    "Bash(python3 {SKILLS_DIR}/product-signal-sources/scripts/normalize_signals.py *)",
    "Bash(python3 {SKILLS_DIR}/product-cross-validation/scripts/generate_index.py *)",
    "Bash(mkdir -p {WORKSPACE_DIR}/*)",
    "mcp__chrome-devtools__navigate_page",
    "mcp__chrome-devtools__wait_for",
    "mcp__chrome-devtools__list_network_requests",
    "mcp__chrome-devtools__get_network_request",
    "mcp__chrome-devtools__list_pages",
    "mcp__chrome-devtools__new_page",
    "mcp__chrome-devtools__take_snapshot",
    "mcp__chrome-devtools__evaluate_script"
  ]
}
```

合并进已有 allow 数组,不要整体替换。改完用 `python3 -m json.tool` 验证 JSON 合法(损坏的 settings.json 会让该文件所有设置失效)。

## 外发动作（按用户意愿决定是否加）

下面这条会触发 GitHub 公开/私有发布(含 git push),**默认不加、保留每次确认**;只有用户明确要"完全无人值守"才加:

```json
"Bash(python3 {SKILLS_DIR}/product-cross-validation/scripts/publish_to_github_pages.py *)"
```

发邮件、发聊天等其它外发通道同理——默认保留确认。

## Codex / OpenCLAW

机制不同但原则一样:把上面这些"抓取/渲染/建目录"的命令加进各自的批准/允许配置,外发动作保留确认。具体配置键名参见各平台文档。
