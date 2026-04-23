---
name: persistent-task-tracker
description: 保存和恢复跨会话的任务进度（断点续传）。触发关键词：恢复任务、继续上次、任务进度、断点续传、resume task、checkpoint
---

# 跨会话任务持久化 (Persistent Task Tracker)

## 概述

解决 AI 会话断开后任务进度丢失的问题。通过将任务状态持久化到 JSON 文件，实现跨会话的断点续传。

**核心价值**：让复杂的多步骤任务不再受限于单次会话，即使中断也能从上次进度继续。

## 适用场景

- 执行 `writing-plans` 生成的多步骤计划
- 跨天的大型重构或迁移任务
- 需要多次会话才能完成的审计/检查工作
- 任何超过 10 个步骤的实施计划

## 状态文件结构

状态文件存储在工作区 `.tasks/` 目录，格式为 JSON：

```json
{
  "task_id": "2026-03-26_feature-name",
  "title": "功能名称实施计划",
  "source_plan": "path/to/plan.md",
  "created_at": "2026-03-26T22:00:00+08:00",
  "updated_at": "2026-03-26T23:30:00+08:00",
  "status": "in_progress",
  "progress": {
    "total": 10,
    "completed": 6,
    "in_progress": 1,
    "pending": 3
  },
  "tasks": [
    {
      "id": 1,
      "title": "任务描述",
      "status": "completed",
      "started_at": "...",
      "completed_at": "...",
      "notes": "执行备注",
      "checkpoint": { "files_modified": [...], "last_command": "..." }
    }
  ],
  "context": {
    "working_directory": "d:\\project",
    "branch": "feature/xxx",
    "key_decisions": ["决策1", "决策2"]
  }
}
```

## 工具脚本

### 初始化任务

从实施计划文件创建任务跟踪状态：

```powershell
python "<skills_dir>\persistent-task-tracker\scripts\task_tracker.py" init --plan "path/to/plan.md" --title "任务名称" --dir ".tasks"
```

### 查看进度

```powershell
python "<skills_dir>\persistent-task-tracker\scripts\task_tracker.py" status --dir ".tasks"
```

### 更新任务状态

```powershell
python "<skills_dir>\persistent-task-tracker\scripts\task_tracker.py" update --task-id 3 --status completed --notes "已完成" --dir ".tasks"
```

### 恢复任务（新会话开始时）

```powershell
python "<skills_dir>\persistent-task-tracker\scripts\task_tracker.py" resume --dir ".tasks"
```

输出未完成任务清单和恢复上下文，供 AI 快速理解当前进度。

### 完成任务

```powershell
python "<skills_dir>\persistent-task-tracker\scripts\task_tracker.py" complete --dir ".tasks"
```

## 工作流程

### 新任务启动

1. 使用 `writing-plans` 生成实施计划
2. 运行 `task_tracker.py init` 初始化任务状态
3. 按计划逐步执行，每完成一步运行 `update`
4. 会话结束前运行 `status` 确认进度已保存

### 恢复继续

1. 新会话开始时运行 `task_tracker.py resume`
2. 脚本输出：上次停在哪里、已完成哪些、待完成哪些
3. 从 `in_progress` 或下一个 `pending` 任务继续

### 与 executing-plans 集成

在 `executing-plans` 的每个 Step 完成后自动调用 `update`，确保进度实时持久化。

## 注意事项

- 状态文件使用 UTF-8 BOM 编码
- `.tasks/` 目录应加入 `.gitignore`
- 支持多个并行任务（按 task_id 区分）

## 与其他工具的关系

### vs. Claude Code 内置 Task 工具
- **内置 Task 工具**：会话内任务追踪，会话结束后丢失
- **本 Skill**：持久化到磁盘，跨会话保留进度

**何时使用本 Skill**：
- 任务需要多个会话才能完成
- 需要断点续传能力
- 需要保留完整的执行历史和上下文

**何时使用内置 Task 工具**：
- 单次会话内可完成的任务
- 不需要跨会话保留进度

### vs. task-scheduler
- **task-scheduler**：自动重试和定时执行单个命令
- **本 Skill**：跨会话的多步骤任务进度管理

**何时使用本 Skill**：
- 多步骤计划需要跨会话执行
- 需要手动控制每步的执行时机

**何时使用 task-scheduler**：
- 单个命令需要自动重试
- 需要定时执行或批量执行命令
