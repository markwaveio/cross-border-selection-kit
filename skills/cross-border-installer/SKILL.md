---
name: cross-border-installer
description: 引导用户安装部署跨境选品自动化套件。当用户说"安装跨境选品""部署这套选品工具""帮我配置选品自动化""我刚下载了 cross-border-selection-kit"等时使用。本 skill 会逐步引导:检测/询问 AI 平台(Claude/Codex/OpenCLAW)→ 适配安装方案 → 收集配置生成 pipeline.config → 安装核心 skill → 配置定时自动运行 → 自检 → 引导开始使用。
---

# 跨境选品自动化 · 安装引导

你正在引导用户把这套跨境选品自动化套件部署到他们自己的环境。**全程用对话引导,一步问清一件事,不要一次抛一堆问题。** 每步做完确认成功再进下一步。

> 套件根目录(KIT_DIR):本 skill 所在的 `cross-border-selection-kit/`。下文命令里的 `$KIT` 指它。

## 第 0 步:欢迎 + 说明要做什么

先告诉用户这套是什么、装完能干什么、需要他配合提供什么:
- 这是一套跨境选品自动化:Amazon 信号 → Ad Library/Trends/1688 三源验证(自带关键词污染自检) → 六维打分 → 出可视化报告。
- 装完后:对 AI 说一句"跑一轮跨境选品"就全自动跑完出报告;可配成定时自动跑。
- 需要他提供:(a) 用哪个 AI 平台,(b) skill 装哪、报告存哪,(c) 是否要发布到 GitHub(可选),(d) 是否要定时。

## 第 1 步:确认 AI 平台 → 决定 skill 安装路径

问用户用的是哪个平台(或自动探测:`~/.claude` 存在=Claude Code、`~/.codex`=Codex、`~/.openclaw`=OpenCLAW)。按平台确定 `SKILLS_DIR`:

| 平台 | SKILLS_DIR | 定时机制 |
|---|---|---|
| Claude Code | `~/.claude/skills` | `/schedule` 云端 routine(首选)或系统 cron |
| Codex | `~/.codex/skills` | 系统 cron / launchd |
| OpenCLAW | `~/.openclaw/skills` | 系统 cron / launchd |
| 其它/不确定 | 问用户 skill 目录在哪 | 系统 cron / launchd |

平台细节见 `references/platform-setup.md`。

## 第 2 步:检查环境依赖

跑 `bash $KIT/scripts/install.sh` 前先确认依赖(脚本也会查,但提前讲清缺什么怎么补体验更好):
- **Node 18+**、**Python 3.9+**(必需,跑抓取/渲染脚本)
- **puppeteer**(Ad Library/1688 抓取依赖,`npm i puppeteer`)
- **Chrome/Chromium**(浏览器自动化)
- **chrome-devtools MCP**(抓 Amazon/Trends/1688 的核心,配置见 references/platform-setup.md)
- **gh CLI**(仅发布到 GitHub 时需要)

缺必需项就停下来,给出对应平台的安装命令,让用户补齐再继续。

## 第 3 步:交互收集配置 → 生成 pipeline.config

逐项问用户(给默认值,他可直接回车采用),**不要一次问完,一项一项来**:

1. **报告存哪**(WORKSPACE_DIR,默认 `~/cross-border-selection/workspace`)
2. **目标市场**(TARGET_MARKET,默认 US;可 UK/DE/JP 等)
3. **是否发布到 GitHub**(可选):
   - 不发布 → `GITHUB_OWNER` 留空,`SCHEDULE_*` 之外其余用默认。
   - 发布 → 问 GitHub 用户名(`GITHUB_OWNER`)、仓名(默认 `cross-border-selection-reports`)、**可见性**。
     - ⚠️ **必须明确提示**:`public` = 选品数据公开、会被搜索引擎索引;不确定就选 `private`。默认给 `private`。
4. **是否定时自动运行**(见第 5 步,先问 true/false 和频率)

收集完,把 `$KIT/config/pipeline.config.example` 复制为 `$KIT/config/pipeline.config`,用用户的值替换。**用 Write/Edit 工具写,逐项填**,写完读回来给用户确认一遍。

## 第 4 步:安装核心 skill + 配置免授权

1. 跑安装脚本:`bash $KIT/scripts/install.sh`(它读 config、拷6个skill到 SKILLS_DIR、建工作区、查 MCP)。确认输出"安装完成"。
2. **配置免授权**(让链路无人值守):按平台把"只读抓取+本地写文件+本地渲染"的命令加进允许列表。
   - Claude Code:加到 `~/.claude/settings.json` 或项目 `.claude/settings.local.json` 的 `permissions.allow`。具体要加的条目清单见 `references/permissions-template.md`,**注意路径要用用户的 SKILLS_DIR 替换**(不是 /Users/mark/...)。
   - Codex/OpenCLAW:对应的权限/批准配置,同样只加只读+本地动作,外发(发邮件/聊天/git push)按用户意愿决定是否加。
3. 说明:免授权只覆盖内部步骤;**对外发布(GitHub push)是否免授权由用户定**——想完全无人值守就加,想每次确认就不加。

## 第 5 步:配置定时自动运行(可选)

如果用户第 3 步选了定时,按平台生成定时配置:

- **Claude Code**:用 `/schedule` 创建一个 routine,在 `SCHEDULE_CRON` 的时间跑"一轮跨境选品"。这是云端定时,机器关机也能跑。
- **Codex / OpenCLAW / 通用**:写一个系统 cron(`crontab -e` 加一行)或 macOS launchd plist,定时调一个启动脚本(该脚本 `cd $KIT && source scripts/load_config.sh` 后触发链路)。模板见 `references/schedule-templates.md`。

问清用户**希望什么时候跑**(默认每周一早 9 点 `0 9 * * 1`),写进 config 的 `SCHEDULE_CRON`,再据此生成对应平台的定时任务。

## 第 6 步:自检(确认全部就位)

逐项验证并把结果报给用户:
- [ ] 6 个核心 skill 都在 SKILLS_DIR(`ls $SKILLS_DIR`)
- [ ] pipeline.config 存在且关键字段已填(GITHUB_OWNER 若要发布则非空)
- [ ] Node/Python/puppeteer/Chrome 都可用
- [ ] chrome-devtools MCP 已配
- [ ] 免授权清单已加(抓取/渲染命令不再弹授权)
- [ ] (若启用)定时任务已创建
- [ ] 工作区目录已建

任何一项 ❌ 就停下来帮用户修,全 ✅ 才进第 7 步。

## 第 7 步:引导开始使用

告诉用户怎么用:
- **手动跑一轮**:对 AI 说「跑一轮跨境选品,从 Amazon 开始」。AI 会自动:抓Amazon→归一化→priority品自动进三源验证(污染自检/自动收窄全自动)→六维打分→出INDEX→(若配了)发布。
- **看结果**:三个入口——(若发布)GitHub 网页 / 工作区里的 `INDEX-<日期>.md` 一页纸 / 逐品下钻看单品报告。
- **扩展**:以后想加数据源/验证维度/发布通道,分别看 `product-signal-sources` 的接入规范、`product-cross-validation/references/scoring-rubric.md` 的维度扩展规范、仿 publisher 写新通道。
- **维护**:核心方法论(关键词污染自检/三源口径对齐)已内置进 skill,正常用不用管;升级套件时重跑 install.sh 即可(已存在的 skill 会跳过,需覆盖则先删旧的)。

最后建议用户**先手动跑一轮**确认链路通,再开定时。

## 重要边界

- **绝不擅自把可见性设成 public**:涉及公开用户选品数据,必须用户明确选择,默认 private。
- **绝不偷偷安装系统级依赖**:缺 node/python/puppeteer 时给命令让用户自己装,不代装。
- **外发动作(GitHub push / 发邮件 / 发聊天)默认保留确认**,除非用户明确要完全无人值守。
- 全程在用户自己的环境操作,路径一律用 config 里的值,不要出现任何开发者的个人路径或账号。
