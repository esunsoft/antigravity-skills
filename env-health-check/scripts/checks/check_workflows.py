# -*- coding: utf-8 -*-
"""
check_workflows.py — Workflows 一致性检查模块
检查规则: WFL-001 ~ WFL-004
"""

import re
from pathlib import Path
from . import (
    Finding, ModuleResult, ModuleStats, Environment,
    SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO,
    RISK_YELLOW, RISK_GREEN,
    estimate_tokens, get_file_size_kb, read_text_safe,
    find_antigravity_dir,
)


def run(env: Environment) -> ModuleResult:
    """执行 Workflows 一致性检查"""
    result = ModuleResult(module="workflows")
    wf_dir = env.workflows_dir
    skills_dir = env.skills_dir
    antigravity_dir = env.base_dir

    if not wf_dir or not wf_dir.exists():
        return result

    wf_files = list(wf_dir.glob("*.md"))
    total_size = sum(f.stat().st_size for f in wf_files)

    result.stats = ModuleStats(
        total_size_kb=round(total_size / 1024, 1),
        estimated_tokens=estimate_tokens(total_size),
        file_count=len(wf_files),
    )

    # 读取所有 workflow 内容
    wf_data = []
    for f in wf_files:
        wf_data.append({
            "name": f.stem,
            "path": f,
            "content": read_text_safe(f),
            "size_kb": get_file_size_kb(f),
        })

    # WFL-001: 与同名 Skill 重叠
    _check_skill_overlap(result, wf_data, skills_dir)

    # WFL-002: bash 语法
    _check_bash_syntax(result, wf_data)

    # WFL-003: 脚本路径失效
    _check_script_paths(result, wf_data, antigravity_dir)

    # WFL-004: 统计信息
    _check_stats(result, wf_data)

    return result


def _check_skill_overlap(result: ModuleResult, wf_data: list, skills_dir: Path):
    """WFL-001: 检测 Workflow 与 Skill 功能重叠"""
    overlaps = []
    for wf in wf_data:
        # 检查是否有同名或相似名称的 skill
        wf_base = wf["name"].replace("superpowers-", "")
        content = wf["content"]

        # 检查 workflow 是否只是简单地调用一个 skill
        skill_ref = re.search(r'Read and apply the `([^`]+)` skill', content)
        if skill_ref:
            ref_skill = skill_ref.group(1)
            skill_path = skills_dir / ref_skill / "SKILL.md"
            if skill_path.exists():
                overlaps.append({
                    "workflow": wf["name"],
                    "skill": ref_skill,
                    "is_thin_wrapper": True,
                })

        # 检查目录名匹配
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and skill_dir.name == wf["name"]:
                overlaps.append({
                    "workflow": wf["name"],
                    "skill": skill_dir.name,
                    "is_thin_wrapper": False,
                })

    if overlaps:
        desc_lines = []
        for o in overlaps:
            wrapper_note = " (仅为薄包装器)" if o["is_thin_wrapper"] else ""
            desc_lines.append(f"  Workflow '{o['workflow']}' ↔ Skill '{o['skill']}'{wrapper_note}")

        result.add(Finding(
            id="WFL-001",
            severity=SEVERITY_MEDIUM,
            risk_level=RISK_YELLOW,
            title=f"{len(overlaps)} 个 Workflow 与 Skill 功能重叠",
            description=(
                "以下 Workflow 与对应 Skill 存在功能重叠:\n"
                + "\n".join(desc_lines)
                + "\n薄包装器型 Workflow 仅调用 Skill 然后保存输出，可考虑合并或删除。"
            ),
            fix_suggestion="评估是否需要同时保留 Workflow 和 Skill，薄包装器可直接删除。",
        ))


def _check_bash_syntax(result: ModuleResult, wf_data: list):
    """WFL-002: 检测 bash 语法"""
    bash_wfs = []
    for wf in wf_data:
        content = wf["content"]
        issues = []
        if "```bash" in content:
            issues.append("```bash 代码块")
        if re.search(r'python\s+\.agent/', content):
            issues.append("使用 .agent/ 路径（非 Windows 标准）")
        if issues:
            bash_wfs.append({"name": wf["name"], "issues": issues})

    if bash_wfs:
        desc_lines = [f"  {w['name']}: {'; '.join(w['issues'])}" for w in bash_wfs]
        result.add(Finding(
            id="WFL-002",
            severity=SEVERITY_MEDIUM,
            risk_level=RISK_YELLOW,
            title=f"{len(bash_wfs)} 个 Workflow 使用 bash/非 Windows 语法",
            description="与 Windows 11 环境冲突:\n" + "\n".join(desc_lines),
            fix_suggestion="将 ```bash 改为 ```powershell，路径改为 Windows 格式。",
        ))


def _check_script_paths(result: ModuleResult, wf_data: list, antigravity_dir: Path):
    """WFL-003: 检测引用脚本路径是否存在"""
    broken = []
    for wf in wf_data:
        # 提取 python 命令中的脚本路径
        scripts = re.findall(r'python\s+["\']?([^\s"\']+\.py)', wf["content"])
        for script in scripts:
            # 尝试解析路径
            script_path = Path(script)
            if not script_path.is_absolute():
                # 相对路径，尝试从 antigravity_dir 解析
                resolved = antigravity_dir / script
                if not resolved.exists():
                    broken.append({"workflow": wf["name"], "script": script})

    if broken:
        desc_lines = [f"  {b['workflow']}: {b['script']}" for b in broken]
        result.add(Finding(
            id="WFL-003",
            severity=SEVERITY_LOW,
            risk_level=RISK_GREEN,
            title=f"{len(broken)} 个 Workflow 引用了不存在的脚本路径",
            description="以下脚本路径无法解析:\n" + "\n".join(desc_lines),
            fix_suggestion="修正脚本路径或删除无效的 Workflow。",
        ))


def _check_stats(result: ModuleResult, wf_data: list):
    """WFL-004: 统计信息"""
    lines = [f"  {wf['name']}: {wf['size_kb']}KB" for wf in sorted(wf_data, key=lambda w: w["size_kb"], reverse=True)]
    result.add(Finding(
        id="WFL-004",
        severity=SEVERITY_INFO,
        risk_level=RISK_GREEN,
        title=f"Workflows 统计 ({len(wf_data)} 个，共 {result.stats.total_size_kb}KB)",
        description="\n".join(lines),
    ))
