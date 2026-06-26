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
4. **是否定时自动运行**:这里只问"要不要定时"(true/false)。**如果要,具体几点跑放到第 5 步专门问清**——这一步先不要替用户填 `SCHEDULE_CRON`,`SCHEDULE_ENABLED` 先按用户意愿填 true/false 即可。

收集完,把 `$KIT/config/pipeline.config.example` 复制为 `$KIT/config/pipeline.config`,用用户的值替换。**用 Write/Edit 工具写,逐项填**,写完读回来给用户确认一遍。

## 第 4 步:安装核心 skill + 配置免授权

1. 跑安装脚本:`bash $KIT/scripts/install.sh`(它读 config、拷6个skill到 SKILLS_DIR、建工作区、查 MCP)。确认输出"安装完成"。
2. **配置免授权**(让链路无人值守):按平台把"只读抓取+本地写文件+本地渲染"的命令加进允许列表。
   - Claude Code:加到 `~/.claude/settings.json` 或项目 `.claude/settings.local.json` 的 `permissions.allow`。具体要加的条目清单见 `references/permissions-template.md`,**注意路径要用用户的 SKILLS_DIR 替换**(不是 /Users/mark/...)。
   - Codex/OpenCLAW:对应的权限/批准配置,同样只加只读+本地动作,外发(发邮件/聊天/git push)按用户意愿决定是否加。
3. 说明:免授权只覆盖内部步骤;**对外发布(GitHub push)是否免授权由用户定**——想完全无人值守就加,想每次确认就不加。

## 第 5 步:配置定时自动运行(可选)

**仅当用户在第 3 步明确选了"要定时"才做这步。** 如果用户没要定时,直接跳过,**不要擅自建任何定时任务**。

如果用户要定时,**必须先问清两件事,拿到答复后才能动手——不许用默认值替用户决定**:

1. **几点跑?**(频率 + 具体时间)。给参考(每周一早 9 点 / 每天早 8 点 / 每月 1 号),但**等用户回答**,把用户给的时间换算成 cron 表达式写进 config 的 `SCHEDULE_CRON`。
   > ⚠️ 常见错误:直接套默认 `0 9 * * 1` 就把定时建好了,从没问用户。**这是不对的**——定时几点跑是用户的决定,必须问。
2. **定时跑到外发步(GitHub 发布)怎么办?** 如果用户配了发布、又希望定时全自动,要提醒他:定时无人值守时,发布步要么提前免授权、要么会卡住等确认(见第 4 步的外发边界)。

确认好时间后,按平台生成定时任务:
- **Claude Code**:用 `/schedule` 创建 routine,在 `SCHEDULE_CRON` 时间跑"一轮跨境选品"。云端定时,关机也能跑。
- **Codex / OpenCLAW / 通用**:写系统 cron(`crontab -e`)或 macOS launchd plist,定时调启动脚本(`cd $KIT && source scripts/load_config.sh` 后触发链路)。模板见 `references/schedule-templates.md`。

建议用户**先手动成功跑通一轮再开定时**,避免定时半夜卡在某个没配好的环节。

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

## 第 7 步:引导开始使用 + 维护说明

**这步要把"怎么用"和"以后怎么维护"都讲清楚,不要只说一句"跑一轮"就结束。** 逐块讲给用户:

### A. 手动跑一轮
对 AI 说「**跑一轮跨境选品,从 Amazon 开始**」。AI 会按 kit 根目录的 `RUNBOOK.md` 顺序执行:
第1步 Amazon 发现候选品 → priority 品自动进 → 第2步 Ad Library → 第3步 Trends → 第4步 1688 →(污染自检/自动收窄全程自动)→ 第5步 六维打分出看板。
> 提醒用户:**如果 Amazon 被反爬拦了(503/验证码),AI 会停下来问你**(重试 / 你直接给品 / 推导但标注),不会偷偷编一组假品——这是故意设计的,别误以为是卡住了。

### B. 看结果(报表查看说明)
所有产出都在 `$WORKSPACE_DIR` 下:
- **最终看板**:`$WORKSPACE_DIR/最终看板/cross-validation-product-report-<日期>-vN.html` —— 浏览器直接打开,这是带排名和决策的主报告。
- **单品报告**:`$WORKSPACE_DIR/单品报告/<品类>.report.md` —— 单个品的 Ad Library 详细分析。
- **原始数据**:`$WORKSPACE_DIR/原始数据/{ad-library,google-trends,1688}/` —— 每步实抓的原始 JSON,想核证据看这里。
- **(若开了发布)** GitHub 网页:`https://<GITHUB_OWNER>.github.io/<GITHUB_REPO>/`。
告诉用户具体的 `$WORKSPACE_DIR` 绝对路径(展开后的),方便他直接去翻。

### C. 维护说明

**① 改配置**:所有设置都在 `config/pipeline.config`,改一处全链路生效。常见改动:
- 换目标市场 → 改 `TARGET_MARKET`。
- 改定时时间 → 改 `SCHEDULE_CRON`(改完要重建定时任务,见 `references/schedule-templates.md`)。

**② 以后想开 GitHub 发布**(一开始没配的话):
1. 装并登录 gh CLI:`gh auth login`(选 GitHub.com、HTTPS、按提示授权)。
2. 在 `pipeline.config` 填 `GITHUB_OWNER`=你的 GitHub 用户名、`GITHUB_REPO`=仓名、`GITHUB_VISIBILITY`=`private` 或 `public`。
   > ⚠️ `public` = 选品数据公开、会被搜索引擎索引。不确定就 `private`。
3. 下次跑完链路,让 AI 用 `publish_to_github_pages.py` 发布(**首次发布 AI 会让你确认一次**,因为内容上公网)。

**③ 关掉/改定时**:
- Claude Code:用 `/schedule` 管理 routine。
- Codex/OpenCLAW:`crontab -e` 删那行,或卸载 launchd plist(`launchctl unload ...`)。

**④ 扩展链路**:
- 加数据源(Amazon 外接更多初筛源)→ 看 `product-signal-sources/SKILL.md`。
- 加验证维度(六维外)→ 看 `product-cross-validation/references/scoring-rubric.md` 的"扩展维度"。
- 加发布通道(邮件/聊天)→ 仿 `publish_to_github_pages.py` 写新通道。

**⑤ 升级套件(增量更新)**:两步——
```bash
cd <kit 目录> && git pull        # 1. 拉最新代码
bash scripts/install.sh --update # 2. 用 --update 覆盖更新已装的 skill 到最新版
```
> ⚠️ 一定要带 `--update`。不带参数的 `install.sh` 遇到已存在的 skill **会跳过、不更新**(那是给首次安装防误覆盖用的)。带 `--update` 才会把 `$SKILLS_DIR` 里的旧 skill 覆盖成最新版。
> `pipeline.config` 是你的本地配置,`git pull` 和 `--update` 都不会动它,设置会保留。更新完**重启一次 AI 助手**让新 skill 生效。
核心方法论(关键词污染自检 / 三源口径对齐 / Amazon 抓不到不编造 / Trends 限流退避重试 / 1688 拦截换会话登录)已内置进 skill,正常用不用管。

### D. 最后
强烈建议用户**先手动成功跑通一轮**,确认浏览器登录态、MCP、抓取都通了,再开定时。

## 重要边界

- **绝不擅自把可见性设成 public**:涉及公开用户选品数据,必须用户明确选择,默认 private。
- **绝不偷偷安装系统级依赖**:缺 node/python/puppeteer 时给命令让用户自己装,不代装。
- **外发动作(GitHub push / 发邮件 / 发聊天)默认保留确认**,除非用户明确要完全无人值守。
- 全程在用户自己的环境操作,路径一律用 config 里的值,不要出现任何开发者的个人路径或账号。
