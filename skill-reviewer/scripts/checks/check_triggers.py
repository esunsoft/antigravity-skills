# -*- coding: utf-8 -*-
"""
模块 3：check_triggers — 触发质量检查（6 条规则 T01-T06）

对应原则：P1 单一职责, P2 稳定接口, P3 可选择调用, P6 模型解耦
"""

import re
from collections import defaultdict
from typing import List, Set

from . import (
    SkillInfo, ModuleResult, RuleFinding,
    SEVERITY_MAJOR, SEVERITY_MINOR, SEVERITY_NIT,
)

# 常见的触发词提取正则
TRIGGER_KEYWORD_PATTERNS = [
    r'(?:trigger|触发|use when|when to use|使用场景)[:\s：]+(.+)',
    r'(?:关键词|keywords?)[:\s：]+(.+)',
]

# aggressive 指标词（description 中应包含的主动性词汇）
AGGRESSIVE_WORDS_EN = {'must', 'always', 'whenever', 'make sure', 'use this', 'even if'}
AGGRESSIVE_WORDS_ZH = {'必须', '务必', '一定', '确保', '每当', '只要'}


def _extract_keywords(description: str) -> Set[str]:
    """从 description 中提取关键词（按标点和逗号分割）"""
    # 先尝试提取显式的关键词声明
    keywords = set()
    for pattern in TRIGGER_KEYWORD_PATTERNS:
        for match in re.finditer(pattern, description, re.IGNORECASE):
            words = re.split(r'[,，、;；]', match.group(1))
            keywords.update(w.strip().lower() for w in words if len(w.strip()) > 1)

    # 如果没找到显式声明，提取有意义的词
    if not keywords:
        # 移除常见停用词后提取
        words = re.findall(r'[\w\u4e00-\u9fff]{2,}', description.lower())
        stop_words = {'the', 'this', 'that', 'when', 'with', 'from', 'for', 'and', 'use',
                      'or', 'to', 'is', 'it', 'in', 'of', 'an', 'as', 'by', 'on',
                      '的', '了', '是', '在', '和', '或', '用', '等', '进行', '使用'}
        keywords = {w for w in words if w not in stop_words}

    return keywords


def check(skill: SkillInfo, all_skills: List[SkillInfo]) -> ModuleResult:
    """执行触发质量检查"""
    result = ModuleResult(module="triggers")

    if not skill.fm_description:
        return result  # S01 已经会报缺少 description

    desc = skill.fm_description

    # T01: description 包含触发关键词 [P3]
    keywords = _extract_keywords(desc)
    if len(keywords) < 3:
        result.add(RuleFinding(
            rule_id="T01", severity=SEVERITY_MAJOR, principle="P3",
            title="description 中可识别的触发关键词不足",
            description=f"仅提取到 {len(keywords)} 个关键词，建议至少包含 3 个明确的触发场景词",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="在 description 中添加具体的触发关键词和使用场景",
        ))

    # T02: 触发词与其他同环境 Skill 无冲突 [P3]
    same_env_skills = [s for s in all_skills
                       if s.env == skill.env
                       and s.name != skill.name
                       and not s.is_archived]
    for other in same_env_skills:
        if not other.fm_description:
            continue
        other_keywords = _extract_keywords(other.fm_description)
        overlap = keywords & other_keywords
        # 排除过于泛化的重叠词
        meaningful_overlap = {w for w in overlap if len(w) > 3}
        if len(meaningful_overlap) >= 5:
            result.add(RuleFinding(
                rule_id="T02", severity=SEVERITY_MAJOR, principle="P3",
                title=f"触发词与 '{other.name}' 高度重叠",
                description=f"共有 {len(meaningful_overlap)} 个重叠关键词：{', '.join(list(meaningful_overlap)[:5])}",
                skill_name=skill.name, skill_env=skill.env,
                fix_suggestion=f"分化两个 Skill 的 description，使触发条件更精确",
            ))

    # T03: description 足够 aggressive [P3]
    has_aggressive = any(w in desc.lower() for w in AGGRESSIVE_WORDS_EN)
    has_aggressive_zh = any(w in desc for w in AGGRESSIVE_WORDS_ZH)
    if not has_aggressive and not has_aggressive_zh:
        result.add(RuleFinding(
            rule_id="T03", severity=SEVERITY_MINOR, principle="P3",
            title="description 缺少主动触发词",
            description="根据 skill-creator 建议，description 应偏主动，包含 'Use when'、'Make sure to use' 等词",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="添加类似 'Use when...' 或 'Make sure to use this skill whenever...' 的主动触发描述",
        ))

    # T04: 中英文触发词覆盖 [P3, P6]
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', desc))
    has_english = bool(re.search(r'[a-zA-Z]{3,}', desc))
    if not (has_chinese and has_english):
        missing = "中文" if not has_chinese else "英文"
        result.add(RuleFinding(
            rule_id="T04", severity=SEVERITY_MINOR, principle="P3, P6",
            title=f"description 缺少{missing}触发词",
            description="中英混用环境中，建议 description 同时包含中英文关键词以提高触发率",
            skill_name=skill.name, skill_env=skill.env,
        ))

    # T05: 归档 Skill 不应有活跃触发词冲突 [P3, P1]
    if not skill.is_archived:
        archived_skills = [s for s in all_skills if s.is_archived and s.env == skill.env]
        for archived in archived_skills:
            if not archived.fm_description:
                continue
            arch_keywords = _extract_keywords(archived.fm_description)
            overlap = keywords & arch_keywords
            meaningful = {w for w in overlap if len(w) > 3}
            if len(meaningful) >= 5:
                result.add(RuleFinding(
                    rule_id="T05", severity=SEVERITY_MAJOR, principle="P3, P1",
                    title=f"与归档 Skill '{archived.name}' 触发词冲突",
                    description=f"归档的 '{archived.name}' 仍有大量重叠触发词，可能干扰本 Skill 的触发",
                    skill_name=skill.name, skill_env=skill.env,
                    fix_suggestion=f"清理归档 Skill '{archived.name}' 的 description，或差异化本 Skill 的触发词",
                ))

    # T06: description 无无效转义/特殊字符 [P2]
    problematic_chars = re.findall(r'[\\`\x00-\x08\x0b\x0c\x0e-\x1f]', desc)
    if problematic_chars:
        result.add(RuleFinding(
            rule_id="T06", severity=SEVERITY_NIT, principle="P2",
            title="description 包含可能影响 YAML 解析的特殊字符",
            description=f"发现 {len(problematic_chars)} 个特殊字符，可能导致不同 YAML 解析器行为不一致",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="移除或转义 description 中的特殊字符",
        ))

    return result
