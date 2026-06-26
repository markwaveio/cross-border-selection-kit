# 跨境选品自动化套件 · cross-border-selection-kit

一套能让 AI 助手**自动帮你做跨境电商选品**的 skill 套件。对 AI 说一句「跑一轮跨境选品」,它就从 Amazon 抓信号 → 三个独立渠道交叉验证 → 六维打分 → 出一份可视化报告。可配成定时自动跑,机器关机也能在云端跑(Claude Code)。

> 适配 **Claude Code / Codex / OpenCLAW** 三种 AI 助手。下载后用内置的引导 skill 一步步装好,不用改代码。

---

## 这套东西解决什么问题

选品最累的是**重复劳动**和**容易被假数据骗**:
- 翻 Amazon 榜单、一个个去 Ad Library / Google Trends / 1688 查、记笔记、横向对比——纯手工要大半天。
- 关键词一宽就被**蹭流量的养生联盟号、跨品类同名词**污染,`reportedResultCount` 虚高,看着火爆其实是假需求。

这套把整个流程自动化,并且**把"防被假数据骗"的纪律写进了 skill 本身**:每个验证环节自带关键词污染自检、语义歧义自检、命中污染会自动收窄关键词重试,三个渠道的关键词口径还会对齐校验。任意品类都生效,不是写死某个品。

---

## 选品漏斗(五步链路)

```
①  Amazon 信号        amazon-trend-signal
        │             抓 Best Sellers / Movers&Shakers,出初筛候选品
        ▼
   归一化 + 去重       product-signal-sources
        │             多源信号统一成候选品 schema(以后可插更多源)
        ▼
┌─────────────────────────────────────────────┐
│  三源交叉验证(priority 候选品自动进入)        │
│                                               │
│  ② Ad Library 验证   ad-library-product-validator   投放热度 + 污染自检 │
│  ③ Google Trends     google-trends-product-validator 搜索趋势 + 歧义自检 │
│  ④ 1688 供应链       1688-supplier-validator          货源 / 价格带      │
└─────────────────────────────────────────────┘
        │
        ▼
⑤  六维交叉打分       product-cross-validation
        │             需求/趋势/竞争/供应/利润/风险 → 一份可视化报告 + INDEX 一页纸
        ▼
   (可选)发布到 GitHub Pages → 一个可视化网页随时看
```

**自带的关键词纪律**(已内置,不用你操心):
- 污染自检:抓回来的结果按相关性分类,低于阈值(默认 0.6)判污染。
- 自动收窄重试:命中污染最多自动收窄 2 次,卡住才回来问你。
- 三源口径对齐:Ad Library / Trends / 1688 用的是不是同一个口径的关键词,会记录并校验,口径不一致的维度打分自动封顶。
- 污染黑名单加速:养生联盟蹭流量、跨品类同名词等已知套路直接识别。

---

## 快速开始

### 1. 下载
```bash
git clone https://github.com/markwaveio/cross-border-selection-kit.git
cd cross-border-selection-kit
```

### 2. 让 AI 引导你安装(推荐)
把这个套件目录给你的 AI 助手,对它说:

> **「我下载了 cross-border-selection-kit,帮我安装部署」**

内置的 `cross-border-installer` 引导 skill 会接管,逐步带你:
1. 确认你用哪个平台(Claude / Codex / OpenCLAW)→ 决定 skill 装哪
2. 检查依赖(Node / Python / puppeteer / Chrome / chrome-devtools MCP)
3. 交互问你几个问题 → 自动生成你的 `pipeline.config`
4. 把 6 个核心 skill 装到位 + 配好免授权(让链路无人值守)
5. (可选)配置定时自动运行——问你想几点跑
6. 自检全部就位
7. 教你怎么开始用

> 引导 skill 怎么被 AI 识别?它就是 `skills/cross-border-installer/`,装进你的 skills 目录后,说上面那句话即可触发。也可以直接让 AI「读 skills/cross-border-installer/SKILL.md 按它引导我」。

### 3. 手动安装(不想用引导)
```bash
# 复制配置模板,填你自己的值(GitHub 用户名、装哪、目标市场……)
cp config/pipeline.config.example config/pipeline.config
# 编辑 config/pipeline.config

# 跑安装脚本(检查依赖 + 拷 skill + 建工作区)
bash scripts/install.sh
```
脚本**不会偷偷装任何东西**,缺依赖只告诉你怎么补。

### 4. 跑起来
装好后,对 AI 说:

> **「跑一轮跨境选品,从 Amazon 开始」**

跑完看结果三个入口:GitHub 网页(若配了发布)/ 工作区里的 `INDEX-<日期>.md` 一页纸 / 逐品下钻看单品报告。

---

## 依赖

| 依赖 | 用途 | 必需? |
|---|---|---|
| Node 18+ | 跑 Ad Library / 1688 抓取脚本 | ✅ |
| Python 3.9+ | 归一化 / 打分 / 渲染报告 | ✅ |
| puppeteer | 驱动浏览器抓 Ad Library / 1688 | ✅ |
| Chrome / Chromium | 浏览器自动化 | ✅ |
| chrome-devtools MCP | 抓 Amazon / Trends / 1688 的核心 | ✅ |
| gh CLI | 发布到 GitHub(可选) | 仅发布时 |

具体配置见 `skills/cross-border-installer/references/platform-setup.md`。

---

## 目录结构

```
cross-border-selection-kit/
├── README.md                    ← 你在看的这份
├── config/
│   └── pipeline.config.example  ← 配置模板(复制成 pipeline.config 填自己的值)
├── scripts/
│   ├── install.sh               ← 一键安装脚本
│   ├── load_config.sh           ← 配置加载(shell)
│   └── pipeline_config.py       ← 配置加载(python)
└── skills/
    ├── cross-border-installer/  ← 安装引导 skill(从这里开始)
    ├── amazon-trend-signal/        ① Amazon 信号初筛
    ├── product-signal-sources/     归一化 + 去重(可插更多源)
    ├── ad-library-product-validator/   ② 投放热度验证
    ├── google-trends-product-validator/ ③ 搜索趋势验证
    ├── 1688-supplier-validator/        ④ 供应链验证
    └── product-cross-validation/       ⑤ 六维打分 + 出报告 + 发布
```

---

## 配置说明(pipeline.config)

| 字段 | 含义 | 默认 |
|---|---|---|
| `SKILLS_DIR` | skill 装哪 | `~/.claude/skills` |
| `WORKSPACE_DIR` | 产出存档根目录 | `~/cross-border-selection/workspace` |
| `PUBLISH_DIR` | 本地发布仓 | `~/cross-border-selection/pages` |
| `GITHUB_OWNER` | 你的 GitHub 用户名(发布用) | 留空 = 不发布 |
| `GITHUB_REPO` | 发布仓名 | `cross-border-selection-reports` |
| `GITHUB_VISIBILITY` | `public` / `private` | `private` |
| `TARGET_MARKET` | 验证哪个市场 | `US` |
| `SCHEDULE_ENABLED` | 是否定时 | `false` |
| `SCHEDULE_CRON` | 多久跑一轮 | `0 9 * * 1`(每周一 9 点) |
| `POLLUTION_THRESHOLD` | 污染自检相关性阈值 | `0.6` |

改一处,全链路生效。

---

## 扩展 & 维护

- **加数据源**(除 Amazon 外接更多初筛源/API):看 `skills/product-signal-sources/SKILL.md` 的接入规范,注册到 `SOURCE_METRIC_MAP`,归一化层会自动合流。
- **加验证维度**(六维之外加新维度):看 `skills/product-cross-validation/references/scoring-rubric.md` 的"扩展验证维度"小节,报告渲染是维度数量无关的,声明了就会画出来。
- **加发布通道**(发邮件 / 发聊天):仿 `product-cross-validation/scripts/publish_to_github_pages.py` 写一个新通道。
- **升级套件**:重跑 `bash scripts/install.sh`,已存在的 skill 会跳过;要覆盖先删旧的。

---

## ⚠️ 安全与边界

- **可见性默认 private**。`GITHUB_VISIBILITY=public` 意味着你的选品数据公开、会被搜索引擎索引——不确定就用 `private`。
- **不会偷偷装系统依赖**。缺 Node/Python/puppeteer 时给你命令,你自己装。
- **对外发布默认要确认**。GitHub push / 发邮件 / 发聊天这类外发动作,默认每次问你;只有你明确要"完全无人值守"才加进免授权。
- 抓取的都是**公开页面的只读浏览**(Amazon 榜单、公开 Ad Library、公开 Trends、1688 搜索页)。需要登录态的站(如 1688)在 MCP 浏览器里登录一次即可持久化。
- 所有路径和账号用你自己 `pipeline.config` 里的值,套件里不含任何他人的个人路径或账号。

---

## 它怎么知道数据是真是假?

这是这套和"手撸一个爬虫"最大的区别。选品最致命的坑是**被虚高数据骗着备货**。套件把几条反踩坑纪律固化进了 skill:

| 坑 | 自检 |
|---|---|
| 关键词太宽,召回一堆别的品类 | 相关性分类,低于阈值判污染、自动收窄 |
| 养生联盟号蹭关键词刷投放数 | 污染黑名单直接识别这类劫持模式 |
| `reportedResultCount` 虚高(如 5 万封顶值) | 当作劫持信号,不直接采信 |
| 同名词跨品类(如某词既是工具又是食品) | top 相关词语义歧义自检 |
| 三个渠道查的根本不是同一个口径 | 关键词口径对齐校验,不一致的维度打分封顶 |

所以它给出的"高分品",是三个独立渠道在**同一口径**下都站得住的品,而不是某一个被污染数据撑起来的假象。

---

*这套套件免费分享。装好遇到问题,把报错丢给你的 AI 助手,它能照着 installer 的引导帮你修。*
