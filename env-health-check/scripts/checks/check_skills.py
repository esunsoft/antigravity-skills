# -*- coding: utf-8 -*-
"""
check_skills.py — Skills 健康检查模块
检查规则: SKL-001 ~ SKL-007
"""

import re
from pathlib import Path
from collections import Counter
from . import (
    Finding, ModuleResult, ModuleStats, Environment,
    SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO,
    RISK_RED, RISK_YELLOW, RISK_GREEN,
    estimate_tokens, get_file_size_kb, read_text_safe,
    find_antigravity_dir,
)

# 阈值常量
MAX_SKILL_COUNT = 50
MAX_SKILL_SIZE_KB = 20.0
MAX_DESC_LENGTH = 200


def run(env: Environment) -> ModuleResult:
    """执行 Skills 健康检查"""
    result = ModuleResult(module="skills")
    skills_dir = env.skills_dir

    if not skills_dir or not skills_dir.exists():
        return result

    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    skill_data = []
    total_size = 0

    for sd in skill_dirs:
        skill_md = sd / "SKILL.md"
        if skill_md.exists():
            size_kb = get_file_size_kb(skill_md)
            content = read_text_safe(skill_md)
            total_size += skill_md.stat().st_size
            skill_data.append({
                "name": sd.name,
                "size_kb": size_kb,
                "content": content,
                "path": sd,
                "skill_md": skill_md,
            })

    result.stats = ModuleStats(
        total_size_kb=round(total_size / 1024, 1),
        estimated_tokens=estimate_tokens(total_size),
        file_count=len(skill_data),
    )

    # SKL-001: 数量过多
    _check_count(result, len(skill_data))

    # SKL-002: 单个过大
    _check_oversized(result, skill_data)

    # SKL-003: 触发词重叠
    _check_trigger_overlap(result, skill_data)

    # SKL-004: 孤立 Skill 检测
    _check_orphan_skills(result, skill_data)

    # SKL-005: 环境冲突语法
    _check_env_conflicts(result, skill_data)

    # SKL-006: 描述过长
    _check_desc_length(result, skill_data)

    # SKL-007: 大小排行
    _check_size_ranking(result, skill_data)

    return result


def _check_count(result: ModuleResult, count: int):
    """SKL-001: Skill 总数检查"""
    if count > MAX_SKILL_COUNT:
        # 估算描述列表的 token 消耗（每个 Skill 在 system prompt 中约占 80-150 tokens 的描述）
        desc_tokens = count * 120  # 平均值
        result.add(Finding(
            id="SKL-001",
            severity=SEVERITY_HIGH,
            risk_level=RISK_RED,
            title=f"Skills 总数过多 ({count} 个，阈值 {MAX_SKILL_COUNT})",
            description=(
                f"当前有 {count} 个 Skill，每个 Skill 的名称+描述会注入到 system prompt 的 skills 列表中，"
                f"预估描述列表消耗约 {desc_tokens} tokens。"
                "建议归档不常用的 Skill，或将功能相近的 Skill 合并。"
            ),
            impact_tokens=desc_tokens,
            fix_suggestion="审查每个 Skill 的使用频率，将不常用的 Skill 移至归档目录。",
        ))


def _check_oversized(result: ModuleResult, skill_data: list):
    """SKL-002: 单个 SKILL.md 过大"""
    oversized = [s for s in skill_data if s["size_kb"] > MAX_SKILL_SIZE_KB]
    for s in oversized:
        tokens = estimate_tokens(s["skill_md"].stat().st_size)
        result.add(Finding(
            id="SKL-002",
            severity=SEVERITY_HIGH,
            risk_level=RISK_RED,
            title=f"Skill '{s['name']}' 的 SKILL.md 过大 ({s['size_kb']}KB)",
            description=(
                f"SKILL.md 达 {s['size_kb']}KB (~{tokens} tokens)，超过 {MAX_SKILL_SIZE_KB}KB 阈值。"
                "过大的 SKILL.md 在被触发时会消耗大量上下文窗口。"
                "建议将详细的参考资料、示例代码拆分到独立文件中，SKILL.md 仅保留核心指令。"
            ),
            impact_tokens=tokens,
            fix_suggestion=f"精简 {s['name']}/SKILL.md，将参考资料拆分到子文件。",
        ))


def _extract_triggers(content: str) -> list:
    """从 SKILL.md 中提取触发关键词"""
    triggers = []
    # 匹配 description 字段
    desc_match = re.search(r'description:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
    if desc_match:
        desc = desc_match.group(1)
        # 提取引号内的关键词
        triggers.extend(re.findall(r'["\']([^"\']+)["\']', desc))
        # 提取逗号分隔的词
        triggers.extend(w.strip() for w in desc.split(',') if len(w.strip()) > 2)

    # 匹配"触发关键词"行
    trigger_match = re.search(r'触发关键词[：:]\s*(.+)', content)
    if trigger_match:
        triggers.extend(
            w.strip() for w in re.split(r'[,，、]', trigger_match.group(1))
            if len(w.strip()) > 1
        )

    return list(set(triggers))


def _check_trigger_overlap(result: ModuleResult, skill_data: list):
    """SKL-003: 触发词重叠检测"""
    # 收集每个 Skill 的触发词
    skill_triggers = {}
    for s in skill_data:
        triggers = _extract_triggers(s["content"])
        if triggers:
            skill_triggers[s["name"]] = triggers

    # 检查重叠
    all_triggers = Counter()
    trigger_to_skills = {}
    for name, triggers in skill_triggers.items():
        for t in triggers:
            t_lower = t.lower().strip()
            if len(t_lower) < 3:
                continue
            all_triggers[t_lower] += 1
            trigger_to_skills.setdefault(t_lower, []).append(name)

    overlaps = {t: skills for t, skills in trigger_to_skills.items() if len(skills) > 1}
    if overlaps:
        # 只报告前 5 个最严重的重叠
        top_overlaps = sorted(overlaps.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        desc_lines = []
        for trigger, skills in top_overlaps:
            desc_lines.append(f"  '{trigger}' → {', '.join(skills)}")
        result.add(Finding(
            id="SKL-003",
            severity=SEVERITY_MEDIUM,
            risk_level=RISK_YELLOW,
            title=f"发现 {len(overlaps)} 个触发词在多个 Skill 间重叠",
            description="触发词重叠可能导致 Skill 选择不稳定:\n" + "\n".join(desc_lines),
            fix_suggestion="为每个 Skill 设定更精确的独占触发词，减少歧义。",
        ))


def _check_orphan_skills(result: ModuleResult, skill_data: list):
    """SKL-004: 孤立 Skill 检测（基于来源分析）"""
    # 无法直接检查使用频率，但可以检查一些特征
    # 1. Skill 来自外部（Anthropic 默认），但用户从未自定义
    # 2. Skill 的 description 中含有与当前环境无关的关键词

    # 已知的 Anthropic/Claude 原生 Skill（不针对用户业务）
    generic_skills = {
        "algorithmic-art", "brand-guidelines", "canvas-design", "claude-api",
        "slack-gif-creator", "internal-comms", "web-artifacts-builder",
    }

    found_generic = []
    for s in skill_data:
        if s["name"] in generic_skills:
            found_generic.append(s["name"])

    if found_generic:
        result.add(Finding(
            id="SKL-004",
            severity=SEVERITY_MEDIUM,
            risk_level=RISK_YELLOW,
            title=f"发现 {len(found_generic)} 个通用/非业务 Skill",
            description=(
                "以下 Skill 是通用模板，可能与当前业务场景无关:\n"
                + ", ".join(found_generic)
                + "\n如果从未使用过，可考虑归档以减少 system prompt 中的描述列表长度。"
            ),
            fix_suggestion="确认这些 Skill 是否在日常工作中使用，不用的可移至归档目录。",
        ))


def _check_env_conflicts(result: ModuleResult, skill_data: list):
    """SKL-005: 检测 Skill 中与 Windows 环境冲突的语法"""
    conflicts = []
    for s in skill_data:
        content = s["content"]
        issues = []
        # 检查 bash 语法
        if "```bash" in content:
            issues.append("使用 ```bash 代码块")
        if "#!/bin/bash" in content or "#!/usr/bin/env bash" in content:
            issues.append("包含 bash shebang")
        if "/tmp/" in content and "$env:TEMP" not in content:
            issues.append("引用 /tmp/ 路径")
        if issues:
            conflicts.append({"name": s["name"], "issues": issues})

    if conflicts:
        desc_lines = []
        for c in conflicts[:10]:  # 最多展示 10 个
            desc_lines.append(f"  {c['name']}: {'; '.join(c['issues'])}")
        result.add(Finding(
            id="SKL-005",
            severity=SEVERITY_MEDIUM,
            risk_level=RISK_YELLOW,
            title=f"{len(conflicts)} 个 Skill 含 Windows 环境冲突语法",
            description="以下 Skill 包含与 Windows 环境不兼容的语法:\n" + "\n".join(desc_lines),
            fix_suggestion="将 bash 语法替换为 PowerShell，/tmp/ 替换为 $env:TEMP。",
        ))


def _check_desc_length(result: ModuleResult, skill_data: list):
    """SKL-006: 检查描述过长"""
    long_descs = []
    for s in skill_data:
        match = re.search(r'description:\s*["\']?(.+?)(?:["\']?\s*$|\n---)', s["content"], re.DOTALL)
        if match:
            desc = match.group(1).strip()
            if len(desc) > MAX_DESC_LENGTH:
                long_descs.append({"name": s["name"], "length": len(desc)})

    if long_descs:
        desc_lines = [f"  {d['name']}: {d['length']} 字符" for d in long_descs[:10]]
        result.add(Finding(
            id="SKL-006",
            severity=SEVERITY_LOW,
            risk_level=RISK_GREEN,
            title=f"{len(long_descs)} 个 Skill 描述超过 {MAX_DESC_LENGTH} 字符",
            description="过长的描述会增加 system prompt 中技能列表的 token 消耗:\n" + "\n".join(desc_lines),
            fix_suggestion="精简 SKILL.md 的 frontmatter description 字段，保留核心触发信息。",
        ))


def _check_size_ranking(result: ModuleResult, skill_data: list):
    """SKL-007: 按大小排序的 Skills 清单"""
    ranked = sorted(skill_data, key=lambda s: s["size_kb"], reverse=True)
    lines = []
    for s in ranked[:15]:  # Top 15
        tokens = estimate_tokens(s["skill_md"].stat().st_size)
        lines.append(f"  {s['name']}: {s['size_kb']}KB (~{tokens} tokens)")

    result.add(Finding(
        id="SKL-007",
        severity=SEVERITY_INFO,
        risk_level=RISK_GREEN,
        title=f"Skills SKILL.md 大小排行 (Top 15/{len(skill_data)})",
        description="\n".join(lines),
    ))
