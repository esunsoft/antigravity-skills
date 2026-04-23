# Skill 模板

从 learning 中提取 Skill 时使用的模板。复制并自定义。

---

## SKILL.md 标准模板

```markdown
---
name: skill-name-here
description: "简洁描述此 Skill 的用途和触发条件。"
---

# Skill Name

简述此 Skill 解决的问题及其来源。

## Quick Reference

| 情景 | 操作 |
|------|------|
| [触发条件 1] | [操作 1] |
| [触发条件 2] | [操作 2] |

## Background

为什么这个知识重要、能预防什么问题、原始 learning 的上下文。

## Solution

### 步骤

1. 第一步（含代码或命令）
2. 第二步
3. 验证步骤

### 代码示例

\`\`\`python
# 示例代码
\`\`\`

## 常见变体

- **变体 A**: 描述及处理方式
- **变体 B**: 描述及处理方式

## 注意事项

- 警告或常见错误 #1
- 警告或常见错误 #2

## Source

从 learning 条目提取。
- **Learning ID**: LRN-YYYYMMDD-XXX
- **原始类别**: correction | insight | knowledge_gap | best_practice
- **提取日期**: YYYY-MM-DD
```

---

## 精简模板

适用于不需要所有章节的简单 Skill：

```markdown
---
name: skill-name-here
description: "此 Skill 的用途和触发条件。"
---

# Skill Name

[一句话问题陈述]

## Solution

[直接给出解决方案和代码/命令]

## Source

- Learning ID: LRN-YYYYMMDD-XXX
```

---

## 带脚本的模板

适用于包含可执行辅助工具的 Skill：

```markdown
---
name: skill-name-here
description: "此 Skill 的用途和触发条件。"
---

# Skill Name

[简介]

## Quick Reference

| 命令 | 用途 |
|------|------|
| `python scripts/helper.py` | [功能描述] |
| `python scripts/validate.py` | [功能描述] |

## Usage

### 自动化（推荐）

\`\`\`powershell
python "<skill_path>\scripts\helper.py" [参数]
\`\`\`

### 手动步骤

1. 步骤一
2. 步骤二

## Source

- Learning ID: LRN-YYYYMMDD-XXX
```

---

## 命名规范

- **Skill 名称**: 小写字母，连字符分隔
  - ✅ `docker-m1-fixes`、`api-timeout-patterns`
  - ❌ `Docker_M1_Fixes`、`APITimeoutPatterns`

- **描述**: 以动词开头，提及触发条件
  - ✅ "修复 Docker 在 Apple Silicon 上的构建失败。当构建出现平台不匹配错误时使用。"
  - ❌ "Docker 相关"

- **文件结构**:
  - `SKILL.md` — 必需，主文档
  - `scripts/` — 可选，Python 脚本
  - `references/` — 可选，详细文档
  - `assets/` — 可选，模板

---

## 提取检查清单

提取前验证：

- [ ] 解决方案已验证（status: resolved）
- [ ] 广泛适用（非一次性问题）
- [ ] 内容完整（包含所有必要上下文）
- [ ] 名称符合规范
- [ ] 描述简洁但信息充分
- [ ] Quick Reference 表可操作
- [ ] 代码示例已测试
- [ ] 源 Learning ID 已记录

提取后：

- [ ] 更新原始 learning 的 status 为 `promoted_to_skill`
- [ ] 在 learning metadata 中添加 `Skill-Path`
- [ ] 在新会话中读取 Skill 确认它自包含
