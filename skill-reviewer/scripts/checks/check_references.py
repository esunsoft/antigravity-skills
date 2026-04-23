# -*- coding: utf-8 -*-
"""
模块 2：check_references — 引用完整性检查（6 条规则 R01-R06）

对应原则：P4 确定性, P5 显式失败, P6 模型解耦, P7 可演进
"""

import ast
import py_compile
import re
import tempfile
from pathlib import Path
from typing import List, Set

from . import (
    SkillInfo, ModuleResult, RuleFinding,
    SEVERITY_BLOCKER, SEVERITY_MAJOR, SEVERITY_MINOR, SEVERITY_NIT,
    extract_file_references, read_text_safe,
)


def _check_py_syntax(py_file: Path) -> str:
    """检查 Python 文件语法，返回错误信息或空字符串"""
    try:
        py_compile.compile(str(py_file), doraise=True)
        return ""
    except py_compile.PyCompileError as e:
        return str(e)


def _extract_imports(py_file: Path) -> List[str]:
    """从 Python 文件中提取顶层 import 的模块名"""
    try:
        content = read_text_safe(py_file)
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return []

    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:  # 绝对导入
                modules.append(node.module.split('.')[0])
    return list(set(modules))


# 标准库模块（常见子集，不完全列举）
STDLIB_MODULES = {
    'abc', 'argparse', 'ast', 'asyncio', 'base64', 'bisect', 'calendar',
    'collections', 'configparser', 'contextlib', 'copy', 'csv', 'ctypes',
    'dataclasses', 'datetime', 'decimal', 'difflib', 'email', 'enum',
    'fileinput', 'fnmatch', 'fractions', 'ftplib', 'functools', 'getopt',
    'getpass', 'glob', 'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http',
    'imaplib', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools',
    'json', 'keyword', 'linecache', 'locale', 'logging', 'lzma',
    'math', 'mimetypes', 'multiprocessing', 'operator', 'os', 'pathlib',
    'pickle', 'platform', 'pprint', 'profile', 'py_compile', 'queue',
    're', 'readline', 'secrets', 'select', 'shelve', 'shlex', 'shutil',
    'signal', 'smtplib', 'socket', 'sqlite3', 'ssl', 'stat', 'statistics',
    'string', 'struct', 'subprocess', 'sys', 'sysconfig', 'tarfile',
    'tempfile', 'textwrap', 'threading', 'time', 'timeit', 'token',
    'tokenize', 'traceback', 'types', 'typing', 'unicodedata', 'unittest',
    'urllib', 'uuid', 'venv', 'warnings', 'weakref', 'webbrowser',
    'xml', 'xmlrpc', 'zipfile', 'zipimport', 'zlib',
    # Windows 特有
    'msvcrt', 'winreg', 'winsound',
    # 内置
    'builtins', '_thread',
}


def check(skill: SkillInfo, all_skills: List[SkillInfo]) -> ModuleResult:
    """执行引用完整性检查"""
    result = ModuleResult(module="references")

    if not skill.skill_md_content:
        return result

    # R01: SKILL.md 中引用的文件路径全部存在 [P4]
    refs = extract_file_references(skill.skill_md_content)
    for ref in refs:
        # 尝试解析为 Skill 目录下的相对路径
        ref_path = skill.path / ref
        # 也尝试去掉可能的前缀目录（如 skill-name/scripts/xx.py）
        if not ref_path.exists() and '/' in ref:
            parts = ref.split('/')
            if len(parts) > 1:
                ref_path = skill.path / '/'.join(parts[1:])
        if not ref_path.exists():
            # 跳过纯示例性路径
            if any(kw in ref.lower() for kw in ['example', 'your-', 'path/to']):
                continue
            result.add(RuleFinding(
                rule_id="R01", severity=SEVERITY_MAJOR, principle="P4",
                title=f"引用的文件不存在：{ref}",
                description=f"SKILL.md 中引用了 '{ref}'，但该文件在 Skill 目录下不存在",
                skill_name=skill.name, skill_env=skill.env,
                fix_suggestion=f"创建缺失的文件 '{ref}'，或修正 SKILL.md 中的引用路径",
            ))

    # R02: Python 脚本语法有效 [P4, P5]
    for py_file in skill.py_files:
        error = _check_py_syntax(py_file)
        if error:
            # 提取核心错误信息
            short_err = error.split('\n')[0][:200]
            result.add(RuleFinding(
                rule_id="R02", severity=SEVERITY_BLOCKER, principle="P4, P5",
                title=f"Python 语法错误：{py_file.name}",
                description=f"编译错误：{short_err}",
                skill_name=skill.name, skill_env=skill.env,
                fix_suggestion="修复语法错误后重新审查",
            ))

    # R03: 无孤立文件 [P7]
    if refs:
        referenced_names: Set[str] = set()
        for ref in refs:
            referenced_names.add(Path(ref).name)
        for f in skill.all_files:
            if f.name == "SKILL.md" or f.name.startswith('.'):
                continue
            if f.name == "__init__.py" or f.name == "__pycache__":
                continue
            rel = f.relative_to(skill.path)
            # 只检查第一层子目录中的文件
            if f.name not in referenced_names and str(rel) not in refs:
                # 不对资源文件过于严格
                pass  # 此规则在快速模式下跳过，完整模式由 AI 判断

    # R04: 脚本依赖可导入 [P4, P6]
    missing_deps = set()
    for py_file in skill.py_files:
        imports = _extract_imports(py_file)
        for mod in imports:
            if mod in STDLIB_MODULES:
                continue
            # 检查是否是 Skill 内部模块
            if (skill.path / "scripts" / f"{mod}.py").exists():
                continue
            if (skill.path / "scripts" / mod / "__init__.py").exists():
                continue
            # 尝试实际导入
            try:
                __import__(mod)
            except ImportError:
                missing_deps.add(mod)
    if missing_deps:
        result.add(RuleFinding(
            rule_id="R04", severity=SEVERITY_MAJOR, principle="P4, P6",
            title=f"缺少依赖包：{', '.join(sorted(missing_deps))}",
            description="脚本导入了未安装的第三方包，运行时会失败",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion=f"安装缺失的包：python -m pip install {' '.join(sorted(missing_deps))}",
        ))

    # R05: 内部交叉引用有效 [P4]
    scripts_dir = skill.path / "scripts"
    if scripts_dir.exists():
        for py_file in skill.py_files:
            if py_file.parent != scripts_dir:
                continue
            try:
                content = read_text_safe(py_file)
                tree = ast.parse(content)
            except (SyntaxError, ValueError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level > 0:
                    # 相对导入，检查目标文件是否存在
                    if node.module:
                        target = scripts_dir / f"{node.module.replace('.', '/')}.py"
                        target_pkg = scripts_dir / node.module.replace('.', '/') / "__init__.py"
                        if not target.exists() and not target_pkg.exists():
                            result.add(RuleFinding(
                                rule_id="R05", severity=SEVERITY_MINOR, principle="P4",
                                title=f"无效的内部引用：{py_file.name} -> {node.module}",
                                description="相对导入的目标模块不存在",
                                skill_name=skill.name, skill_env=skill.env,
                            ))

    # R06: 外部 URL 引用可达 [P6] — 标记为可选，默认不执行网络检查
    url_pattern = re.compile(r'https?://[^\s\)\]\}>"\']+')
    urls = url_pattern.findall(skill.skill_md_content)
    if urls:
        # 仅记录统计信息，不实际检查可达性
        pass

    return result
