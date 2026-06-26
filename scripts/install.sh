#!/usr/bin/env bash
# ============================================================
# 跨境选品自动化 · 安装脚本
# ============================================================
# 做什么:
#   1. 检查环境依赖(Node / Python3 / puppeteer / gh / chrome)
#   2. 读 pipeline.config 拿安装路径
#   3. 把 6 个核心 skill 拷到你的 SKILLS_DIR
#   4. 创建工作区目录
#   5. 检查 chrome-devtools MCP 是否配好(没配则给出配置指引)
#   6. 打印下一步
#
# 它【不会】偷偷安装任何东西或改你已有的 skill。缺依赖时只告诉你怎么补。
#
# 用法:
#   bash scripts/install.sh            首次安装(已存在的 skill 会跳过,不覆盖)
#   bash scripts/install.sh --update   增量更新(覆盖更新已存在的 skill 到最新版)
#                                      —— 配合 git pull 用:先 git pull 拉最新代码,
#                                         再 bash scripts/install.sh --update
# ============================================================
set -uo pipefail
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KIT_DIR"

# 解析参数:--update / -u 表示覆盖更新已存在的 skill
UPDATE_MODE=0
for arg in "$@"; do
  case "$arg" in
    --update|-u) UPDATE_MODE=1 ;;
    -h|--help)
      echo "用法: bash scripts/install.sh [--update]"
      echo "  (无参数)  首次安装,已存在的 skill 跳过不覆盖"
      echo "  --update  增量更新,覆盖已存在的 skill 到最新版(先 git pull 再跑本命令)"
      exit 0 ;;
    *) echo "未知参数: $arg(可用: --update / --help)"; exit 1 ;;
  esac
done

c_ok(){ printf "  ✅ %s\n" "$1"; }
c_no(){ printf "  ❌ %s\n" "$1"; }
c_warn(){ printf "  ⚠️  %s\n" "$1"; }
hr(){ printf "\n──────────────────────────────────────────\n"; }

echo "🛒 跨境选品自动化 · 安装"
hr
echo "【1/5】检查环境依赖"

MISSING=0
check_cmd(){ # name  min-hint
  if command -v "$1" >/dev/null 2>&1; then c_ok "$1 已安装 ($("$1" --version 2>&1 | head -1))"
  else c_no "$1 未安装 —— $2"; MISSING=1; fi
}
check_cmd node   "装 Node 18+:https://nodejs.org 或 brew install node"
check_cmd python3 "装 Python 3.9+:https://python.org 或 brew install python"
check_cmd gh     "(仅发布到 GitHub 时需要)装 GitHub CLI:https://cli.github.com 或 brew install gh"

# puppeteer(Ad Library / 1688 抓取依赖)
if node -e "require('puppeteer')" >/dev/null 2>&1; then c_ok "puppeteer 可用"
else c_warn "puppeteer 未安装 —— Ad Library/1688 抓取需要。在某个 node 项目里跑: npm i puppeteer"; fi

# Chrome
if [ -d "/Applications/Google Chrome.app" ] || command -v google-chrome >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1; then
  c_ok "Chrome/Chromium 已安装"
else c_warn "未检测到 Chrome —— puppeteer 抓取与 chrome-devtools MCP 都需要浏览器"; fi

hr
echo "【2/5】读取配置"
CONFIG="$KIT_DIR/config/pipeline.config"
if [ ! -f "$CONFIG" ]; then
  c_no "未找到 config/pipeline.config"
  echo "     先复制模板并填写你自己的值:"
  echo "       cp config/pipeline.config.example config/pipeline.config"
  echo "     （或运行 installer 引导 skill 自动生成）然后重跑本脚本。"
  exit 1
fi
# shellcheck disable=SC1091
source "$KIT_DIR/scripts/load_config.sh"
c_ok "配置已加载:SKILLS_DIR=$SKILLS_DIR"
c_ok "工作区:WORKSPACE_DIR=$WORKSPACE_DIR"

hr
if [ "$UPDATE_MODE" -eq 1 ]; then
  echo "【3/5】更新核心 skill 到 $SKILLS_DIR(--update:覆盖已存在的)"
else
  echo "【3/5】安装核心 skill 到 $SKILLS_DIR(已存在的跳过;要更新加 --update)"
fi
mkdir -p "$SKILLS_DIR"
INSTALLED=0; UPDATED=0; SKIPPED=0
for s in product-signal-sources amazon-trend-signal ad-library-product-validator \
         google-trends-product-validator 1688-supplier-validator product-cross-validation; do
  src="$KIT_DIR/skills/$s"
  dst="$SKILLS_DIR/$s"
  if [ ! -d "$src" ]; then c_no "$s 源缺失($src)—— 仓库可能不完整,先 git pull"; continue; fi
  if [ -d "$dst" ]; then
    if [ "$UPDATE_MODE" -eq 1 ]; then
      # 先删旧目录再整体拷贝,确保上游删掉的文件不会残留
      rm -rf "$dst" && cp -R "$src" "$dst" && { c_ok "$s 已更新"; UPDATED=$((UPDATED+1)); }
    else
      c_warn "$s 已存在 —— 跳过(要更新到最新版:bash scripts/install.sh --update)"; SKIPPED=$((SKIPPED+1))
    fi
  else
    cp -R "$src" "$dst" && { c_ok "$s 已安装"; INSTALLED=$((INSTALLED+1)); }
  fi
done
echo "     新装 $INSTALLED · 更新 $UPDATED · 跳过 $SKIPPED。"

hr
echo "【4/5】创建工作区目录"
mkdir -p "$WORKSPACE_DIR"/{原始数据,单品报告,最终看板} "${PUBLISH_DIR:-$HOME/cross-border-selection/pages}"
c_ok "工作区就绪:$WORKSPACE_DIR"

hr
echo "【5/5】检查 chrome-devtools MCP"
# 探测常见 MCP 配置位置(不同平台不同)
MCP_FOUND=0
for f in "$HOME/.claude.json" "$HOME/.claude/settings.json" "$HOME/.codex/config.toml" "$HOME/.openclaw/mcp.json"; do
  [ -f "$f" ] && grep -qi "chrome-devtools" "$f" 2>/dev/null && { c_ok "在 $f 检测到 chrome-devtools MCP"; MCP_FOUND=1; }
done
if [ "$MCP_FOUND" -eq 0 ]; then
  c_warn "未检测到 chrome-devtools MCP 配置。抓取 Amazon/Trends/1688 需要它。"
  echo "     Claude Code 配置示例(加到 MCP 配置):"
  echo '       claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest'
  echo "     其它平台(Codex/OpenCLAW)参见各自 MCP 配置文档,server 名为 chrome-devtools。"
fi

hr
if [ "$MISSING" -eq 1 ]; then
  echo "⚠️  有必需依赖缺失(见上方 ❌)。补齐后重跑 bash scripts/install.sh"
elif [ "$UPDATE_MODE" -eq 1 ]; then
  echo "✅ 更新完成!(更新 $UPDATED 个 skill)重启 AI 助手让新版生效。"
else
  echo "✅ 安装完成!"
fi
echo ""
echo "下一步:"
echo "  • 在你的 AI 助手里说「跑一轮跨境选品,从 Amazon 开始」"
echo "  • 或运行 installer 引导 skill 配置定时自动运行"
echo "  • 产出会存到 $WORKSPACE_DIR,看板在 最终看板/ 子目录"
echo "  • 以后升级套件:git pull 后跑 bash scripts/install.sh --update"
