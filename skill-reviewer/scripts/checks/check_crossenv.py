# -*- coding: utf-8 -*-
"""
模块 6：check_crossenv — 跨环境分析（4 条规则 X01-X04）

对应原则：P1 单一职责, P3 可选择调用, P6 模型解耦, P7 可演进
"""

import difflib
from typing import List, Dict, Set

from . import (
    SkillInfo, ModuleResult, RuleFinding,
    SEVERITY_MAJOR, SEVERITY_MINOR,
    ENV_ANTIGRAVITY, ENV_CLAUDE,
)


def _group_by_env(skills: List[SkillInfo]) -> Dict[str, List[SkillInfo]]:
    """按环境分组"""
    groups = {}
    for s in skills:
        groups.setdefault(s.env, []).append(s)
    return groups


def check_ecosystem(all_skills: List[SkillInfo]) -> ModuleResult:
    """执行跨环境分析（生态级检查，不针对单个 Skill）"""
    result = ModuleResult(module="crossenv")
    env_groups = _group_by_env(all_skills)

    if len(env_groups) < 2:
        return result  # 只有一个环境，无需跨环境检查

    ag_skills = {s.name: s for s in env_groups.get(ENV_ANTIGRAVITY, []) if not s.is_archived}
    cc_skills = {s.name: s for s in env_groups.get(ENV_CLAUDE, []) if not s.is_archived}

    # X01: 同名 Skill 跨环境版本一致性 [P7]
    common_names = set(ag_skills.keys()) & set(cc_skills.keys())
    for name in sorted(common_names):
        ag = ag_skills[name]
        cc = cc_skills[name]
        # 比较 SKILL.md 内容相似度
        if ag.skill_md_content and cc.skill_md_content:
            ratio = difflib.SequenceMatcher(
                None, ag.skill_md_content, cc.skill_md_content
            ).ratio()
            if ratio < 0.95:  # 相似度低于 95% 视为不一致
                diff_pct = int((1 - ratio) * 100)
                result.add(RuleFinding(
                    rule_id="X01", severity=SEVERITY_MAJOR, principle="P7",
                    title=f"跨环境版本不一致：'{name}'（差异 {diff_pct}%）",
                    description=f"'{name}' 在 Antigravity 和 Claude Code 中内容差异 {diff_pct}%",
                    skill_name=name,
                    fix_suggestion="同步两个环境中的 Skill 内容",
                ))

    # X02: 跨环境触发词冲突 [P3]
    # 不同名但 description 高度相似的 Skill
    for ag_name, ag_skill in ag_skills.items():
        for cc_name, cc_skill in cc_skills.items():
            if ag_name == cc_name:
                continue
            if not ag_skill.fm_description or not cc_skill.fm_description:
                continue
            desc_ratio = difflib.SequenceMatcher(
                None, ag_skill.fm_description.lower(), cc_skill.fm_description.lower()
            ).ratio()
            if desc_ratio > 0.7:
                result.add(RuleFinding(
                    rule_id="X02", severity=SEVERITY_MAJOR, principle="P3",
                    title=f"跨环境触发词冲突：'{ag_name}' vs '{cc_name}'",
                    description=f"Antigravity 的 '{ag_name}' 和 Claude 的 '{cc_name}' "
                                f"description 相似度 {int(desc_ratio*100)}%",
                    fix_suggestion="差异化两个 Skill 的 description，或合并为同名 Skill",
                ))

    # X03: 跨环境功能重复 [P1]
    # 检查是否有大量同名 Skill（本身就是功能重复的信号）
    if len(common_names) > 10:
        result.add(RuleFinding(
            rule_id="X03", severity=SEVERITY_MINOR, principle="P1",
            title=f"跨环境重复 Skill 较多：{len(common_names)} 个",
            description=f"两个环境共享 {len(common_names)} 个同名 Skill，建议评估是否需要同步维护",
            fix_suggestion="考虑使用符号链接或统一管理方案减少维护负担",
        ))

    # X04: 环境特定依赖检查 [P6]
    # 检查 Claude Code 特有的工具引用
    claude_only_tools = ['present_files', 'Task', 'TodoWrite', 'TodoRead']
    ag_only_tools = ['browser_subagent', 'generate_image']
    for name, skill in ag_skills.items():
        for tool in claude_only_tools:
            if tool in skill.skill_md_content:
                result.add(RuleFinding(
                    rule_id="X04", severity=SEVERITY_MINOR, principle="P6",
                    title=f"Antigravity Skill 引用了 Claude Code 工具：'{name}'",
                    description=f"'{name}' 中引用了 Claude Code 特有的 '{tool}' 工具",
                    skill_name=name, skill_env=ENV_ANTIGRAVITY,
                    fix_suggestion=f"移除或条件化 '{tool}' 引用",
                ))
                break
    for name, skill in cc_skills.items():
        for tool in ag_only_tools:
            if tool in skill.skill_md_content:
                result.add(RuleFinding(
                    rule_id="X04", severity=SEVERITY_MINOR, principle="P6",
                    title=f"Claude Code Skill 引用了 Antigravity 工具：'{name}'",
                    description=f"'{name}' 中引用了 Antigravity 特有的 '{tool}' 工具",
                    skill_name=name, skill_env=ENV_CLAUDE,
                    fix_suggestion=f"移除或条件化 '{tool}' 引用",
                ))
                break

    return result
