---
name: long-task-executor
description: 执行长时间运行的任务（批量处理、后台任务、大文件处理）。触发关键词：长任务、后台执行、批量处理、long running、background task
---

# 长任务执行框架 (Long Task Executor)

## 概述

为超出常规执行时间的任务提供完整的执行框架：后台执行、日志捕获、进度追踪、超时保护、资源监控。

**核心价值**：让 AI 可以启动、监控和管理长时间运行的任务，而不会被执行超时中断。

## 适用场景

- PBL 批量源码提取/导入（数百个对象）
- DataWindow 批量质量检查（数千个 .srd 文件）
- SQL Server 大表数据迁移/转换
- 批量文件处理（编码转换、格式化、重命名）
- 长时间运行的数据库脚本

## 执行模式

### 模式 1: 前台执行 + 实时日志

适合需要实时观察的任务：

```powershell
python "<skills_dir>\long-task-executor\scripts\executor.py" run `
  --cmd "python batch_process.py" `
  --timeout 3600 `
  --progress-pattern "^\[(\d+)/(\d+)\]" `
  --log "task.log"
```

### 模式 2: 后台执行 + 状态查询

适合长时间运行不需要实时观察的任务：

```powershell
# 启动后台任务，返回任务 ID
python "<skills_dir>\long-task-executor\scripts\executor.py" start `
  --cmd "python long_migration.py" `
  --timeout 7200 `
  --log "migration.log" `
  --state ".tasks/executor"

# 查询任务状态
python "<skills_dir>\long-task-executor\scripts\executor.py" status `
  --state ".tasks/executor"

# 查看输出尾部
python "<skills_dir>\long-task-executor\scripts\executor.py" tail `
  --state ".tasks/executor" `
  --lines 50

# 终止任务
python "<skills_dir>\long-task-executor\scripts\executor.py" abort `
  --state ".tasks/executor"
```

### 模式 3: 分片执行

将大任务拆分为小批次，逐批执行：

```powershell
python "<skills_dir>\long-task-executor\scripts\executor.py" chunked `
  --cmd-template "python process.py --offset {offset} --limit {limit}" `
  --total 10000 `
  --chunk-size 500 `
  --delay 5 `
  --log "chunks.json"
```

## 进度追踪

### 自动检测

通过正则匹配 stdout 输出来提取进度：

```powershell
--progress-pattern "^\[(\d+)/(\d+)\]"     # 匹配 [42/100] 格式
--progress-pattern "^Progress: (\d+)%"     # 匹配 Progress: 85% 格式
--progress-pattern "^处理第 (\d+) 条"       # 匹配中文进度
```

### 进度报告

```json
{
  "task_id": "exec_20260326_220000",
  "command": "python batch_process.py",
  "status": "running",
  "pid": 12345,
  "started_at": "2026-03-26T22:00:00",
  "elapsed_seconds": 1800,
  "timeout_seconds": 3600,
  "progress": {
    "current": 450,
    "total": 1000,
    "percentage": 45.0,
    "estimated_remaining_seconds": 2200
  },
  "resource_usage": {
    "cpu_percent": 35.2,
    "memory_mb": 256.8
  },
  "log_file": "task.log",
  "log_tail": ["最近5行输出..."]
}
```

## 资源监控

执行器自动监控任务的系统资源占用：

- **CPU 使用率** — 通过 `psutil`（如已安装）或 WMI 查询
- **内存占用** — 进程工作集大小
- **磁盘 I/O** — 输出日志的增长速度
- **超时预警** — 接近超时时间时发出警告

## 超时管理

```
┌─────────────┬────────────────────────────┐
│ 经过时间    │ 动作                        │
├─────────────┼────────────────────────────┤
│ 80% 超时   │ 输出警告到日志              │
│ 100% 超时  │ 发送 CTRL+C (graceful)      │
│ +30s       │ 强制终止 (taskkill /F)      │
└─────────────┴────────────────────────────┘
```

## 日志管理

### 日志格式

```
[2026-03-26 22:00:01] [INFO] 任务启动: python batch_process.py
[2026-03-26 22:00:01] [INFO] PID: 12345, 超时: 3600s
[2026-03-26 22:00:05] [STDOUT] 开始处理第 1 批...
[2026-03-26 22:15:30] [PROGRESS] 45% (450/1000), 预计剩余: 36m40s
[2026-03-26 22:30:00] [STDOUT] 处理完成
[2026-03-26 22:30:01] [INFO] 任务完成, 退出码: 0, 耗时: 30m0s
```

### 日志轮转

- 单个日志文件最大 50MB
- 超过后自动轮转为 `task.log.1`, `task.log.2` 等
- 最多保留 5 个历史日志

## 与其他 Skill 集成

| Skill | 集成方式 |
|-------|---------|
| **persistent-task-tracker** | 任务完成后自动更新跟踪状态 |
| **task-scheduler** | 使用 scheduler 的重试能力包装执行器 |
| **executing-plans** | 为计划中的耗时步骤提供后台执行支持 |
| **pb-orca-tool** | PBL 批量导出/导入使用分片执行模式 |
| **pb-dw-quality-check** | 批量 DW 检查使用进度追踪 |

## AI 使用指南

当 AI 需要执行长任务时：

1. **评估任务时间** — 预计超过 60 秒的任务建议使用本框架
2. **选择执行模式**：
   - < 5 分钟：前台执行 + 实时日志
   - 5-30 分钟：后台执行 + 定期查询
   - > 30 分钟：分片执行 + 进度追踪
3. **设置合理超时** — 预估时间的 2-3 倍
4. **检查结果** — 使用 `status` 或 `tail` 命令确认完成

## 注意事项

- Windows 环境无 `SIGALRM`，超时通过 `threading.Timer` 实现
- 后台进程使用 `subprocess.Popen` 启动，状态通过 PID 文件追踪
- 进程终止优先使用 `CTRL+C` 信号，30 秒后 `taskkill /F`
- 所有文件使用 UTF-8 BOM 编码
- 状态文件存储在 `--state` 指定的目录
