# -*- coding: utf-8 -*-
"""
env-health-check 公共工具模块
提供 Finding 数据类、统一 JSON 输出格式和通用工具函数
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from pathlib import Path


# === 严重程度与风险等级常量 ===
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"
SEVERITY_INFO = "info"

RISK_RED = "red"        # 逐项确认
RISK_YELLOW = "yellow"  # 批量确认
RISK_GREEN = "green"    # 自动修复

# 扣分映射
SEVERITY_PENALTY = {
    SEVERITY_CRITICAL: 15,
    SEVERITY_HIGH: 10,
    SEVERITY_MEDIUM: 5,
    SEVERITY_LOW: 2,
    SEVERITY_INFO: 0,
}

# === 环境常量 ===
ENV_ANTIGRAVITY = "antigravity"
ENV_CLAUDE_CLI = "claude_cli"
ENV_CLAUDE_VS = "claude_vs"

# 模块权重（满分 100）
MODULE_WEIGHTS = {
    "config": 0.25,    # 对应原 gemini (GEMINI.md / CLAUDE.md)
    "skills": 0.30,
    "workflows": 0.10,
    "resources": 0.15,
    "knowledge": 0.05,
    "mcp": 0.05,
    "learnings": 0.10,
}


@dataclass
class Finding:
    """单个检查发现"""
    id: str
    severity: str
    risk_level: str
    title: str
    description: str
    impact_tokens: int = 0
    fix_suggestion: str = ""
    auto_fixable: bool = False
    fix_command: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class ModuleStats:
    """模块统计信息"""
    total_size_kb: float = 0.0
    estimated_tokens: int = 0
    file_count: int = 0
    extra: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class ModuleResult:
    """单个模块的检查结果"""
    module: str
    findings: List[Finding] = field(default_factory=list)
    stats: ModuleStats = field(default_factory=ModuleStats)

    def to_dict(self):
        return {
            "module": self.module,
            "findings": [f.to_dict() for f in self.findings],
            "stats": self.stats.to_dict(),
        }

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def add(self, finding: Finding):
        self.findings.append(finding)

    @property
    def score(self) -> int:
        """计算本模块得分（满分 100）"""
        penalty = sum(SEVERITY_PENALTY.get(f.severity, 0) for f in self.findings)
        return max(0, 100 - penalty)


@dataclass
class Environment:
    """工具环境定义"""
    name: str           # ENV_ANTIGRAVITY, etc.
    display_name: str
    base_dir: Path
    config_dir: Path    # 存放配置和规则的目录
    rule_file: str      # GEMINI.md or CLAUDE.md
    skills_dir: Path
    learnings_dir: Path
    workflows_dir: Optional[Path] = None
    knowledge_dir: Optional[Path] = None
    mcp_config: Optional[Path] = None


def estimate_tokens(size_bytes: int) -> int:
    """粗略估算 token 数（1 token ≈ 4 bytes 对中英混合文本）"""
    return size_bytes // 4


def get_file_size_kb(path: Path) -> float:
    """获取文件大小 (KB)"""
    try:
        return round(path.stat().st_size / 1024, 1)
    except OSError:
        return 0.0


def detect_environments() -> List[Environment]:
    """探测系统中安装的环境"""
    envs = []
    home = Path.home()

    # 1. Antigravity
    ag_base = home / ".gemini" / "antigravity"
    if ag_base.exists():
        envs.append(Environment(
            name=ENV_ANTIGRAVITY,
            display_name="Antigravity",
            base_dir=ag_base,
            config_dir=home / ".gemini",
            rule_file="GEMINI.md",
            skills_dir=ag_base / "skills",
            learnings_dir=ag_base / ".learnings",
            workflows_dir=ag_base / "workflows",
            knowledge_dir=ag_base / "knowledge",
            mcp_config=ag_base / "mcp_config.json"
        ))

    # 2. Claude Code CLI
    claude_base = home / ".claude"
    if claude_base.exists():
        envs.append(Environment(
            name=ENV_CLAUDE_CLI,
            display_name="Claude Code CLI",
            base_dir=claude_base,
            config_dir=claude_base,
            rule_file="CLAUDE.md",
            skills_dir=claude_base / "skills",
            learnings_dir=claude_base / "learnings",
            mcp_config=claude_base / "settings.json"
        ))

    # 3. Claude Code VS Extension
    appdata = os.environ.get("APPDATA")
    if appdata:
        vs_storage = Path(appdata) / "Code" / "User" / "globalStorage" / "anthropic.claude-code"
        vs_ext = Path.home() / ".vscode" / "extensions"
        has_ext = any(vs_ext.glob("anthropic.claude-code-*")) if vs_ext.exists() else False
        
        if vs_storage.exists() or has_ext:
            envs.append(Environment(
                name=ENV_CLAUDE_VS,
                display_name="Claude Code VS Plugin",
                base_dir=vs_storage if vs_storage.exists() else claude_base,
                config_dir=claude_base, # 通常共享
                rule_file="CLAUDE.md",
                skills_dir=claude_base / "skills",
                learnings_dir=vs_storage / "learnings" if vs_storage.exists() else Path("N/A")
            ))

    return envs


def find_antigravity_dir() -> Path:
    """自动定位 antigravity 目录"""
    env_dir = os.environ.get("ANTIGRAVITY_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".gemini" / "antigravity"


def find_gemini_dir() -> Path:
    """自动定位 .gemini 目录"""
    env_dir = os.environ.get("GEMINI_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".gemini"


def read_text_safe(path: Path) -> str:
    """安全读取文本文件，处理编码"""
    for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def collect_files(directory: Path, pattern: str = "*", recursive: bool = True) -> List[Path]:
    """收集目录下匹配模式的文件"""
    if not directory.exists():
        return []
    if recursive:
        return list(directory.rglob(pattern))
    return list(directory.glob(pattern))
