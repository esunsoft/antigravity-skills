---
name: self-improvement
description: "Captures learnings, errors, and corrections to enable continuous improvement. Use when: (1) A command or operation fails unexpectedly, (2) User corrects Claude ('No, that's wrong...', 'Actually...'), (3) User requests a capability that doesn't exist, (4) An external API or tool fails, (5) Claude realizes its knowledge is outdated or incorrect, (6) A better approach is discovered for a recurring task. Also review learnings before major tasks."
---

# Self-Improvement Skill

记录学习、错误和修正，实现持续改进。日志存储在项目本地 `.learnings/` 目录中。

## Quick Reference

| 情景 | 操作 |
|------|------|
| 命令/操作失败 | 记录到 `.learnings/ERRORS.md` |
| 用户纠正你 | 记录到 `.learnings/LEARNINGS.md`（类别：`correction`） |
| 用户需要缺失功能 | 记录到 `.learnings/FEATURE_REQUESTS.md` |
| API/外部工具失败 | 记录到 `.learnings/ERRORS.md`（含集成详情） |
| 知识过时 | 记录到 `.learnings/LEARNINGS.md`（类别：`knowledge_gap`） |
| 发现更好方案 | 记录到 `.learnings/LEARNINGS.md`（类别：`best_practice`） |
| 广泛适用的经验 | 提升为 KI（Knowledge Item）或新 Skill |

## Setup

### 创建日志目录

在项目根目录下创建 `.learnings/` 目录：

```powershell
New-Item -ItemType Directory -Path ".learnings" -Force
```

从 `assets/` 复制模板文件，或手动创建：
- `LEARNINGS.md` — 修正、知识空白、最佳实践
- `ERRORS.md` — 命令失败、异常
- `FEATURE_REQUESTS.md` — 用户请求的功能

### 查看学习统计

```powershell
python "<skill_path>\scripts\review_learnings.py" --dir ".learnings"
```

## 日志格式

### Learning 条目

追加到 `.learnings/LEARNINGS.md`：

```markdown
## [LRN-YYYYMMDD-XXX] category

**Logged**: ISO-8601 时间戳
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
一句话描述学到了什么

### Details
完整上下文：发生了什么、哪里错了、正确做法是什么

### Suggested Action
具体的修复或改进措施

### Metadata
- Source: conversation | error | user_feedback
- Related Files: path/to/file.ext
- Tags: tag1, tag2
- See Also: LRN-20250110-001（如与已有条目相关）
- Pattern-Key: simplify.dead_code（可选，用于追踪复现模式）
- Recurrence-Count: 1（可选）

---
```

### Error 条目

追加到 `.learnings/ERRORS.md`：

```markdown
## [ERR-YYYYMMDD-XXX] command_or_tool_name

**Logged**: ISO-8601 时间戳
**Priority**: high
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
简述什么失败了

### Error
```
实际错误消息或输出
```

### Context
- 尝试的命令/操作
- 使用的输入或参数
- 相关环境细节

### Suggested Fix
如果可识别，描述可能的解决方法

### Metadata
- Reproducible: yes | no | unknown
- Related Files: path/to/file.ext
- See Also: ERR-20250110-001（如复现）

---
```

### Feature Request 条目

追加到 `.learnings/FEATURE_REQUESTS.md`：

```markdown
## [FEAT-YYYYMMDD-XXX] capability_name

**Logged**: ISO-8601 时间戳
**Priority**: medium
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Requested Capability
用户想要做什么

### User Context
为什么需要、在解决什么问题

### Complexity Estimate
simple | medium | complex

### Suggested Implementation
可以如何实现、可能扩展什么

---
```

## ID 生成

格式：`TYPE-YYYYMMDD-XXX`
- TYPE：`LRN`（学习）、`ERR`（错误）、`FEAT`（功能请求）
- YYYYMMDD：当前日期
- XXX：顺序编号或随机3字符（如 `001`、`A7B`）

## 解决条目

当问题被修复时，更新条目：

1. 将 `**Status**: pending` → `**Status**: resolved`
2. 在 Metadata 后添加：

```markdown
### Resolution
- **Resolved**: 2025-01-16T09:00:00Z
- **Notes**: 简述做了什么
```

其他状态值：
- `in_progress` — 正在处理
- `wont_fix` — 决定不处理（在 Resolution 中说明原因）
- `promoted` — 已提升为 KI 或 Skill

## 提升为持久记忆

当学习具有广泛适用性时，提升为持久存储。

### 何时提升

- 学习适用于多个文件/功能
- 任何贡献者都应该知道的知识
- 可防止反复出错
- 记录项目特有惯例

### 提升目标

| 目标 | 适合内容 |
|------|---------|
| Knowledge Item (KI) | 项目特定模式、配置、环境细节 |
| 新 Skill | 跨项目可复用的广泛技术 |
| 用户全局规则 | 应始终遵守的行为约束 |

### 提升步骤

1. 将学习内容提炼为简洁的规则或事实
2. 使用 `extracting-knowledge` Skill 判断目标（KI vs Skill）
3. 更新原始条目：`**Status**: promoted`

## 检测触发器

当你注意到以下模式时自动记录：

**纠正** → `correction`：
- "不对，应该是…"
- "实际上…"
- "你搞错了…"
- "那个过时了…"

**功能请求** → feature request：
- "你能不能也…"
- "有没有办法…"
- "为什么不能…"

**知识空白** → `knowledge_gap`：
- 用户提供了你不知道的信息
- 你引用的文档已过时
- API 行为与你的理解不同

**错误** → error entry：
- 命令返回非零退出码
- 异常或堆栈跟踪
- 超时或连接失败

## 优先级指南

| 优先级 | 使用场景 |
|--------|---------|
| `critical` | 阻塞核心功能、数据丢失风险、安全问题 |
| `high` | 显著影响、影响常见工作流、复现问题 |
| `medium` | 中等影响、有变通方案 |
| `low` | 轻微不便、边缘场景 |

## 最佳实践

1. **立即记录** — 问题刚发生时上下文最清晰
2. **具体描述** — 未来的 agent 需要快速理解
3. **包含复现步骤** — 尤其是错误
4. **链接相关文件** — 方便修复
5. **建议具体修复** — 不只是"待调查"
6. **定期审查** — 陈旧的学习会失去价值
