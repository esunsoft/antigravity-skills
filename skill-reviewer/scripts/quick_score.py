# -*- coding: utf-8 -*-
"""
skill-reviewer 快速评分入口

调用 scanner + 6 个 check 模块，计算加权评分，输出终端表格。
支持 --json 和 --env 参数。内容质量维度使用启发式估算。
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))

from checks import (
    SkillInfo, SkillReviewResult, ModuleResult, RuleFinding,
    DIMENSION_WEIGHTS, score_to_grade,
    SEVERITY_MINOR, SEVERITY_NIT,
    count_pattern_density,
)
from checks.check_structure import check as check_structure
from checks.check_references import check as check_references
from checks.check_triggers import check as check_triggers
from checks.check_design import check as check_design
from checks.check_security import check as check_security
from checks.check_crossenv import check_ecosystem
from scanner import scan_all


def _content_heuristic(skill: SkillInfo) -> ModuleResult:
    """内容质量启发式估算（不调用 AI）"""
    result = ModuleResult(module="content")
    content = skill.skill_md_content
    if not content:
        return result

    # MUST/ALWAYS/NEVER 密度
    density = count_pattern_density(content, [r'\bMUST\b', r'\bALWAYS\b', r'\bNEVER\b'])
    if density > 5.0:
        result.add(RuleFinding(
            rule_id="CH01", severity=SEVERITY_MINOR, principle="P6",
            title=f"MUST/ALWAYS/NEVER 密度过高（{density:.1f}/千字符）",
            description="过多的强制性指令是反模式信号",
            skill_name=skill.name, skill_env=skill.env,
        ))

    # 代码块与解释的比例
    code_blocks = content.count('```')
    total_lines = skill.skill_md_lines
    if total_lines > 20 and code_blocks > 0:
        # 粗略估计代码行占比
        code_line_ratio = (code_blocks * 10) / total_lines  # 假设每个代码块约 10 行
        if code_line_ratio > 0.7:
            result.add(RuleFinding(
                rule_id="CH02", severity=SEVERITY_NIT, principle="P2",
                title="代码块占比过高",
                description="SKILL.md 中代码块过多，缺少足够的文字解释",
                skill_name=skill.name, skill_env=skill.env,
            ))

    # 章节标题覆盖度
    important_sections = ['输入', '输出', 'input', 'output', '错误', 'error',
                          '使用', 'usage', '安全', 'safety']
    found = sum(1 for s in important_sections if s in content.lower())
    if skill.py_files and found < 2:
        result.add(RuleFinding(
            rule_id="CH03", severity=SEVERITY_MINOR, principle="P2, P5",
            title="缺少关键章节",
            description="SKILL.md 缺少输入/输出/错误处理等重要章节",
            skill_name=skill.name, skill_env=skill.env,
        ))

    # description 与正文关键词重叠度
    if skill.fm_description:
        desc_words = set(skill.fm_description.lower().split())
        body_words = set(content.lower().split())
        if desc_words:
            overlap = len(desc_words & body_words) / len(desc_words)
            if overlap < 0.3:
                result.add(RuleFinding(
                    rule_id="CH04", severity=SEVERITY_MINOR, principle="P3",
                    title="description 与正文关键词重叠度低",
                    description=f"仅 {int(overlap*100)}% 的 description 词出现在正文中",
                    skill_name=skill.name, skill_env=skill.env,
                ))

    return result


def review_skill(skill: SkillInfo, all_skills: List[SkillInfo]) -> SkillReviewResult:
    """对单个 Skill 执行全部检查"""
    review = SkillReviewResult(skill=skill)
    review.modules["structure"] = check_structure(skill, all_skills)
    review.modules["references"] = check_references(skill, all_skills)
    review.modules["triggers"] = check_triggers(skill, all_skills)
    review.modules["design"] = check_design(skill, all_skills)
    review.modules["security"] = check_security(skill, all_skills)
    review.modules["content"] = _content_heuristic(skill)
    return review


def print_table(reviews: List[SkillReviewResult], env_name: str):
    """输出终端评分表格"""
    print(f"\n{'='*90}")
    print(f" Skill Review — {env_name} ({len(reviews)} skills)")
    print(f"{'='*90}")
    header = f"{'Skill':<30} {'Str':>4} {'Ref':>4} {'Trg':>4} {'Dsg':>4} {'Sec':>4} {'Cnt':>4} {'Total':>6} {'Grade':>6}"
    print(header)
    print(f"{'-'*90}")

    for r in sorted(reviews, key=lambda x: x.total_score):
        name = r.skill.name[:28]
        str_s = r.modules.get("structure", ModuleResult("")).dimension_score
        ref_s = r.modules.get("references", ModuleResult("")).dimension_score
        trg_s = r.modules.get("triggers", ModuleResult("")).dimension_score
        dsg_s = r.modules.get("design", ModuleResult("")).dimension_score
        sec_s = r.modules.get("security", ModuleResult("")).dimension_score
        cnt_s = r.modules.get("content", ModuleResult("")).dimension_score
        letter, emoji = r.grade
        print(f"  {name:<28} {str_s:>4} {ref_s:>4} {trg_s:>4} {dsg_s:>4} {sec_s:>4} {cnt_s:>4} {r.total_score:>5} {emoji} {letter}")

    # 生态评分
    if reviews:
        avg = sum(r.total_score for r in reviews) / len(reviews)
        letter, emoji = score_to_grade(int(avg))
        print(f"{'-'*90}")
        print(f"  {'Ecosystem Average':<28} {'':>4} {'':>4} {'':>4} {'':>4} {'':>4} {'':>4} {int(avg):>5} {emoji} {letter}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Skill Reviewer — 快速评分")
    parser.add_argument("--env", choices=["antigravity", "claude"],
                        help="仅审查指定环境")
    parser.add_argument("--path", type=str, help="自定义 Skill 路径（单个 Skill 或包含多个 Skills 的目录）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--active-only", action="store_true", default=True,
                        help="仅审查活跃 Skill（默认）")
    parser.add_argument("skill_name", nargs="?", help="审查指定 Skill")
    args = parser.parse_args()

    envs = [args.env] if args.env else None
    all_skills = scan_all(envs, custom_path=args.path)

    if args.active_only:
        active_skills = [s for s in all_skills if not s.is_archived]
    else:
        active_skills = all_skills

    # 单 Skill 模式
    if args.skill_name:
        matches = [s for s in all_skills if s.name == args.skill_name or s.fm_name == args.skill_name]
        if not matches:
            print(f"未找到 Skill：{args.skill_name}")
            sys.exit(1)
        active_skills = matches

    # 执行审查
    reviews = [review_skill(s, all_skills) for s in active_skills]

    # 跨环境检查
    crossenv_result = check_ecosystem(all_skills)

    if args.json:
        output = {
            "reviews": [r.to_dict() for r in reviews],
            "crossenv": crossenv_result.to_dict(),
            "summary": {
                "total_skills": len(reviews),
                "avg_score": int(sum(r.total_score for r in reviews) / max(len(reviews), 1)),
                "blocker_count": sum(sum(m.blocker_count for m in r.modules.values()) for r in reviews),
            }
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # 按环境分组输出
        for env_name in ["antigravity", "claude"]:
            env_reviews = [r for r in reviews if r.skill.env == env_name]
            if env_reviews:
                print_table(env_reviews, env_name)

        # 跨环境问题
        if crossenv_result.findings:
            print(f"\n{'='*90}")
            print(f" Cross-Environment Issues ({len(crossenv_result.findings)} findings)")
            print(f"{'='*90}")
            for f in crossenv_result.findings:
                print(f"  [{f.severity}] {f.rule_id}: {f.title}")


if __name__ == "__main__":
    main()
