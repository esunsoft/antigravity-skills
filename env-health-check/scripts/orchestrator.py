# -*- coding: utf-8 -*-
"""
orchestrator.py — 主编排器
调度所有检查模块，汇总结果输出 JSON
"""

import sys
import json
import argparse
import time
from pathlib import Path

# 将 scripts 目录加入 sys.path 以支持相对导入
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from checks import (
    ModuleResult, Environment, detect_environments,
    ENV_ANTIGRAVITY, ENV_CLAUDE_CLI, ENV_CLAUDE_VS
)
from checks import check_gemini as check_config
from checks import check_skills
from checks import check_workflows
from checks import check_resources
from checks import check_knowledge
from checks import check_mcp
from checks import check_learnings


# 模块注册表（名称 → 运行函数）
MODULE_REGISTRY = [
    ("config",    check_config.run),
    ("skills",    check_skills.run),
    ("workflows", check_workflows.run),
    ("resources", check_resources.run),
    ("knowledge", check_knowledge.run),
    ("mcp",       check_mcp.run),
    ("learnings", check_learnings.run),
]


def run_env_checks(env: Environment, modules: list = None) -> dict:
    """运行指定环境的所有检查模块"""
    results = []
    errors = []
    start_time = time.time()

    for name, run_func in MODULE_REGISTRY:
        if modules and name not in modules:
            continue

        # 特殊模块过滤：某些环境可能不具备某些特性
        if name == "workflows" and not env.workflows_dir:
            continue
        if name == "knowledge" and not env.knowledge_dir:
            continue

        try:
            module_result = run_func(env)
            results.append(module_result.to_dict())
        except Exception as e:
            errors.append({"module": name, "error": str(e)})
            empty = ModuleResult(module=name)
            results.append(empty.to_dict())

    elapsed = round(time.time() - start_time, 2)

    # 汇总统计
    total_findings = sum(len(r["findings"]) for r in results)
    severity_counts = {}
    for r in results:
        for f in r["findings"]:
            sev = f["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

    total_recoverable_tokens = sum(
        f.get("impact_tokens", 0)
        for r in results
        for f in r["findings"]
    )

    return {
        "env_name": env.name,
        "display_name": env.display_name,
        "elapsed_seconds": elapsed,
        "summary": {
            "total_findings": total_findings,
            "severity_counts": severity_counts,
            "total_recoverable_tokens": total_recoverable_tokens,
            "modules_checked": len(results),
        },
        "modules": results,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Claude 环境健康检查编排器 (支持 Antigravity, CLI, VS)"
    )
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="指定环境名称 (antigravity, claude_cli, claude_vs), 多个用逗号分隔，默认全部",
    )
    parser.add_argument(
        "--modules",
        type=str,
        default=None,
        help="要运行的模块列表 (config, skills, workflows, etc.), 默认全部",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出 JSON 文件路径",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="格式化 JSON 输出",
    )

    args = parser.parse_args()

    # 环境检测
    all_envs = detect_environments()
    if args.env:
        target_envs = args.env.split(",")
        envs = [e for e in all_envs if e.name in target_envs]
    else:
        envs = all_envs

    if not envs:
        print("未检测到指定的运行环境。", file=sys.stderr)
        sys.exit(1)

    modules = args.modules.split(",") if args.modules else None

    # 执行检查
    env_results = [run_env_checks(env, modules) for env in envs]

    output = {
        "version": "2.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "environments": env_results,
    }

    indent = 2 if args.pretty else None
    json_str = json.dumps(output, ensure_ascii=False, indent=indent)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str, encoding="utf-8")
        print(f"结果已保存到: {output_path}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
