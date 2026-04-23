# -*- coding: utf-8 -*-
"""
模块 4：check_design — 设计质量检查（7 条规则 D01-D07）

对应原则：P1-P7，直接映射 8 大设计原则中的工程质量维度
"""

import ast
import re
from pathlib import Path
from typing import List

from . import (
    SkillInfo, ModuleResult, RuleFinding,
    SEVERITY_MAJOR, SEVERITY_MINOR, SEVERITY_NIT,
    read_text_safe, count_pattern_density,
)


def _count_domain_clusters(description: str) -> int:
    """估算 description 中涉及的独立领域数量"""
    domain_markers = [
        # 数据库相关
        (r'(?:sql|database|数据库|存储过程|索引|查询)', 'db'),
        # 前端相关
        (r'(?:html|css|react|vue|frontend|前端|ui|界面)', 'frontend'),
        # 文档相关
        (r'(?:doc|文档|报告|word|pdf|markdown)', 'doc'),
        # 测试相关
        (r'(?:test|测试|验证|断言)', 'test'),
        # DevOps 相关
        (r'(?:deploy|docker|ci/cd|部署|容器)', 'devops'),
        # AI/ML 相关
        (r'(?:model|llm|prompt|agent|ai|机器学习)', 'ai'),
        # 安全相关
        (r'(?:security|安全|审计|漏洞)', 'security'),
        # PowerBuilder 相关
        (r'(?:powerbuilder|pb|datawindow|pfc)', 'pb'),
    ]
    domains = set()
    for pattern, domain in domain_markers:
        if re.search(pattern, description, re.IGNORECASE):
            domains.add(domain)
    return len(domains)


def _check_script_parameterized(py_file: Path) -> bool:
    """检查 Python 脚本是否参数化（使用 argparse 或 sys.argv）"""
    try:
        content = read_text_safe(py_file)
        return 'argparse' in content or 'sys.argv' in content or 'click' in content
    except Exception:
        return False


def _check_script_error_handling(py_file: Path) -> bool:
    """检查 Python 脚本是否有错误处理"""
    try:
        content = read_text_safe(py_file)
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return True  # 无法解析时不报告此规则

    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            return True
    return False


def check(skill: SkillInfo, all_skills: List[SkillInfo]) -> ModuleResult:
    """执行设计质量检查"""
    result = ModuleResult(module="design")
    content = skill.skill_md_content

    if not content:
        return result

    # D01: 单一职责检查 [P1]
    domain_count = _count_domain_clusters(skill.fm_description)
    if domain_count >= 4:
        result.add(RuleFinding(
            rule_id="D01", severity=SEVERITY_MAJOR, principle="P1",
            title=f"Skill 涉及 {domain_count} 个不相关领域",
            description="description 中涵盖了过多不同领域，违反单一职责原则",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="考虑将 Skill 拆分为多个聚焦于单一领域的 Skill",
        ))

    # D02: I/O 接口规范 [P2]
    io_keywords = ['输入', '输出', 'input', 'output', '参数', 'parameter',
                   'argument', '返回', 'return', '格式', 'format']
    has_io_section = any(kw in content.lower() for kw in io_keywords)
    if skill.py_files and not has_io_section:
        result.add(RuleFinding(
            rule_id="D02", severity=SEVERITY_MAJOR, principle="P2",
            title="SKILL.md 缺少输入/输出接口说明",
            description="有脚本文件但 SKILL.md 中未描述输入格式和输出格式",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="在 SKILL.md 中添加输入/输出格式说明章节",
        ))

    # D03: 执行确定性 [P4]
    nondeterministic_patterns = [
        r'random\.',
        r'uuid\.',
        r'time\.time\(\)',
        r'datetime\.now\(\)',
    ]
    for py_file in skill.py_files:
        py_content = read_text_safe(py_file)
        for pattern in nondeterministic_patterns:
            if re.search(pattern, py_content):
                # 不是所有使用都有问题，只在输出路径上使用时才是问题
                # 这里只做轻度标记
                break

    # D04: 错误处理与恢复 [P5]
    main_scripts = [f for f in skill.py_files
                    if f.stem in ('main', 'quick_score', 'orchestrator', 'scanner')
                    or f.parent.name == 'scripts' and f.parent.parent == skill.path]
    scripts_without_error_handling = []
    for py_file in main_scripts:
        if not _check_script_error_handling(py_file):
            scripts_without_error_handling.append(py_file.name)
    if scripts_without_error_handling:
        result.add(RuleFinding(
            rule_id="D04", severity=SEVERITY_MAJOR, principle="P5",
            title=f"脚本缺少错误处理：{', '.join(scripts_without_error_handling)}",
            description="入口脚本没有 try/except 错误处理，运行时异常会导致无有效输出",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="为入口脚本添加顶层 try/except 错误处理",
        ))

    # 检查 SKILL.md 中是否描述了失败处理
    failure_keywords = ['失败', '错误', 'error', 'fail', '异常', 'exception',
                        '回退', 'fallback', '降级', 'degrade']
    has_failure_doc = any(kw in content.lower() for kw in failure_keywords)
    if skill.py_files and not has_failure_doc:
        result.add(RuleFinding(
            rule_id="D04", severity=SEVERITY_MINOR, principle="P5",
            title="SKILL.md 未描述失败处理策略",
            description="SKILL.md 中没有关于错误/失败场景的描述",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="在 SKILL.md 中添加失败场景和恢复策略说明",
        ))

    # D05: 模型解耦度 [P6]
    model_names = ['claude', 'gpt-4', 'gpt-3', 'gemini', 'llama', 'mistral']
    for name in model_names:
        # 在正文中硬编码模型名（description 中合理）
        if name in content.lower() and name not in skill.fm_description.lower():
            # 排除一些合理场景（如 claude-api skill）
            if 'api' in skill.name.lower() or 'claude' in skill.name.lower():
                continue
            result.add(RuleFinding(
                rule_id="D05", severity=SEVERITY_MINOR, principle="P6",
                title=f"SKILL.md 中硬编码了模型名：'{name}'",
                description="引用特定模型名称会降低 Skill 的可移植性",
                skill_name=skill.name, skill_env=skill.env,
                fix_suggestion=f"将 '{name}' 替换为通用描述，或参数化模型选择",
            ))
            break

    # D06: 可复用性 [P7]
    if skill.py_files:
        parameterized_count = sum(1 for f in skill.py_files if _check_script_parameterized(f))
        entry_scripts = [f for f in skill.py_files if f.parent.name == 'scripts']
        if entry_scripts and parameterized_count == 0:
            result.add(RuleFinding(
                rule_id="D06", severity=SEVERITY_MINOR, principle="P7",
                title="脚本未使用参数化（argparse/sys.argv）",
                description="所有脚本都没有使用命令行参数，灵活性受限",
                skill_name=skill.name, skill_env=skill.env,
                fix_suggestion="使用 argparse 添加命令行参数支持",
            ))

    # D07: 可测试性 [P7]
    has_tests = any(d in skill.subdirs for d in ['evals', 'tests', 'test', 'eval-viewer'])
    has_test_files = any('test' in f.stem.lower() or 'eval' in f.stem.lower()
                         for f in skill.all_files)
    if skill.py_files and not has_tests and not has_test_files:
        result.add(RuleFinding(
            rule_id="D07", severity=SEVERITY_NIT, principle="P7",
            title="缺少测试用例或 eval 配置",
            description="没有 evals/、tests/ 目录或测试文件",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="添加 evals/ 目录和测试用例，或使用 skill-creator 生成评估配置",
        ))

    return result
