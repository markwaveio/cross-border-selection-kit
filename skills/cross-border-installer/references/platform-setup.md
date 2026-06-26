# 平台适配细节(Claude / Codex / OpenCLAW)

## skill 安装目录

| 平台 | SKILLS_DIR | 探测方式 |
|---|---|---|
| Claude Code | `~/.claude/skills` | `~/.claude` 目录存在 |
| Codex | `~/.codex/skills` | `~/.codex` 目录存在 |
| OpenCLAW | `~/.openclaw/skills` | `~/.openclaw` 目录存在 |

skill 是"一个目录含 SKILL.md"的形式,三平台通用——拷过去即被识别(可能需重启或重载 skill 列表)。

## chrome-devtools MCP 配置(三平台都需要)

抓 Amazon Best Sellers、Google Trends widget API、1688 搜索页都靠这个 MCP。

**Claude Code**:
```bash
claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest
```
或手动加到 `~/.claude.json` 的 `mcpServers`:
```json
"chrome-devtools": { "command": "npx", "args": ["-y", "chrome-devtools-mcp@latest"] }
```

**Codex**:加到 `~/.codex/config.toml`:
```toml
[mcp_servers.chrome-devtools]
command = "npx"
args = ["-y", "chrome-devtools-mcp@latest"]
```

**OpenCLAW**:加到其 MCP 配置(通常 `~/.openclaw/mcp.json`),server 名 `chrome-devtools`,启动命令同上。

配好后,需要登录态的网站(如 1688)在 MCP 的浏览器里登录一次即可持久化(见套件方法论说明)。

## puppeteer(Ad Library / 1688 抓取脚本依赖)

`meta-ad-library-scrape.mjs` 和 `1688-supplier-scrape.mjs` 用 puppeteer 驱动本地 Chrome。
```bash
# 在任意 node 环境装(全局或某项目)
npm i puppeteer
```
若沙箱启动 Chrome 失败,以提权方式重跑脚本即可(这是对公开页的只读浏览自动化)。

## 平台差异小结

- **Claude Code** 体验最完整:有 `/schedule` 云端定时、settings.json 细粒度免授权、原生 skill。推荐首选。
- **Codex / OpenCLAW**:skill 和脚本通用,但定时走系统 cron/launchd,免授权机制按各自配置。
