# -*- coding: utf-8 -*-
"""
reporter.py — Markdown 报告生成器
从 orchestrator.py 输出的 JSON 生成结构化 Markdown 体检报告
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime


# 严重程度的显示映射
SEVERITY_LABELS = {
    "critical": "🔴 Critical",
    "high": "🔴 High",
    "medium": "🟡 Medium",
    "low": "🟢 Low",
    "info": "ℹ️ Info",
}

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

MODULE_LABELS = {
    "config": "配置层 (GEMINI/CLAUDE)",
    "skills": "Skills 健康度",
    "workflows": "Workflows 一致性",
    "resources": "资源文件整洁度",
    "knowledge": "Knowledge Items",
    "mcp": "MCP 配置",
    "learnings": "学习记录",
}


def generate_report(data: dict) -> str:
    """从 JSON 数据生成 Markdown 报告"""
    lines = []

    # === 报告头部 ===
    lines.append("# 🏥 Claude 环境健康体检报告")
    lines.append("")
    timestamp = data.get("timestamp", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    lines.append(f"> 生成时间: {timestamp}")
    lines.append(f"> Skill 版本: {data.get('version', '2.0.0')}")
    lines.append("")

    envs = data.get("environments", [])
    if not envs:
        lines.append("⚠️ 未检测到任何运行环境。")
        return "\n".join(lines)

    # === 跨环境摘要表 ===
    lines.append("## 📊 跨环境汇总")
    lines.append("")
    lines.append("| 环境 | 问题数 | 预估可回收 Token | 扫描耗时 |")
    lines.append("|------|--------|-----------------|----------|")

    for env_data in envs:
        summary = env_data.get("summary", {})
        total_sev = summary.get("severity_counts", {})
        total_high = total_sev.get("critical", 0) + total_sev.get("high", 0)
        total_med = total_sev.get("medium", 0)
        total_count_str = f"{total_high} 🔴 {total_med} 🟡" if (total_high + total_med) > 0 else "✅ 正常"
        total_tokens = summary.get("total_recoverable_tokens", 0)
        token_str = f"~{total_tokens:,}" if total_tokens > 0 else "—"
        lines.append(f"| **{env_data['display_name']}** | {total_count_str} | {token_str} | {env_data.get('elapsed_seconds', 0)}s |")

    lines.append("")

    # === 详情循环 ===
    for env_data in envs:
        lines.append(f"## 🌐 环境详情: {env_data['display_name']}")
        lines.append("")

        # 环境得分表
        lines.append("| 模块 | 得分 | 问题分布 | 影响 Token |")
        lines.append("|------|------|----------|-----------|")

        for mod in env_data.get("modules", []):
            mod_name = mod["module"]
            label = MODULE_LABELS.get(mod_name, mod_name)
            findings = mod.get("findings", [])

            # 计算得分
            from checks import SEVERITY_PENALTY
            penalty = sum(SEVERITY_PENALTY.get(f["severity"], 0) for f in findings)
            score = max(0, 100 - penalty)

            # 统计问题数
            sev_counts = {}
            for f in findings:
                sev = f["severity"]
                if sev != "info":
                    sev_counts[sev] = sev_counts.get(sev, 0) + 1

            count_str = " ".join(
                f"{c}{'🔴' if s in ('critical', 'high') else '🟡' if s == 'medium' else '🟢'}"
                for s, c in sorted(sev_counts.items(), key=lambda x: SEVERITY_ORDER.index(x[0]))
            ) or "—"

            mod_tokens = sum(f.get("impact_tokens", 0) for f in findings)
            token_str = f"~{mod_tokens:,}" if mod_tokens > 0 else "—"
            lines.append(f"| {label} | {score}/100 | {count_str} | {token_str} |")

        lines.append("")

        # 按严重程度展示 Findings
        all_findings = []
        for mod in env_data.get("modules", []):
            for f in mod.get("findings", []):
                f["_module"] = mod["module"]
                all_findings.append(f)

        for sev in SEVERITY_ORDER:
            sev_findings = [f for f in all_findings if f["severity"] == sev]
            if sev_findings:
                lines.append(f"### {SEVERITY_LABELS[sev]} 条目")
                lines.append("")
                for f in sev_findings:
                    lines.extend(_render_finding(f, compact=(sev in ("low", "info"))))
                    lines.append("")

        # 错误信息
        errors = env_data.get("errors", [])
        if errors:
            lines.append("### ⚠️ 模块扫描错误")
            for e in errors:
                lines.append(f"- **{e['module']}**: {e['error']}")
            lines.append("")

    return "\n".join(lines)


def _render_finding(finding: dict, compact: bool = False) -> list:
    """渲染单个 finding"""
    lines = []
    sev_label = SEVERITY_LABELS.get(finding["severity"], finding["severity"])
    module_label = MODULE_LABELS.get(finding.get("_module", ""), "")

    if compact:
        lines.append(f"### {finding['id']}: {finding['title']}")
        if finding.get("description"):
            # 对于多行描述，用代码块包裹
            desc = finding["description"]
            if "\n" in desc:
                lines.append("")
                lines.append("```")
                lines.append(desc)
                lines.append("```")
            else:
                lines.append(f"- {desc}")
        if finding.get("fix_suggestion"):
            lines.append(f"- **修复**: {finding['fix_suggestion']}")
        if finding.get("fix_command"):
            lines.append(f"- **命令**: `{finding['fix_command'][:120]}`")
    else:
        lines.append(f"### {finding['id']}: {finding['title']}")
        lines.append("")
        lines.append(f"- **严重程度**: {sev_label}")
        lines.append(f"- **所属模块**: {module_label}")
        if finding.get("impact_tokens"):
            lines.append(f"- **Token 影响**: ~{finding['impact_tokens']:,} tokens")
        if finding.get("description"):
            lines.append(f"- **详情**:")
            desc = finding["description"]
            if "\n" in desc:
                lines.append("")
                lines.append("```")
                lines.append(desc)
                lines.append("```")
            else:
                lines.append(f"  {desc}")
        if finding.get("fix_suggestion"):
            lines.append(f"- **修复建议**: {finding['fix_suggestion']}")
        risk = finding.get("risk_level", "")
        risk_label = {"red": "🔴 需逐项确认", "yellow": "🟡 批量确认", "green": "🟢 可自动执行"}.get(risk, "")
        if risk_label:
            lines.append(f"- **修复风险**: {risk_label}")

    return lines


def main():
    parser = argparse.ArgumentParser(description="从 JSON 生成 Markdown 体检报告")
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="输入 JSON 文件路径（orchestrator.py 的输出）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="输出 Markdown 文件路径（默认输出到 stdout）",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    report = generate_report(data)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"报告已保存到: {output_path}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
