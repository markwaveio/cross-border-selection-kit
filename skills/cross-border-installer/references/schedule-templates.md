# 定时自动运行模板

`SCHEDULE_CRON` 默认 `0 9 * * 1`(每周一早 9 点)。问清用户希望的频率后填进 config,再据此生成对应平台的定时任务。

## Claude Code — /schedule 云端 routine（首选）

用 `/schedule` 创建一个按 `SCHEDULE_CRON` 触发的 routine,任务内容是运行一轮跨境选品。云端定时,机器关机也能跑。在 Claude Code 里:
```
/schedule 每周一早9点 跑一轮跨境选品(从Amazon开始,跑完发布报告)
```
或用 schedule skill 指定 cron 表达式。

## 系统 cron（Codex / OpenCLAW / 通用）

先写一个启动脚本 `run_pipeline.sh`(放 `$KIT/scripts/`),内容是 `cd $KIT && source scripts/load_config.sh` 后触发链路(具体触发方式取决于平台 CLI 如何无头调用 AI 助手跑 skill)。然后:
```bash
crontab -e
# 加一行(把路径换成实际值):
0 9 * * 1 /bin/bash ~/cross-border-selection-kit/scripts/run_pipeline.sh >> ~/cross-border-selection/cron.log 2>&1
```

## macOS launchd（开机常驻更稳）

写 `~/Library/LaunchAgents/com.user.crossborder-selection.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.user.crossborder-selection</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>/Users/你的用户名/cross-border-selection-kit/scripts/run_pipeline.sh</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardErrorPath</key><string>/tmp/crossborder-selection.err.log</string>
</dict></plist>
```
加载:`launchctl load ~/Library/LaunchAgents/com.user.crossborder-selection.plist`

## cron 表达式速查

| 频率 | cron |
|---|---|
| 每周一 9:00 | `0 9 * * 1` |
| 每天 8:00 | `0 8 * * *` |
| 每月 1 号 9:00 | `0 9 1 * *` |
| 每 3 天 9:00 | `0 9 */3 * *` |

## 重要

- 定时跑的是**完整一轮**(含外发)。若用户没把发布加进免授权,定时跑到发布步会卡住等确认——所以**配定时前要确认免授权边界**(完全无人值守才加发布免授权)。
- 建议用户**先手动成功跑通一轮**再开定时,避免定时在半夜卡在某个没配好的环节。
