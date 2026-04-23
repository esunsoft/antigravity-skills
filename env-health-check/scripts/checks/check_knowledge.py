# -*- coding: utf-8 -*-
"""
check_knowledge.py — Knowledge Items 时效性检查模块
检查规则: KNW-001 ~ KNW-003
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from . import (
    Finding, ModuleResult, ModuleStats, Environment,
    SEVERITY_LOW, SEVERITY_INFO,
    RISK_YELLOW, RISK_GREEN,
    find_antigravity_dir, read_text_safe,
)

# 过时阈值（天）
STALE_DAYS = 30


def run(env: Environment) -> ModuleResult:
    """执行 Knowledge Items 检查"""
    result = ModuleResult(module="knowledge")
    ki_dir = env.knowledge_dir

    if not ki_dir or not ki_dir.exists():
        return result

    ki_dirs = [d for d in ki_dir.iterdir() if d.is_dir()]
    ki_data = []

    for d in ki_dirs:
        meta_file = d / "metadata.json"
        if meta_file.exists():
            try:
                meta = json.loads(read_text_safe(meta_file))
                ki_data.append({
                    "name": d.name,
                    "path": d,
                    "metadata": meta,
                })
            except json.JSONDecodeError:
                ki_data.append({
                    "name": d.name,
                    "path": d,
                    "metadata": {},
                })

    total_size = sum(
        sum(f.stat().st_size for f in d["path"].rglob("*") if f.is_file())
        for d in ki_data
    )

    result.stats = ModuleStats(
        total_size_kb=round(total_size / 1024, 1),
        estimated_tokens=0,  # KI 按需加载，不持续消耗
        file_count=len(ki_data),
    )

    # KNW-001: 时效性检查
    _check_staleness(result, ki_data)

    # KNW-002: 引用文件检查
    _check_broken_refs(result, ki_data)

    # KNW-003: 统计信息
    _check_stats(result, ki_data)

    return result


def _check_staleness(result: ModuleResult, ki_data: list):
    """KNW-001: 检测过时的 KI"""
    stale_kis = []
    now = datetime.now(timezone.utc)

    for ki in ki_data:
        meta = ki["metadata"]
        last_accessed = meta.get("lastAccessed") or meta.get("last_accessed")
        if last_accessed:
            try:
                # 尝试解析时间戳
                if isinstance(last_accessed, str):
                    # 移除可能的时区信息简化解析
                    ts = last_accessed.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(ts)
                    days_ago = (now - dt).days
                    if days_ago > STALE_DAYS:
                        stale_kis.append({
                            "name": ki["name"],
                            "days_ago": days_ago,
                            "last_accessed": last_accessed,
                        })
            except (ValueError, TypeError):
                pass

    if stale_kis:
        desc_lines = [f"  {s['name']}: {s['days_ago']} 天前 ({s['last_accessed'][:10]})" for s in stale_kis]
        result.add(Finding(
            id="KNW-001",
            severity=SEVERITY_LOW,
            risk_level=RISK_YELLOW,
            title=f"{len(stale_kis)} 个 KI 超过 {STALE_DAYS} 天未被访问",
            description="可能已过时的 Knowledge Items:\n" + "\n".join(desc_lines),
            fix_suggestion="确认这些 KI 是否仍然准确有效，过时的可以更新或删除。",
        ))


def _check_broken_refs(result: ModuleResult, ki_data: list):
    """KNW-002: 检测引用文件失效"""
    broken = []

    for ki in ki_data:
        artifacts_dir = ki["path"] / "artifacts"
        if artifacts_dir.exists():
            # 检查 metadata 中列出的 artifact 文件是否存在
            meta = ki["metadata"]
            artifacts = meta.get("artifacts", [])
            if isinstance(artifacts, list):
                for art in artifacts:
                    if isinstance(art, str):
                        art_path = artifacts_dir / art
                        if not art_path.exists():
                            broken.append(f"  {ki['name']}: {art} (文件不存在)")
                    elif isinstance(art, dict):
                        art_file = art.get("path") or art.get("file")
                        if art_file:
                            art_path = artifacts_dir / art_file
                            if not art_path.exists():
                                broken.append(f"  {ki['name']}: {art_file} (文件不存在)")

    if broken:
        result.add(Finding(
            id="KNW-002",
            severity=SEVERITY_LOW,
            risk_level=RISK_GREEN,
            title=f"{len(broken)} 个 KI artifact 引用失效",
            description="以下引用的文件不存在:\n" + "\n".join(broken),
            fix_suggestion="更新 metadata.json 中的引用，或恢复缺失的文件。",
        ))


def _check_stats(result: ModuleResult, ki_data: list):
    """KNW-003: KI 统计信息"""
    lines = []
    for ki in ki_data:
        meta = ki["metadata"]
        summary = meta.get("summary", "无摘要")
        if len(summary) > 60:
            summary = summary[:60] + "..."
        ki_size = sum(f.stat().st_size for f in ki["path"].rglob("*") if f.is_file())
        lines.append(f"  {ki['name']}: {ki_size / 1024:.1f}KB - {summary}")

    result.add(Finding(
        id="KNW-003",
        severity=SEVERITY_INFO,
        risk_level=RISK_GREEN,
        title=f"Knowledge Items 统计 ({len(ki_data)} 个)",
        description="\n".join(lines) if lines else "  无 Knowledge Items",
    ))
