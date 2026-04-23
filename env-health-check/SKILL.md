---
name: env-health-check
description: 检查和清理 Claude Code 环境健康度（skills 冗余、配置冲突、资源膨胀）。触发关键词：环境健康检查、环境体检、health check、环境清理、token 优化
---

# Antigravity 环境健康检查 Skill

## 概述

本 Skill 提供两种模式来检查和维护 Antigravity 环境的健康度：

1. **快速评分** (`--quick`)：秒级输出 0-100 分的环境健康评分
2. **完整体检** (`--full`)：运行全部 7 个检查模块，生成详细报告并引导交互式修复

## 入口判断

- 用户输入含 `/health-check`、"快速评分"、"环境评分" → 使用 `--quick` 模式
- 用户输入含 `/health-audit`、"完整体检"、"全面检查"、"环境清理" → 使用 `--full` 模式
- 模糊请求 → 先运行 `--quick`，如分数 < 70 则建议 `--full`

## 使用流程

### 模式一：快速评分

```powershell
python "<this_skill_dir>\scripts\quick_score.py"
```

展示评分结果给用户，根据分数给出建议：
- ≥ 80: 告知环境健康，无需进一步操作
- 70-79: 告知基本健康，可选择性优化
- 50-69: 建议执行完整体检
- < 50: 强烈建议立即执行完整体检

### 模式二：完整体检

#### 步骤 1：运行扫描

```powershell
python "<this_skill_dir>\scripts\orchestrator.py" --pretty --output "$env:TEMP\ag-health-check.json"
```

#### 步骤 2：生成报告

```powershell
python "<this_skill_dir>\scripts\reporter.py" -i "$env:TEMP\ag-health-check.json"
```

将报告内容展示给用户（使用 Markdown 格式）。

#### 步骤 3：交互式修复

报告展示后，按以下顺序引导用户处理问题：

**第一轮：🟢 低风险自动修复**

收集所有 `risk_level == "green"` 且 `auto_fixable == true` 的 findings，向用户展示清单并询问：
> "以下 N 项可安全自动修复（删除备份文件、清理临时文件等），确认执行？(Y/n)"

description: 检查和清理 Antigravity、Claude Code CLI 及 Claude VS Extension 环境健康度（冗余清理、冲突校验、资源膨胀）。触发关键词：环境健康检查、环境体检、health check、Claude 环境审计、token 优化
---

# Antigravity & Claude 环境健康检查 (v2.0)

全面检查您的 AI 助手开发环境（Antigravity, Claude Code CLI, Claude Code VS Extension）。
自动诊断配置冗余、Token 膨胀、资源堆积、Skill 冲突、Workflows 失效及 Knowledge Item 时效性。

## 🌟 核心特性

- **多环境支持**: 自动识别并同时审计 Antigravity、Claude Code CLI 及 VS Code 插件环境。
- **Token 恢复引擎**: 精确识别 GEMINI.md/CLAUDE.md 及 Skills 中的冗余内容，预估可回收的上下文空间。
- **配置一致性**: 检查多套环境间的规则冲突（编码规范、Shell 语法、路径标准）。
- **自动化清理**: 提供一键清理备份文件、临时文件及 __pycache__ 的 PowerShell 命令。
- **分级审计报告**: 输出包含综合评分、环境对比、严重程度分组的专业 Markdown 报告。

## 🛠️ 运行模式

### 1. 快速体检 (Quick Score)
秒级运行，给出多个环境的综合健康得分和核心指标。
`python scripts/quick_score.py`

### 2. 深度审计 (Full Audit)
执行全量检查模块（配置、技能、工作流、资源、知识库、MCP、学习记录）。
`python scripts/orchestrator.py --output report.json`

### 3. 环境对比报告 (Report Generation)
将审计结果转换为美观、易读的 Markdown 报告。
`python scripts/reporter.py --input report.json --output HEALTH_REPORT.md`

## 📋 审计维度 (Module IDs)

| 模块 | 检查项 (IDs) | 重点说明 |
|------|-------------|---------|
| **Config** | CFG-001~005 | GEMINI.md/CLAUDE.md 大小、注入状态、章节分布 |
| **Skills** | SKL-001~007 | 触发词重叠、SKILL.md 体积、Windows 环境兼容性 |
| **Workflows** | WFL-001~004 | 引用脚本有效性、功能冗余、bash 语法检测 |
| **Resources** | RES-001~004 | 大体积二进制文件、孤立资源、临时文件积压 |
| **Knowledge** | KNW-001~003 | KI 时效性、引用失效检测、条目统计 |
| **MCP** | MCP-001~003 | JSON 语法验证、配置备份、Server 活跃统计 |
| **Learnings** | LRN-001~003 | 未处理的 High/Critical 条目、总量预警 |

## 🚀 触发关键词
- `环境健康检查` / `环境体检` / `health check`
- `检查 claude 环境` / `审计技能库` / `token 优化`
- `清理 claude 备份` / `优化规则文件` / `环境清理`

## 📐 架构设计

- `scripts/checks/__init__.py`: 环境发现引擎与共享数据模型。
- `scripts/quick_score.py`: 轻量级探测器。
- `scripts/orchestrator.py`: 多环境并发审计编排器。
- `scripts/reporter.py`: 跨环境汇总报告模板。
- `scripts/checks/*.py`: 领域特定的原子检查插件。

---
> [!IMPORTANT]
> 本工具仅进行读取和诊断。自动修复建议（fix_command）需由用户确认后手动在终端执行。

```powershell
python "<this_skill_dir>\scripts\quick_score.py" --json
```
