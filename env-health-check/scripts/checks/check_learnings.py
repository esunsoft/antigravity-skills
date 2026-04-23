# -*- coding: utf-8 -*-
"""
check_learnings.py — 学习记录积压检查模块
检查规则: LRN-001 ~ LRN-003
"""

import re
from pathlib import Path
from . import (
    Finding, ModuleResult, ModuleStats, Environment,
    SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO,
    RISK_YELLOW, RISK_GREEN,
    find_gemini_dir, read_text_safe,
)

# 阈值
MAX_LEARNINGS_SIZE_KB = 50


def run(env: Environment) -> ModuleResult:
    """执行学习记录检查"""
    result = ModuleResult(module="learnings")
    ld = env.learnings_dir

    if not ld or not ld.exists():
        result.stats = ModuleStats(file_count=0)
        result.add(Finding(
            id="LRN-003",
            severity=SEVERITY_INFO,
            risk_level=RISK_GREEN,
            title="未发现 .learnings 目录",
            description=f"环境 {env.display_name} 中没有 .learnings 目录",
        ))
        return result

    learnings_dirs = [ld]

    if not learnings_dirs:
        result.stats = ModuleStats(file_count=0)
        result.add(Finding(
            id="LRN-003",
            severity=SEVERITY_INFO,
            risk_level=RISK_GREEN,
            title="未发现 .learnings 目录",
            description="当前环境中没有 .learnings 目录",
        ))
        return result

    all_files = []
    for ld in learnings_dirs:
        all_files.extend(f for f in ld.rglob("*") if f.is_file())

    total_size = sum(f.stat().st_size for f in all_files)
    result.stats = ModuleStats(
        total_size_kb=round(total_size / 1024, 1),
        file_count=len(all_files),
    )

    # LRN-001: 未处理的 high/critical 条目
    _check_unresolved_critical(result, all_files)

    # LRN-002: 总量过大
    _check_total_size(result, total_size, all_files)

    # LRN-003: 统计信息
    _check_stats(result, learnings_dirs, all_files)

    return result




def _check_unresolved_critical(result: ModuleResult, all_files: list):
    """LRN-001: 检测未处理的 high/critical 级别条目"""
    unresolved = []

    for f in all_files:
        if f.suffix.lower() != ".md":
            continue
        content = read_text_safe(f)
        # 查找 priority: high/critical 且 status 不是 resolved 的条目
        entries = re.findall(
            r'(?:^|\n)##\s+(.+?)(?:\n.*?priority:\s*(high|critical).*?(?:status:\s*(\w+))?)',
            content,
            re.DOTALL | re.IGNORECASE,
        )
        for title, priority, status in entries:
            if status.lower() not in ("resolved", "done", "closed", "promoted"):
                unresolved.append({
                    "file": f.name,
                    "title": title.strip()[:60],
                    "priority": priority,
                })

        # 简化检查：如果文件名含 ERRORS 或 LEARNINGS，检查是否有 high/critical 关键词
        if not entries and f.stem.upper() in ("ERRORS", "LEARNINGS"):
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if re.search(r'\b(high|critical)\b', line, re.IGNORECASE):
                    # 检查是否有 resolved 标记
                    context = "\n".join(lines[max(0, i - 2):i + 3])
                    if not re.search(r'\b(resolved|done|closed|promoted)\b', context, re.IGNORECASE):
                        unresolved.append({
                            "file": f.name,
                            "title": line.strip()[:60],
                            "priority": "high",
                        })

    if unresolved:
        desc_lines = [f"  [{u['priority']}] {u['file']}: {u['title']}" for u in unresolved[:10]]
        result.add(Finding(
            id="LRN-001",
            severity=SEVERITY_MEDIUM,
            risk_level=RISK_YELLOW,
            title=f"发现 {len(unresolved)} 个未处理的 high/critical 学习记录",
            description="以下条目需要处理或提升为 Knowledge Item:\n" + "\n".join(desc_lines),
            fix_suggestion="处理这些条目：修复问题、提升为 KI、或标记为已解决。",
        ))


def _check_total_size(result: ModuleResult, total_size: int, all_files: list):
    """LRN-002: 总量过大"""
    total_kb = total_size / 1024
    if total_kb > MAX_LEARNINGS_SIZE_KB:
        result.add(Finding(
            id="LRN-002",
            severity=SEVERITY_LOW,
            risk_level=RISK_GREEN,
            title=f".learnings 总量偏大 ({total_kb:.1f}KB，阈值 {MAX_LEARNINGS_SIZE_KB}KB)",
            description=(
                f"包含 {len(all_files)} 个文件，合计 {total_kb:.1f}KB。"
                "过多的学习记录可能降低 self-improvement 机制的效率。"
                "建议定期归档已解决的条目。"
            ),
            fix_suggestion="将已解决的条目归档到 .learnings/archive/ 目录。",
        ))


def _check_stats(result: ModuleResult, learnings_dirs: list, all_files: list):
    """LRN-003: 统计信息"""
    lines = []
    for ld in learnings_dirs:
        files = [f for f in all_files if str(f).startswith(str(ld))]
        dir_size = sum(f.stat().st_size for f in files) / 1024
        lines.append(f"  {ld}: {len(files)} 个文件, {dir_size:.1f}KB")
        for f in files:
            lines.append(f"    {f.name}: {f.stat().st_size / 1024:.1f}KB")

    result.add(Finding(
        id="LRN-003",
        severity=SEVERITY_INFO,
        risk_level=RISK_GREEN,
        title=f".learnings 统计 ({len(all_files)} 个文件)",
        description="\n".join(lines),
    ))
