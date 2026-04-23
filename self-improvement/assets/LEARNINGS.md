# Learnings

修正、洞察和知识空白记录。

**类别**: correction | insight | knowledge_gap | best_practice
**区域**: frontend | backend | infra | tests | docs | config
**状态**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill

## 状态定义

| 状态 | 含义 |
|------|------|
| `pending` | 尚未处理 |
| `in_progress` | 正在处理中 |
| `resolved` | 问题已修复或知识已整合 |
| `wont_fix` | 决定不处理（在 Resolution 中说明原因） |
| `promoted` | 已提升为 Knowledge Item (KI) 或用户全局规则 |
| `promoted_to_skill` | 已提取为可复用的 Skill |

## Skill 提取字段

当 learning 被提升为 Skill 时，添加以下字段：

```markdown
**Status**: promoted_to_skill
**Skill-Path**: .agents/skills/skill-name
```

---
