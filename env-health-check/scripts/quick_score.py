# -*- coding: utf-8 -*-
"""
quick_score.py — 轻量级快速评分（< 3秒）
仅统计文件数量和大小，不做深度分析
输出 0-100 环境健康评分
"""

import sys
import json
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from checks import (
    MODULE_WEIGHTS, SEVERITY_PENALTY,
    Environment, detect_environments,
    get_file_size_kb, read_text_safe,
)


# 快速评分阈值
THRESHOLDS = {
    "config_max_kb": 12.0,  # Claude CLI 的 CLAUDE.md 通常比较大
    "skill_max_count": 50,
    "skill_max_single_kb": 25.0,
    "workflow_bash_check": True,
    "resource_max_mb": 5.0,
    "ki_stale_days": 30,
    "learnings_max_kb": 100,
}


def quick_score(env: Environment) -> dict:
    """快速计算指定环境的健康评分"""
    scores = {}
    issues = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    # === 配置层评分 (Config/Rules) ===
    config_score = 100
    rule_file = env.config_dir / env.rule_file
    if rule_file.exists():
        size_kb = get_file_size_kb(rule_file)
        if size_kb > THRESHOLDS["config_max_kb"]:
            config_score -= 10
            issues["medium"] += 1
        
        # 检查备份文件
        bak_count = len(list(env.config_dir.glob(f"{env.rule_file}*.bak")))
        if bak_count > 0:
            config_score -= min(bak_count * 2, 6)
            issues["low"] += bak_count
            
        # 角色定位/注入检查
        content = read_text_safe(rule_file)
        if "角色定义" in content or "Role Definition" in content:
            # 如果内容过大且包含重复注入迹象
            if size_kb > 10.0 and content.count("##") > 20:
                config_score -= 5
                issues["low"] += 1
    else:
        config_score -= 20
        issues["high"] += 1
    scores["config"] = max(0, config_score)

    # === Skills 评分 ===
    skills_score = 100
    if env.skills_dir.exists():
        skill_dirs = [d for d in env.skills_dir.iterdir() if d.is_dir()]
        skill_count = len(skill_dirs)
        if skill_count > THRESHOLDS["skill_max_count"]:
            skills_score -= 10
            issues["high"] += 1
        
        # 检查过大的 SKILL.md
        oversized = 0
        for sd in skill_dirs:
            skill_md = sd / "SKILL.md"
            if skill_md.exists() and get_file_size_kb(skill_md) > THRESHOLDS["skill_max_single_kb"]:
                oversized += 1
        if oversized > 0:
            skills_score -= min(oversized * 5, 20)
            issues["medium"] += oversized
    else:
        skills_score = 100 # 如果没有 skills 目录，可能该环境不使用 skills
    scores["skills"] = max(0, skills_score)

    # === Workflows 评分 ===
    wf_score = 100
    if env.workflows_dir and env.workflows_dir.exists():
        for wf in env.workflows_dir.glob("*.md"):
            content = read_text_safe(wf)
            if "```bash" in content:
                wf_score -= 5
                issues["medium"] += 1
    scores["workflows"] = max(0, wf_score)

    # === 资源文件评分 ===
    res_score = 100
    if env.skills_dir.exists():
        binary_exts = {".ttf", ".otf", ".woff", ".xsd", ".pdf", ".gz", ".zip", ".exe", ".dll"}
        total_binary_mb = 0
        temp_count = 0
        for f in env.skills_dir.rglob("*"):
            if f.is_file():
                if f.suffix.lower() in binary_exts:
                    total_binary_mb += f.stat().st_size / (1024 * 1024)
                if f.suffix.lower() in {".bak", ".tmp", ".log", ".pyc"}:
                    temp_count += 1
        if total_binary_mb > THRESHOLDS["resource_max_mb"]:
            res_score -= 15
            issues["medium"] += 1
        if temp_count > 0:
            res_score -= min(temp_count * 2, 10)
            issues["low"] += temp_count
    scores["resources"] = max(0, res_score)

    # === Knowledge Items 评分 ===
    ki_score = 100
    if env.knowledge_dir and env.knowledge_dir.exists():
        ki_count = len([d for d in env.knowledge_dir.iterdir() if d.is_dir()])
        if ki_count == 0:
            ki_score -= 5
    scores["knowledge"] = max(0, ki_score)

    # === MCP/Settings 评分 ===
    mcp_score = 100
    if env.mcp_config and env.mcp_config.exists():
        try:
            content = read_text_safe(env.mcp_config)
            json.loads(content)
        except json.JSONDecodeError:
            mcp_score -= 10
            issues["high"] += 1
    scores["mcp"] = max(0, mcp_score)

    # === 学习记录评分 ===
    lrn_score = 100
    if env.learnings_dir and env.learnings_dir.exists():
        total_kb = sum(f.stat().st_size for f in env.learnings_dir.rglob("*") if f.is_file()) / 1024
        if total_kb > THRESHOLDS["learnings_max_kb"]:
            lrn_score -= 5
            issues["low"] += 1
    scores["learnings"] = max(0, lrn_score)

    # === 加权总分 ===
    total_score = round(sum(scores[k] * MODULE_WEIGHTS[k] for k in scores))

    return {
        "env_name": env.display_name,
        "total_score": total_score,
        "module_scores": scores,
        "issues": issues,
        "recommendation": _get_recommendation(total_score, issues),
    }


def _get_recommendation(score: int, issues: dict) -> str:
    """根据分数给出建议"""
    high_count = issues.get("critical", 0) + issues.get("high", 0)
    if score >= 85:
        return "✅ 极佳"
    elif score >= 75:
        return "💡 良好"
    elif score >= 60:
        return "⚠️ 待优化"
    else:
        return "🚨 建议清理"


def _render_bar(score: int, width: int = 10) -> str:
    """渲染进度条"""
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def print_summary(results: list):
    """打印所有环境的汇总评分"""
    print("\n" + "═" * 50)
    print("       🚀 Claude 环境健康检查报告 🚀")
    print("═" * 50)
    
    for res in results:
        total = res["total_score"]
        bar = _render_bar(total, width=15)
        print(f"[{res['env_name']:^20}] {bar} {total:3d}/100 {res['recommendation']}")
    
    print("═" * 50)
    print("使用 --full 模式获取详细报告及修复建议。\n")


def main():
    parser = argparse.ArgumentParser(description="Claude 环境快速健康评分")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    envs = detect_environments()
    if not envs:
        print("未检测到任何有效的 Claude/Antigravity 环境。")
        sys.exit(1)

    results = [quick_score(env) for env in envs]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_summary(results)


if __name__ == "__main__":
    main()
