# -*- coding: utf-8 -*-
"""
check_mcp.py — MCP 配置有效性检查模块
检查规则: MCP-001 ~ MCP-003
"""

import json
from pathlib import Path
from . import (
    Finding, ModuleResult, ModuleStats, Environment,
    SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO,
    RISK_YELLOW, RISK_GREEN,
    find_antigravity_dir, read_text_safe,
)


def run(env: Environment) -> ModuleResult:
    """执行 MCP 配置检查"""
    result = ModuleResult(module="mcp")
    mcp_config = env.mcp_config

    if not mcp_config or not mcp_config.exists():
        result.stats = ModuleStats(file_count=0)
        return result

    result.stats = ModuleStats(
        total_size_kb=round(mcp_config.stat().st_size / 1024, 1),
        file_count=1,
    )

    # MCP-001: JSON 语法检查
    content = read_text_safe(mcp_config)
    _check_json_syntax(result, content, mcp_config)

    # MCP-002: 备份文件
    _check_backup(result, env.base_dir)

    # MCP-003: 配置信息
    _check_config_info(result, content)

    return result


def _check_json_syntax(result: ModuleResult, content: str, config_path: Path):
    """MCP-001: JSON 语法验证"""
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        result.add(Finding(
            id="MCP-001",
            severity=SEVERITY_MEDIUM,
            risk_level=RISK_YELLOW,
            title="MCP 配置文件 JSON 语法错误",
            description=f"文件: {config_path.name}\n错误: {e}",
            fix_suggestion="修正 JSON 语法错误。",
        ))


def _check_backup(result: ModuleResult, antigravity_dir: Path):
    """MCP-002: 检测备份文件"""
    bak_files = list(antigravity_dir.glob("mcp_config*.bak"))
    if bak_files:
        total_kb = sum(f.stat().st_size for f in bak_files) / 1024
        result.add(Finding(
            id="MCP-002",
            severity=SEVERITY_LOW,
            risk_level=RISK_GREEN,
            title=f"发现 {len(bak_files)} 个 MCP 配置备份 ({total_kb:.1f}KB)",
            description=", ".join(f.name for f in bak_files),
            auto_fixable=True,
            fix_suggestion="删除 MCP 配置备份文件。",
            fix_command="; ".join(f'Remove-Item "{f}"' for f in bak_files),
        ))


def _check_config_info(result: ModuleResult, content: str):
    """MCP-003: 已配置的 MCP server 列表"""
    try:
        config = json.loads(content)
        servers = config.get("mcpServers", config.get("servers", {}))
        if isinstance(servers, dict):
            lines = []
            for name, info in servers.items():
                cmd = info.get("command", "N/A")
                lines.append(f"  {name}: {cmd}")
            result.add(Finding(
                id="MCP-003",
                severity=SEVERITY_INFO,
                risk_level=RISK_GREEN,
                title=f"已配置 {len(servers)} 个 MCP Server",
                description="\n".join(lines) if lines else "  无 MCP Server",
            ))
        else:
            result.add(Finding(
                id="MCP-003",
                severity=SEVERITY_INFO,
                risk_level=RISK_GREEN,
                title="MCP 配置结构信息",
                description="配置格式非标准 dict 结构",
            ))
    except (json.JSONDecodeError, AttributeError):
        pass  # 已在 MCP-001 中报告
