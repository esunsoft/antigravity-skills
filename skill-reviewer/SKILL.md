---
name: skill-reviewer
description: Comprehensive quality audit for AI skills across Antigravity and Claude Code environments. Reviews structure, references, triggers, design quality, security, and cross-environment consistency against 8 engineering principles (41 rules). Use when auditing skill quality, checking for security issues, validating skill design, or reviewing skill ecosystem health. Trigger keywords - skill review, skill audit, skill quality, skill check, Skill 审查, 质量检查, 安全审查, 技能审计, Skill 评分.
---

# Skill Reviewer

对 AI Skills 进行全方位质量审查，基于 8 大工程设计原则、41 条规则。

## 前置要求：输出目录

**执行任何审查前，必须先确认输出目录。**

- 如果用户在请求中明确指定了输出目录（如 `d:\reports`），直接使用
- 如果用户未指定，**必须询问用户**：「请提供审查报告的输出目录路径」
- **禁止**默认使用 `$env:TEMP` 或其他临时目录

所有中间产物（JSON 数据、Markdown 报告）均输出到用户指定的目录下。

## 运行模式

### 快速模式（默认）

纯 Python 脚本执行，秒级出结果，零 Token 消耗。

```
python "<skills_dir>/skill-reviewer/scripts/quick_score.py"
```

参数：
- `--env antigravity` — 仅审查 Antigravity 环境
- `--env claude` — 仅审查 Claude Code 环境
- `--path <路径>` — 审查自定义路径下的 Skill（单个 Skill 目录或包含多个 Skills 的父目录）
- `<skill-name>` — 聚焦审查单个 Skill（仅在标准环境下有效）
- `--json` — 输出 JSON 格式（供脚本调用或报告生成器使用）

执行流程：
1. 向用户确认输出目录
2. 运行快速评分：
   - **标准环境**：
     ```
     python "<skills_dir>/skill-reviewer/scripts/quick_score.py" --json | Out-File -FilePath "<输出目录>\skill-review.json" -Encoding utf8
     ```
   - **自定义路径**：
     ```
     python "<skills_dir>/skill-reviewer/scripts/quick_score.py" --path "<自定义路径>" --json | Out-File -FilePath "<输出目录>\skill-review.json" -Encoding utf8
     ```
3. 生成 Markdown 报告：
   ```
   python "<skills_dir>/skill-reviewer/scripts/reporter.py" -i "<输出目录>\skill-review.json" -o "<输出目录>\skill-review-report.md"
   ```
4. 创建摘要 artifact，呈现关键发现

### 完整模式

脚本评分 + AI 深度审查。读取 `references/content_review_guide.md` 中的标准，对 Skill 的 SKILL.md 正文进行 11 个维度的内容质量评估。

支持两种范围：
- **全量审查**：审查所有 Skill（优先关注低分 Skill）
- **单 Skill 审查**：用户指定 Skill 名称，仅深度审查该 Skill

步骤：
1. 向用户确认输出目录
2. 运行快速评分获取 JSON 结果：
   ```
   python "<skills_dir>/skill-reviewer/scripts/quick_score.py" [<skill-name>] --json | Out-File -FilePath "<输出目录>\skill-review.json" -Encoding utf8
   ```
3. 生成 Markdown 报告：
   ```
   python "<skills_dir>/skill-reviewer/scripts/reporter.py" -i "<输出目录>\skill-review.json" -o "<输出目录>\skill-review-report.md"
   ```
4. AI 读取 `references/content_review_guide.md`，对目标 Skill 进行深度审查：
   - **全量模式**：优先审查低分（C/D/F 级）Skill
   - **单 Skill 模式**：仅审查用户指定的 Skill
5. AI 补充内容质量评估，输出最终评估报告到用户指定目录
6. **STOP — 等待用户指示**（见下方修复引导）

## 检查模块（6 个）

| 模块 | 规则数 | 核心检查内容 |
|------|--------|-------------|
| structure | 10 | YAML frontmatter、目录结构、描述长度 |
| references | 6 | 文件路径、Python 语法、依赖包 |
| triggers | 6 | 触发关键词、跨 Skill 冲突 |
| design | 7 | 单一职责、I/O 接口、错误处理 |
| security | 8 | 网络调用、文件操作、凭据、数据泄露 |
| crossenv | 4 | 版本一致性、环境特定依赖 |

## 评分体系

- 满分 100，六个维度加权（安全性 25% 最高）
- Blocker 级问题使该维度归零
- 安全 Blocker 使整个 Skill 降至 F 级
- 等级：A(90+) / B(75+) / C(60+) / D(40+) / F(<40)

## 报告生成

```
python "<skills_dir>/skill-reviewer/scripts/reporter.py" -i "<输出目录>\skill-review.json" -o "<输出目录>\report.md"
python "<skills_dir>/skill-reviewer/scripts/reporter.py" -i "<输出目录>\skill-review.json" --skill env-health-check
```

## 修复引导

> **重要**：审查完成后，**必须等待用户明确指示再进行任何修复操作**。
> 禁止在审查报告输出后自动进入修复流程。

当用户明确要求修复时，按风险级别分层引导：
1. **绿色自动修复**：删除备份文件、补充编码声明等无副作用操作 — 列出清单，用户确认后批量执行
2. **黄色批量确认**：按模块分组展示修复方案，用户选择执行/跳过
3. **红色逐项确认**：高风险操作（如修改 description、重构代码）逐一说明影响，逐一获得用户确认

修复前自动备份到 `$env:TEMP\skill-reviewer-cleanup-{timestamp}\`。
