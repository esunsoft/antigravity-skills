# Skill Reviewer 使用示例

## 1. 审查标准环境下的所有 Skills

```bash
# Antigravity 环境
python scripts/quick_score.py --env antigravity --json > output/antigravity-review.json
python scripts/reporter.py -i output/antigravity-review.json -o output/antigravity-report.md

# Claude Code 环境
python scripts/quick_score.py --env claude --json > output/claude-review.json
python scripts/reporter.py -i output/claude-review.json -o output/claude-report.md

# 所有环境
python scripts/quick_score.py --json > output/all-review.json
python scripts/reporter.py -i output/all-review.json -o output/all-report.md
```

## 2. 审查标准环境下的单个 Skill

```bash
# 按目录名审查
python scripts/quick_score.py skill-reviewer --json > output/skill-reviewer.json
python scripts/reporter.py -i output/skill-reviewer.json -o output/skill-reviewer-report.md

# 按 frontmatter name 审查
python scripts/quick_score.py sqlserver-perf-audit --json > output/perf-audit.json
```

## 3. 审查自定义路径下的单个 Skill

```bash
# 指定单个 Skill 目录
python scripts/quick_score.py --path /d/my-project/.claude/skills/my-skill --json > output/my-skill.json
python scripts/reporter.py -i output/my-skill.json -o output/my-skill-report.md

# Windows 路径示例
python scripts/quick_score.py --path "D:\AI-workspace\sql\.claude\skills\sqlserver-perf-audit" --json > output/perf-audit.json
```

## 4. 审查自定义路径下的多个 Skills

```bash
# 指定包含多个 Skills 的父目录
python scripts/quick_score.py --path /d/my-project/.claude/skills --json > output/project-review.json
python scripts/reporter.py -i output/project-review.json -o output/project-report.md

# 审查项目级 Skills 目录
python scripts/quick_score.py --path "D:\AI-workspace\sql\.claude\skills" --json > output/sql-skills.json
```

## 5. 生成单个 Skill 的详细报告

```bash
# 从完整审查结果中提取单个 Skill 报告
python scripts/reporter.py -i output/all-review.json --skill skill-reviewer

# 输出到文件
python scripts/reporter.py -i output/all-review.json --skill skill-reviewer -o output/skill-reviewer-detail.md
```

## 6. 完整工作流示例

### 场景 A：审查项目级 Skills

```bash
# 1. 审查项目下所有 Skills
cd /c/Users/esun/.claude/skills/skill-reviewer
python scripts/quick_score.py --path /d/my-project/.claude/skills --json > /d/reports/project-skills.json

# 2. 生成汇总报告
python scripts/reporter.py -i /d/reports/project-skills.json -o /d/reports/project-skills-report.md

# 3. 查看低分 Skills
cat /d/reports/project-skills.json | jq '.reviews[] | select(.grade == "C" or .grade == "D" or .grade == "F") | {name: .skill.name, score: .total_score, grade: .grade}'

# 4. 针对低分 Skill 生成详细报告
python scripts/reporter.py -i /d/reports/project-skills.json --skill my-low-score-skill -o /d/reports/my-low-score-skill-detail.md
```

### 场景 B：持续集成检查

```bash
# CI 脚本示例
#!/bin/bash
set -e

SKILLS_DIR="/d/my-project/.claude/skills"
OUTPUT_DIR="/d/ci-reports"
THRESHOLD=75

# 运行审查
python scripts/quick_score.py --path "$SKILLS_DIR" --json > "$OUTPUT_DIR/review.json"

# 检查平均分
AVG_SCORE=$(cat "$OUTPUT_DIR/review.json" | jq '.summary.avg_score')
if [ "$AVG_SCORE" -lt "$THRESHOLD" ]; then
    echo "❌ Skills 平均分 $AVG_SCORE 低于阈值 $THRESHOLD"
    python scripts/reporter.py -i "$OUTPUT_DIR/review.json" -o "$OUTPUT_DIR/report.md"
    exit 1
fi

# 检查 Blocker 问题
BLOCKER_COUNT=$(cat "$OUTPUT_DIR/review.json" | jq '.summary.blocker_count')
if [ "$BLOCKER_COUNT" -gt 0 ]; then
    echo "❌ 发现 $BLOCKER_COUNT 个 Blocker 级问题"
    python scripts/reporter.py -i "$OUTPUT_DIR/review.json" -o "$OUTPUT_DIR/report.md"
    exit 1
fi

echo "✓ Skills 质量检查通过"
```

### 场景 C：开发时快速检查

```bash
# 开发完成后快速检查单个 Skill
python scripts/quick_score.py --path ./my-new-skill --json | jq '{name: .reviews[0].skill.name, score: .reviews[0].total_score, grade: .reviews[0].grade, blocker_count: (.reviews[0].modules | to_entries | map(.value.blocker_count) | add)}'

# 输出示例：
# {
#   "name": "my-new-skill",
#   "score": 85,
#   "grade": "B",
#   "blocker_count": 0
# }
```

## 7. 常见问题排查

### 问题：找不到 Skill

```bash
# 确认路径是否正确
ls -la /d/my-project/.claude/skills/my-skill/SKILL.md

# 确认是否在正确的环境
python scripts/scanner.py --env antigravity --json | jq '.[] | .name'
```

### 问题：依赖包缺失

```bash
# 检查 Python 环境
python --version
python -c "import yaml; print('PyYAML OK')"

# 安装依赖
pip install pyyaml
```

### 问题：编码错误

```bash
# 确保使用 UTF-8 编码
export PYTHONIOENCODING=utf-8

# Windows PowerShell
$env:PYTHONIOENCODING="utf-8"
```

## 8. 高级用法

### 过滤特定问题

```bash
# 查找所有安全问题
cat output/review.json | jq '.reviews[].modules.security.findings[] | select(.severity == "Major" or .severity == "Blocker")'

# 查找所有引用问题
cat output/review.json | jq '.reviews[].modules.references.findings[]'

# 统计问题分布
cat output/review.json | jq '[.reviews[].modules | to_entries[] | .value.findings[] | .severity] | group_by(.) | map({severity: .[0], count: length})'
```

### 批量修复建议

```bash
# 提取所有可自动修复的问题
cat output/review.json | jq '.reviews[].modules | to_entries[] | .value.findings[] | select(.auto_fixable == true) | {skill: .skill_name, rule: .rule_id, fix: .fix_command}'

# 生成修复脚本
cat output/review.json | jq -r '.reviews[].modules | to_entries[] | .value.findings[] | select(.fix_command != null) | .fix_command' > fix-commands.sh
```

## 9. 输出格式说明

### JSON 输出结构

```json
{
  "reviews": [
    {
      "skill": {
        "name": "skill-name",
        "path": "/path/to/skill",
        "env": "custom",
        "fm_name": "skill-name",
        "fm_description": "...",
        "skill_md_lines": 345,
        "file_count": 43,
        "py_file_count": 10
      },
      "total_score": 72,
      "grade": "C",
      "modules": {
        "structure": { "dimension_score": 100, "findings": [] },
        "references": { "dimension_score": 60, "findings": [...] },
        "triggers": { "dimension_score": 90, "findings": [...] },
        "design": { "dimension_score": 80, "findings": [...] },
        "security": { "dimension_score": 32, "findings": [...] },
        "content": { "dimension_score": 100, "findings": [] }
      }
    }
  ],
  "crossenv": {
    "module": "crossenv",
    "dimension_score": 100,
    "findings": []
  },
  "summary": {
    "total_skills": 1,
    "avg_score": 72,
    "blocker_count": 0
  }
}
```

### Markdown 报告结构

```markdown
# Skill Review Report

## Summary
- Total Skills: 1
- Ecosystem Score: 72 ⚠️ C
- Blockers: 0

## Major (6)
### [R01] 引用的文件不存在
...

## Minor (2)
### [T03] description 缺少主动触发词
...

## Nit (1)
### [T06] description 包含特殊字符
...
```
