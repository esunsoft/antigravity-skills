# -*- coding: utf-8 -*-
"""
check_resources.py — 资源文件审计模块
检查规则: RES-001 ~ RES-004
"""

from pathlib import Path
from collections import defaultdict
from . import (
    Finding, ModuleResult, ModuleStats, Environment,
    SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO,
    RISK_YELLOW, RISK_GREEN,
    find_antigravity_dir, read_text_safe,
)

# 大文件阈值
LARGE_FILE_KB = 100
LARGE_GROUP_MB = 1.0

# 可清理的临时文件扩展名
TEMP_EXTENSIONS = {".bak", ".tmp", ".log", ".pyc", ".pyo", ".swp", ".swo"}

# 二进制资源扩展名（不含代码文件）
BINARY_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2", ".xsd", ".pdf", ".png", ".jpg", ".gif", ".ico", ".gz", ".zip"}


def run(env: Environment) -> ModuleResult:
    """执行资源文件审计"""
    result = ModuleResult(module="resources")
    skills_dir = env.skills_dir

    if not skills_dir or not skills_dir.exists():
        return result

    # 收集所有文件
    all_files = list(skills_dir.rglob("*"))
    all_files = [f for f in all_files if f.is_file()]

    total_size = sum(f.stat().st_size for f in all_files)
    result.stats = ModuleStats(
        total_size_kb=round(total_size / 1024, 1),
        estimated_tokens=0,  # 资源文件不消耗 token
        file_count=len(all_files),
    )

    # RES-001: 大体积文件
    _check_large_files(result, all_files)

    # RES-002: 孤立资源检测
    _check_orphan_resources(result, skills_dir)

    # RES-003: 临时文件
    _check_temp_files(result, all_files)

    # RES-004: 按类型统计
    _check_type_stats(result, all_files)

    return result


def _check_large_files(result: ModuleResult, all_files: list):
    """RES-001: 检测大体积文件"""
    # 按扩展名分组
    ext_groups = defaultdict(list)
    for f in all_files:
        if f.suffix.lower() in BINARY_EXTENSIONS:
            ext_groups[f.suffix.lower()].append(f)

    findings_parts = []
    for ext, files in sorted(ext_groups.items()):
        group_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
        if group_size_mb >= LARGE_GROUP_MB:
            findings_parts.append(
                f"  {ext}: {len(files)} 个文件，合计 {group_size_mb:.1f}MB"
            )

    # 单个大文件
    large_singles = []
    for f in all_files:
        size_kb = f.stat().st_size / 1024
        if size_kb > LARGE_FILE_KB and f.suffix.lower() in BINARY_EXTENSIONS:
            large_singles.append(f"  {f.relative_to(f.parents[2])}: {size_kb:.0f}KB")

    if findings_parts or large_singles:
        desc = ""
        if findings_parts:
            desc += "大体积文件组:\n" + "\n".join(findings_parts)
        if large_singles:
            if desc:
                desc += "\n\n"
            desc += f"大文件 (>{LARGE_FILE_KB}KB) 前 10 个:\n" + "\n".join(large_singles[:10])

        result.add(Finding(
            id="RES-001",
            severity=SEVERITY_MEDIUM,
            risk_level=RISK_YELLOW,
            title="发现大体积二进制资源文件",
            description=desc,
            fix_suggestion="审查这些文件是否为 Skill 运行所必需，不需要的可以移除。",
        ))


def _check_orphan_resources(result: ModuleResult, skills_dir: Path):
    """RES-002: 孤立资源检测"""
    orphans = []

    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue

        # 收集该 Skill 的所有资源文件（非 .py, .md, .json）
        resource_files = [
            f for f in skill_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in BINARY_EXTENSIONS
        ]

        if not resource_files:
            continue

        # 收集该 Skill 的所有文本文件内容（用于检查是否引用了资源）
        text_content = ""
        for tf in skill_dir.rglob("*"):
            if tf.is_file() and tf.suffix.lower() in (".py", ".md", ".json", ".js", ".ts", ".html"):
                text_content += read_text_safe(tf) + "\n"

        for rf in resource_files:
            # 检查资源文件名是否在文本内容中被引用
            if rf.name not in text_content and rf.stem not in text_content:
                rel_path = rf.relative_to(skills_dir)
                size_kb = rf.stat().st_size / 1024
                orphans.append(f"  {rel_path} ({size_kb:.0f}KB)")

    if orphans:
        result.add(Finding(
            id="RES-002",
            severity=SEVERITY_MEDIUM,
            risk_level=RISK_YELLOW,
            title=f"发现 {len(orphans)} 个疑似孤立资源文件",
            description=(
                "以下资源文件未被同一 Skill 的代码/文档引用（前 15 个）:\n"
                + "\n".join(orphans[:15])
            ),
            fix_suggestion="确认这些文件是否仍需保留，不需要的可以删除。",
        ))


def _check_temp_files(result: ModuleResult, all_files: list):
    """RES-003: 临时文件检查"""
    temp_files = [f for f in all_files if f.suffix.lower() in TEMP_EXTENSIONS]

    # 排除 __pycache__ 目录下的 .pyc（这是正常的）
    non_cache_temps = [f for f in temp_files if "__pycache__" not in str(f)]

    if non_cache_temps:
        total_kb = sum(f.stat().st_size for f in non_cache_temps) / 1024
        file_list = [f"  {f.name} ({f.stat().st_size / 1024:.1f}KB)" for f in non_cache_temps[:10]]
        result.add(Finding(
            id="RES-003",
            severity=SEVERITY_LOW,
            risk_level=RISK_GREEN,
            title=f"发现 {len(non_cache_temps)} 个临时/备份文件 ({total_kb:.1f}KB)",
            description="可清理的文件:\n" + "\n".join(file_list),
            auto_fixable=True,
            fix_suggestion="删除这些临时文件。",
            fix_command="; ".join(f'Remove-Item "{f}"' for f in non_cache_temps),
        ))

    # 检查 __pycache__ 目录
    pyc_files = [f for f in temp_files if "__pycache__" in str(f)]
    if pyc_files:
        pyc_dirs = set(f.parent for f in pyc_files)
        total_kb = sum(f.stat().st_size for f in pyc_files) / 1024
        result.add(Finding(
            id="RES-003b",
            severity=SEVERITY_LOW,
            risk_level=RISK_GREEN,
            title=f"发现 {len(pyc_dirs)} 个 __pycache__ 目录 ({total_kb:.0f}KB)",
            description=f"包含 {len(pyc_files)} 个 .pyc 文件",
            auto_fixable=True,
            fix_suggestion="清理 __pycache__ 目录。",
            fix_command="; ".join(f'Remove-Item -Recurse -Force "{d}"' for d in pyc_dirs),
        ))


def _check_type_stats(result: ModuleResult, all_files: list):
    """RES-004: 按类型统计"""
    ext_stats = defaultdict(lambda: {"count": 0, "size": 0})
    for f in all_files:
        ext = f.suffix.lower() if f.suffix else "(无扩展名)"
        ext_stats[ext]["count"] += 1
        ext_stats[ext]["size"] += f.stat().st_size

    lines = []
    for ext, stats in sorted(ext_stats.items(), key=lambda x: x[1]["size"], reverse=True)[:15]:
        size_str = f"{stats['size'] / 1024:.1f}KB" if stats["size"] < 1024 * 1024 else f"{stats['size'] / (1024 * 1024):.1f}MB"
        lines.append(f"  {ext}: {stats['count']} 个, {size_str}")

    result.add(Finding(
        id="RES-004",
        severity=SEVERITY_INFO,
        risk_level=RISK_GREEN,
        title=f"资源文件类型统计 (共 {len(all_files)} 个文件)",
        description="\n".join(lines),
    ))
