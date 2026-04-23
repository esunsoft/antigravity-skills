# -*- coding: utf-8 -*-
"""
skill-reviewer 公共数据模型与工具函数

定义 SkillInfo（单个 Skill 的元数据）、RuleFinding（单条发现）、
ModuleResult（模块结果）以及通用工具函数。
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from pathlib import Path


# === 严重级别常量 ===
SEVERITY_BLOCKER = "Blocker"
SEVERITY_MAJOR = "Major"
SEVERITY_MINOR = "Minor"
SEVERITY_NIT = "Nit"

# 扣分映射（维度满分 100）
SEVERITY_PENALTY = {
    SEVERITY_BLOCKER: 100,  # 该维度直接归零
    SEVERITY_MAJOR: 20,
    SEVERITY_MINOR: 8,
    SEVERITY_NIT: 2,
}

# 维度权重
DIMENSION_WEIGHTS = {
    "structure":  0.15,
    "references": 0.15,
    "triggers":   0.10,
    "design":     0.20,
    "security":   0.25,
    "content":    0.15,
}

# crossenv 不计入单 Skill 评分（它是生态级指标）

# 等级映射
GRADE_THRESHOLDS = [
    (90, "A", "\u2b50"),
    (75, "B", "\u2705"),
    (60, "C", "\u26a0\ufe0f"),
    (40, "D", "\U0001f536"),
    (0,  "F", "\u274c"),
]


def score_to_grade(score: int) -> tuple:
    """将分数转换为 (等级字母, emoji)"""
    for threshold, letter, emoji in GRADE_THRESHOLDS:
        if score >= threshold:
            return letter, emoji
    return "F", "\u274c"


# === 环境常量 ===
ENV_ANTIGRAVITY = "antigravity"
ENV_CLAUDE = "claude"

ENV_PATHS = {
    ENV_ANTIGRAVITY: Path.home() / ".gemini" / "antigravity" / "skills",
    ENV_CLAUDE: Path.home() / ".claude" / "skills",
}


@dataclass
class SkillInfo:
    """单个 Skill 的元数据"""
    name: str                       # 目录名
    path: Path                      # Skill 目录绝对路径
    env: str                        # 所属环境 (antigravity/claude)
    is_archived: bool = False       # 是否在 _archived/ 下
    # 从 SKILL.md 解析
    skill_md_path: Optional[Path] = None
    skill_md_content: str = ""
    skill_md_lines: int = 0
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    fm_name: str = ""               # frontmatter 中的 name
    fm_description: str = ""        # frontmatter 中的 description
    # 文件清单
    all_files: List[Path] = field(default_factory=list)
    py_files: List[Path] = field(default_factory=list)
    md_files: List[Path] = field(default_factory=list)
    subdirs: List[str] = field(default_factory=list)  # 直接子目录名

    def to_dict(self) -> dict:
        """序列化为可 JSON 化的字典"""
        return {
            "name": self.name,
            "path": str(self.path),
            "env": self.env,
            "is_archived": self.is_archived,
            "fm_name": self.fm_name,
            "fm_description": self.fm_description,
            "skill_md_lines": self.skill_md_lines,
            "file_count": len(self.all_files),
            "py_file_count": len(self.py_files),
            "subdirs": self.subdirs,
        }


@dataclass
class RuleFinding:
    """单条检查发现"""
    rule_id: str            # 如 S01, R02, SEC03
    severity: str           # Blocker/Major/Minor/Nit
    principle: str          # 对应原则 如 "P1" 或 "P1, P3"
    title: str              # 一句话标题
    description: str        # 详细描述
    skill_name: str = ""    # 涉及的 Skill 名称
    skill_env: str = ""     # 涉及的环境
    fix_suggestion: str = ""  # 修复建议
    auto_fixable: bool = False
    fix_command: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModuleResult:
    """单个检查模块的结果"""
    module: str             # 模块名 如 "structure"
    findings: List[RuleFinding] = field(default_factory=list)

    def add(self, finding: RuleFinding):
        self.findings.append(finding)

    @property
    def dimension_score(self) -> int:
        """计算本模块维度得分（满分 100）"""
        if not self.findings:
            return 100
        # Blocker 直接归零
        if any(f.severity == SEVERITY_BLOCKER for f in self.findings):
            return 0
        penalty = sum(SEVERITY_PENALTY.get(f.severity, 0) for f in self.findings)
        return max(0, 100 - penalty)

    @property
    def blocker_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SEVERITY_BLOCKER)

    @property
    def major_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SEVERITY_MAJOR)

    @property
    def minor_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SEVERITY_MINOR)

    @property
    def nit_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == SEVERITY_NIT)

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "dimension_score": self.dimension_score,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class SkillReviewResult:
    """单个 Skill 的完整审查结果"""
    skill: SkillInfo
    modules: Dict[str, ModuleResult] = field(default_factory=dict)

    @property
    def total_score(self) -> int:
        """加权总分"""
        total = 0.0
        for dim_name, weight in DIMENSION_WEIGHTS.items():
            mr = self.modules.get(dim_name)
            dim_score = mr.dimension_score if mr else 100
            total += dim_score * weight
        # 安全 Blocker 惩罚：直接降至 F
        sec = self.modules.get("security")
        if sec and sec.blocker_count > 0:
            return min(int(total), 39)
        return int(total)

    @property
    def grade(self) -> tuple:
        return score_to_grade(self.total_score)

    @property
    def all_findings(self) -> List[RuleFinding]:
        result = []
        for mr in self.modules.values():
            result.extend(mr.findings)
        return result

    def to_dict(self) -> dict:
        letter, emoji = self.grade
        return {
            "skill": self.skill.to_dict(),
            "total_score": self.total_score,
            "grade": letter,
            "modules": {k: v.to_dict() for k, v in self.modules.items()},
        }


# === 工具函数 ===

def read_text_safe(path: Path) -> str:
    """安全读取文本文件，自动处理编码"""
    for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def parse_yaml_frontmatter(content: str) -> Dict[str, Any]:
    """解析 SKILL.md 的 YAML frontmatter（轻量实现，不依赖 pyyaml）"""
    if not content.startswith("---"):
        return {}
    end_match = re.search(r'\n---\s*\n', content[3:])
    if not end_match:
        return {}
    fm_text = content[3:end_match.start() + 3]
    result = {}
    for line in fm_text.strip().split('\n'):
        line = line.strip()
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                result[key] = value
    return result


def _strip_code_blocks(content: str) -> str:
    """剥离 Markdown 围栏代码块（```...```），返回剩余文本"""
    return re.sub(r'```[^\n]*\n.*?```', '', content, flags=re.DOTALL)


def extract_file_references(content: str) -> List[str]:
    """从 SKILL.md 内容中提取被引用的文件路径

    仅从非代码块区域提取引用，避免将命令示例、URL 等误识别为文件引用。
    """
    # 先剥离代码块，避免匹配示例代码中的命令
    text = _strip_code_blocks(content)

    refs = []
    # 匹配反引号中的路径 如 `scripts/xxx.py`
    refs.extend(re.findall(r'`([^`\n]*(?:scripts|references|assets|agents)/[^`\n]+)`', text))
    # 匹配目录结构中的文件 如 ├── xxx.py
    refs.extend(re.findall(r'[├└─│\s]+(\S+\.(?:py|md|json|yaml|yml|txt))', text))
    # 去重并清理
    cleaned = []
    for ref in refs:
        ref = ref.strip().strip('"').strip("'")
        if not ref:
            continue
        if '<' in ref or '>' in ref:
            continue
        if ref.startswith(('http://', 'https://')):
            continue
        if '$' in ref:
            continue
        if re.search(r'[\u4e00-\u9fff]', ref):
            continue
        if '\n' in ref:
            continue
        if ref.startswith('`') or ref.endswith('`'):
            continue
        if ref in cleaned:
            continue
        cleaned.append(ref)
    return cleaned


def count_pattern_density(content: str, patterns: List[str]) -> float:
    """计算特定模式在文本中的密度（每 1000 字符出现次数）"""
    if not content:
        return 0.0
    total = sum(len(re.findall(p, content, re.IGNORECASE)) for p in patterns)
    return (total / len(content)) * 1000
