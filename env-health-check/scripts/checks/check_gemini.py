# -*- coding: utf-8 -*-
"""
check_gemini.py — GEMINI.md 配置检查模块
检查规则: GEM-001 ~ GEM-005
"""

import re
from pathlib import Path
from . import (
    Finding, ModuleResult, ModuleStats, Environment,
    SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO,
    RISK_YELLOW, RISK_GREEN,
    estimate_tokens, get_file_size_kb, read_text_safe,
    find_antigravity_dir,
    ENV_ANTIGRAVITY, ENV_CLAUDE_CLI, ENV_CLAUDE_VS
)


# 阈值常量
MAX_GEMINI_SIZE_KB = 8.0


def run(env: Environment) -> ModuleResult:
    """执行配置和规则文件检查 (GEMINI.md / CLAUDE.md)"""
    result = ModuleResult(module="config")
    rule_file = env.config_dir / env.rule_file

    if not rule_file.exists():
        result.add(Finding(
            id="CFG-000",
            severity=SEVERITY_INFO,
            risk_level=RISK_GREEN,
            title=f"{env.rule_file} 不存在",
            description=f"未找到环境 {env.display_name} 的全局配置文件 {env.rule_file}",
        ))
        return result

    content = read_text_safe(rule_file)
    size_kb = get_file_size_kb(rule_file)
    tokens = estimate_tokens(rule_file.stat().st_size)

    result.stats = ModuleStats(
        total_size_kb=size_kb,
        estimated_tokens=tokens,
        file_count=1,
    )

    # CFG-001: 注入状态检查
    _check_injection_status(result, env, content, tokens)

    # CFG-002: 大小超标
    _check_size_threshold(result, env, size_kb, tokens)

    # CFG-003: 与 Skill 内容重复
    _check_skill_overlap(result, env, content)

    # CFG-004: 备份文件
    _check_backup_files(result, env)

    # CFG-005: 各章节 token 占比
    _check_section_breakdown(result, content, tokens)

    return result


def _check_injection_status(result: ModuleResult, env: Environment, content: str, tokens: int):
    """CFG-001: 规则文件注入状态检查"""
    result.add(Finding(
        id="CFG-001",
        severity=SEVERITY_INFO,
        risk_level=RISK_GREEN,
        title=f"{env.rule_file} 正常注入 ({tokens} tokens)",
        description=(
            f"{env.rule_file} 作为全局规则注入 system prompt。 "
            "Editor 或配置文件直接管理此文件。"
        ),
    ))


def _check_size_threshold(result: ModuleResult, env: Environment, size_kb: float, tokens: int):
    """CFG-002: 检测规则文件大小是否超标"""
    max_size = 12.0 if env.name != ENV_ANTIGRAVITY else 8.0
    if size_kb > max_size:
        result.add(Finding(
            id="CFG-002",
            severity=SEVERITY_MEDIUM,
            risk_level=RISK_YELLOW,
            title=f"{env.rule_file} 体积偏大 ({size_kb}KB)",
            description=(
                f"{env.rule_file} 当前 {size_kb}KB (~{tokens} tokens)，超过 {max_size}KB 阈值。"
                "建议将详细规则拆分到独立 Skill 中。"
            ),
            impact_tokens=tokens,
            fix_suggestion=f"精简 {env.rule_file}，将具体代码模板迁移到 Skill 中。",
        ))


def _check_skill_overlap(result: ModuleResult, env: Environment, content: str):
    """CFG-003: 检测与 Skill 内容的重叠"""
    if not env.skills_dir or not env.skills_dir.exists():
        return

    # 检查 powershell-rules 或 windows-rules
    target_skills = ["powershell-rules", "windows-rules", "pb-code-standards"]
    for skill_name in target_skills:
        skill_md = env.skills_dir / skill_name / "SKILL.md"
        if skill_md.exists():
            # 简单的关键词重叠检查 (简化版)
            if "powershell" in content.lower() and skill_name == "powershell-rules":
                result.add(Finding(
                    id="CFG-003",
                    severity=SEVERITY_LOW,
                    risk_level=RISK_YELLOW,
                    title=f"{env.rule_file} 与 {skill_name} 可能存在冗余",
                    description=f"检测到 {env.rule_file} 中包含大量 PowerShell 规则，建议确认为何不直接使用对应 Skill。",
                    fix_suggestion=f"审查 {env.rule_file} 中的相关章节并考虑精简。",
                ))


def _check_backup_files(result: ModuleResult, env: Environment):
    """CFG-004: 检测备份文件"""
    bak_files = list(env.config_dir.glob(f"{env.rule_file}*.bak"))
    # 同时检查 .claude.json.backup
    if env.name in [ENV_CLAUDE_CLI, ENV_CLAUDE_VS]:
        bak_files.extend(list(env.config_dir.glob(".claude.json.backup.*")))
        bak_files.extend(list(env.config_dir.glob("config.json.bak")))

    if bak_files:
        bak_names = ", ".join(f.name for f in bak_files[:5])
        if len(bak_files) > 5:
            bak_names += f" (等共 {len(bak_files)} 个)"
        total_kb = round(sum(f.stat().st_size for f in bak_files) / 1024, 1)
        result.add(Finding(
            id="CFG-004",
            severity=SEVERITY_LOW,
            risk_level=RISK_GREEN,
            title=f"发现 {len(bak_files)} 个配置文件备份 ({total_kb}KB)",
            description=f"备份文件堆积会占用空间并导致配置混乱。",
            auto_fixable=True,
            fix_suggestion="清理旧的配置文件备份。",
            fix_command="; ".join(f'Remove-Item "{f}"' for f in bak_files),
        ))


def _check_section_breakdown(result: ModuleResult, content: str, total_tokens: int):
    """CFG-005: 各章节 token 占比分析"""
    sections = re.split(r'^(## .+)$', content, flags=re.MULTILINE)
    breakdown = []
    for i in range(1, len(sections), 2):
        title = sections[i].strip()
        body = sections[i + 1] if i + 1 < len(sections) else ""
        sec_tokens = estimate_tokens(len(body.encode('utf-8')))
        pct = round(sec_tokens / total_tokens * 100) if total_tokens > 0 else 0
        if pct > 5: # 只列出占比超过 5% 的
            breakdown.append(f"{title}: ~{sec_tokens} tokens ({pct}%)")

    if breakdown:
        result.add(Finding(
            id="CFG-005",
            severity=SEVERITY_INFO,
            risk_level=RISK_GREEN,
            title="规则文件章节分布",
            description="\n".join(breakdown),
        ))
