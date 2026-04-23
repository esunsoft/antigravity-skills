---
name: task-scheduler
description: 定时执行任务和自动重试失败的命令。触发关键词：定时任务、自动重试、调度执行、schedule task、retry、cron
---

# 任务调度与自动重试 (Task Scheduler)

## 概述

为 Antigravity 环境提供轻量级任务调度能力：定时执行、失败重试、进程监控。

**核心价值**：让需要重复执行或需要重试的操作自动化，无需人工盯守。

## 适用场景

- 数据库批量操作需要分批执行并检查结果
- 长时间运行的脚本需要超时保护和自动重试
- 需要定期检查某个状态（如数据库同步进度）
- 文件处理任务需要逐批执行避免内存溢出

## 功能模块

### 1. 自动重试执行 (retry)

执行命令，失败时按指数退避策略自动重试：

```powershell
python "<skills_dir>\task-scheduler\scripts\scheduler.py" retry `
  --cmd "python process_batch.py --batch 1" `
  --max-retries 5 `
  --base-delay 10 `
  --timeout 300
```

参数说明：
- `--cmd` — 要执行的命令
- `--max-retries` — 最大重试次数（默认 3）
- `--base-delay` — 基础延迟秒数（默认 5，指数增长：5/10/20/40...）
- `--timeout` — 单次执行超时秒数（默认 600）
- `--retry-on` — 触发重试的退出码（默认非零即重试）
- `--log` — 日志文件路径（默认 stdout）

### 2. 批量顺序执行 (batch)

按顺序执行多个命令，支持失败策略：

```powershell
python "<skills_dir>\task-scheduler\scripts\scheduler.py" batch `
  --commands "commands.json" `
  --on-error continue `
  --log "batch_result.json"
```

commands.json 格式：
```json
[
  {"name": "第一步", "cmd": "python step1.py", "timeout": 120},
  {"name": "第二步", "cmd": "python step2.py", "timeout": 300, "retry": 3},
  {"name": "第三步", "cmd": "python step3.py", "depends_on": "第二步"}
]
```

### 3. 后台监控 (watch)

监控后台进程，定期报告状态：

```powershell
python "<skills_dir>\task-scheduler\scripts\scheduler.py" watch `
  --pid 12345 `
  --interval 30 `
  --timeout 3600 `
  --log "watch.log"
```

### 4. 定时执行 (schedule)

简单的定时执行（非守护进程，适合前台运行）：

```powershell
python "<skills_dir>\task-scheduler\scripts\scheduler.py" schedule `
  --cmd "python check_status.py" `
  --interval 60 `
  --count 10 `
  --until-success
```

参数说明：
- `--interval` — 执行间隔秒数
- `--count` — 最大执行次数（默认无限）
- `--until-success` — 成功后停止

## 重试策略详解

```
延迟 = base_delay × 2^(attempt - 1) + random_jitter
```

| 重试次数 | 基础延迟 5s | 延迟范围 |
|---------|-----------|---------|
| 第 1 次 | 5s | 5-7s |
| 第 2 次 | 10s | 10-14s |
| 第 3 次 | 20s | 20-28s |
| 第 4 次 | 40s | 40-56s |
| 第 5 次 | 80s | 80-112s |

## 输出格式

所有执行结果以结构化 JSON 输出到日志文件：

```json
{
  "task": "命令描述",
  "start_time": "2026-03-26T22:00:00",
  "end_time": "2026-03-26T22:05:30",
  "attempts": 3,
  "final_status": "success",
  "exit_code": 0,
  "duration_seconds": 330,
  "history": [
    {"attempt": 1, "exit_code": 1, "error": "连接超时"},
    {"attempt": 2, "exit_code": 1, "error": "连接超时"},
    {"attempt": 3, "exit_code": 0, "output": "完成"}
  ]
}
```

## 与其他 Skill 集成

- **persistent-task-tracker** — 批量执行每步完成后自动更新任务状态
- **executing-plans** — 为计划中的每个步骤添加重试保护
- **self-improvement** — 记录失败原因到 `.learnings/`

## 与 Claude Code 内置工具的关系

### vs. CronCreate 工具
- **CronCreate**：Claude Code 内置的 cron 调度工具，用于定时触发 Claude 会话
- **本 Skill**：Python 脚本级别的命令重试和批量执行

**何时使用本 Skill**：
- 需要在单次会话内执行带重试的命令
- 需要批量执行多个相关命令
- 需要指数退避重试策略

**何时使用 CronCreate**：
- 需要定时触发 Claude 会话执行任务
- 需要跨会话的定期任务调度

## 注意事项

- 所有脚本使用 Python 标准库，零外部依赖
- Windows 兼容，使用 `subprocess` 执行命令
- 日志文件使用 UTF-8 BOM 编码
- 超时使用 `subprocess.Popen` + 计时器实现（Windows 无 `signal.SIGALRM`）
