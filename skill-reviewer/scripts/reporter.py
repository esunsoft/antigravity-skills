# -*- coding: utf-8 -*-
"""
skill-reviewer 报告生成器

从 JSON 审查结果生成 Markdown 格式的完整报告。
支持全量报告和单 Skill 体检卡两种模式。
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from checks import score_to_grade, SEVERITY_BLOCKER, SEVERITY_MAJOR, SEVERITY_MINOR, SEVERITY_NIT


def generate_report(data: dict) -> str:
    """生成 Markdown 格式的完整报告"""
    reviews = data.get("reviews", [])
    crossenv = data.get("crossenv", {})
    summary = data.get("summary", {})

    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"# Skill Review Report")
    lines.append(f"")
    lines.append(f"Generated: {now}")
    lines.append(f"")

    # 摘要
    total = summary.get("total_skills", len(reviews))
    avg = summary.get("avg_score", 0)
    blockers = summary.get("blocker_count", 0)
    letter, emoji = score_to_grade(avg)
    lines.append(f"## Summary")
    lines.append(f"")
    lines.append(f"- **Total Skills**: {total}")
    lines.append(f"- **Ecosystem Score**: {avg} {emoji} {letter}")
    lines.append(f"- **Blockers**: {blockers}")
    lines.append(f"")

    # 按等级分组
    grade_groups: Dict[str, list] = {"A": [], "B": [], "C": [], "D": [], "F": []}
    for r in reviews:
        grade = r.get("grade", "F")
        grade_groups.setdefault(grade, []).append(r)

    lines.append(f"### Grade Distribution")
    lines.append(f"")
    for grade in ["A", "B", "C", "D", "F"]:
        count = len(grade_groups.get(grade, []))
        if count:
            lines.append(f"- **{grade}**: {count} skills")
    lines.append(f"")

    # 按严重级分组的 Findings
    all_findings = []
    for r in reviews:
        skill_name = r.get("skill", {}).get("name", "?")
        for mod_name, mod_data in r.get("modules", {}).items():
            for f in mod_data.get("findings", []):
                f["_skill"] = skill_name
                all_findings.append(f)

    for severity in [SEVERITY_BLOCKER, SEVERITY_MAJOR, SEVERITY_MINOR, SEVERITY_NIT]:
        sev_findings = [f for f in all_findings if f.get("severity") == severity]
        if not sev_findings:
            continue
        lines.append(f"## {severity} ({len(sev_findings)})")
        lines.append(f"")
        for f in sev_findings:
            rule_id = f.get("rule_id", "?")
            title = f.get("title", "?")
            skill = f.get("_skill", "?")
            desc = f.get("description", "")
            fix = f.get("fix_suggestion", "")
            lines.append(f"### [{rule_id}] {title}")
            lines.append(f"")
            lines.append(f"**Skill**: {skill} | **Principle**: {f.get('principle', '?')}")
            lines.append(f"")
            if desc:
                lines.append(f"{desc}")
                lines.append(f"")
            if fix:
                lines.append(f"> **Fix**: {fix}")
                lines.append(f"")

    # 跨环境问题
    xenv_findings = crossenv.get("findings", [])
    if xenv_findings:
        lines.append(f"## Cross-Environment Issues ({len(xenv_findings)})")
        lines.append(f"")
        for f in xenv_findings:
            lines.append(f"- **[{f.get('rule_id')}]** {f.get('title')}")
        lines.append(f"")

    return "\n".join(lines)


def generate_skill_card(review: dict) -> str:
    """生成单 Skill 的详细体检卡"""
    skill = review.get("skill", {})
    lines = []
    lines.append(f"# Skill Review Card: {skill.get('name', '?')}")
    lines.append(f"")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| Environment | {skill.get('env', '?')} |")
    lines.append(f"| SKILL.md Lines | {skill.get('skill_md_lines', 0)} |")
    lines.append(f"| Files | {skill.get('file_count', 0)} |")
    lines.append(f"| Python Files | {skill.get('py_file_count', 0)} |")
    lines.append(f"| Total Score | **{review.get('total_score', 0)}** {review.get('grade', '?')} |")
    lines.append(f"")

    # 各维度得分
    lines.append(f"## Dimension Scores")
    lines.append(f"")
    lines.append(f"| Dimension | Score | Findings |")
    lines.append(f"|-----------|-------|----------|")
    for mod_name, mod_data in review.get("modules", {}).items():
        score = mod_data.get("dimension_score", 100)
        count = mod_data.get("finding_count", 0)
        letter, emoji = score_to_grade(score)
        lines.append(f"| {mod_name} | {score} {emoji} | {count} |")
    lines.append(f"")

    # 详细 Findings
    lines.append(f"## Findings Detail")
    lines.append(f"")
    for mod_name, mod_data in review.get("modules", {}).items():
        findings = mod_data.get("findings", [])
        if not findings:
            continue
        lines.append(f"### {mod_name}")
        lines.append(f"")
        for f in findings:
            sev = f.get("severity", "?")
            lines.append(f"- **[{sev}] {f.get('rule_id', '?')}**: {f.get('title', '?')}")
            if f.get("fix_suggestion"):
                lines.append(f"  - Fix: {f['fix_suggestion']}")
        lines.append(f"")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Skill Reviewer — 报告生成器")
    parser.add_argument("-i", "--input", required=True, help="JSON 审查结果文件路径")
    parser.add_argument("-o", "--output", help="输出 Markdown 文件路径")
    parser.add_argument("--skill", help="仅输出指定 Skill 的体检卡")
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)

    if args.skill:
        # 单 Skill 体检卡模式
        for r in data.get("reviews", []):
            if r.get("skill", {}).get("name") == args.skill:
                report = generate_skill_card(r)
                break
        else:
            print(f"未找到 Skill：{args.skill}")
            sys.exit(1)
    else:
        report = generate_report(data)

    if args.output:
        Path(args.output).write_text(report, encoding='utf-8')
        print(f"报告已输出到：{args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
