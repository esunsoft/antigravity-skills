# -*- coding: utf-8 -*-
"""
模块 1：check_structure — 结构合规检查（10 条规则 S01-S10）

对应原则：P1 单一职责, P2 稳定接口, P3 可选择调用, P4 确定性, P7 可演进
"""

import re
from pathlib import Path
from typing import List

from . import (
    SkillInfo, ModuleResult, RuleFinding,
    SEVERITY_BLOCKER, SEVERITY_MAJOR, SEVERITY_MINOR, SEVERITY_NIT,
)

BACKUP_EXTENSIONS = {'.bak', '.old', '.backup', '.orig', '.tmp'}
BACKUP_PATTERNS = ['_copy', '_backup', '_old', '~']
STANDARD_SUBDIRS = {'scripts', 'references', 'assets', 'agents', 'evals', 'tests', 'eval-viewer'}


def check(skill: SkillInfo, all_skills: List[SkillInfo]) -> ModuleResult:
    """执行结构合规检查"""
    result = ModuleResult(module="structure")

    # S04: SKILL.md 文件存在 [P2] — 先检查这个，不存在则后续规则无意义
    if not skill.skill_md_path or not skill.skill_md_path.exists():
        result.add(RuleFinding(
            rule_id="S04", severity=SEVERITY_BLOCKER, principle="P2",
            title="SKILL.md 文件不存在",
            description=f"目录 {skill.path} 中没有 SKILL.md 文件",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="创建 SKILL.md 文件，至少包含 YAML frontmatter（name 和 description）",
        ))
        return result  # 无法继续后续检查

    # S01: YAML frontmatter 存在且有效 [P2]
    if not skill.frontmatter:
        result.add(RuleFinding(
            rule_id="S01", severity=SEVERITY_BLOCKER, principle="P2",
            title="YAML frontmatter 缺失或无效",
            description="SKILL.md 必须以 --- 开头的 YAML frontmatter 包含 name 和 description",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="在 SKILL.md 顶部添加：\n---\nname: skill-name\ndescription: 触发描述\n---",
        ))
    else:
        if not skill.fm_name:
            result.add(RuleFinding(
                rule_id="S01", severity=SEVERITY_BLOCKER, principle="P2",
                title="frontmatter 缺少 name 字段",
                description="YAML frontmatter 中必须包含 name 字段",
                skill_name=skill.name, skill_env=skill.env,
            ))
        if not skill.fm_description:
            result.add(RuleFinding(
                rule_id="S01", severity=SEVERITY_BLOCKER, principle="P2",
                title="frontmatter 缺少 description 字段",
                description="YAML frontmatter 中必须包含 description 字段",
                skill_name=skill.name, skill_env=skill.env,
            ))

    # S02: name 与目录名一致 [P2]
    if skill.fm_name and skill.fm_name != skill.name:
        result.add(RuleFinding(
            rule_id="S02", severity=SEVERITY_MAJOR, principle="P2",
            title=f"name 与目录名不一致：'{skill.fm_name}' vs '{skill.name}'",
            description="frontmatter 中的 name 应与 Skill 目录名一致",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion=f"将 frontmatter 中的 name 改为 '{skill.name}'，或重命名目录为 '{skill.fm_name}'",
        ))

    # S03: SKILL.md 行数 ≤ 500 [P1]
    if skill.skill_md_lines > 500:
        result.add(RuleFinding(
            rule_id="S03", severity=SEVERITY_MINOR, principle="P1",
            title=f"SKILL.md 过长：{skill.skill_md_lines} 行（建议 ≤ 500）",
            description="过长的 SKILL.md 会增加 context 消耗，建议将详细内容拆分到 references/ 目录",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="将详细指南、示例等拆分到 references/ 子目录中，SKILL.md 只保留核心指令",
        ))

    # S05: 目录结构符合约定 [P2]
    for subdir in skill.subdirs:
        if subdir not in STANDARD_SUBDIRS and not subdir.startswith('.') and not subdir.startswith('_'):
            # 非标准目录名，但不严格限制
            pass  # 仅在有脚本时检查是否放在了 scripts/ 下
    # 检查是否有 .py 文件直接放在 Skill 根目录
    root_py = [f for f in skill.py_files if f.parent == skill.path]
    if root_py:
        result.add(RuleFinding(
            rule_id="S05", severity=SEVERITY_MINOR, principle="P2",
            title=f"Python 脚本应放在 scripts/ 目录下（{len(root_py)} 个文件在根目录）",
            description=f"文件：{', '.join(f.name for f in root_py[:3])}",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="将 Python 脚本移至 scripts/ 子目录",
        ))

    # S06: 无孤立备份文件 [P7]
    backup_files = []
    for f in skill.all_files:
        if f.suffix.lower() in BACKUP_EXTENSIONS:
            backup_files.append(f.name)
        elif any(p in f.stem.lower() for p in BACKUP_PATTERNS):
            backup_files.append(f.name)
    if backup_files:
        result.add(RuleFinding(
            rule_id="S06", severity=SEVERITY_NIT, principle="P7",
            title=f"发现 {len(backup_files)} 个备份文件",
            description=f"文件：{', '.join(backup_files[:5])}",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="删除不需要的备份文件",
            auto_fixable=True,
        ))

    # S07: 脚本文件有 utf-8 编码声明 [P4]
    for py_file in skill.py_files:
        try:
            first_lines = py_file.read_text(encoding='utf-8-sig')[:200]
        except Exception:
            continue
        if 'coding' not in first_lines.split('\n')[0] and \
           (len(first_lines.split('\n')) < 2 or 'coding' not in first_lines.split('\n')[1]):
            result.add(RuleFinding(
                rule_id="S07", severity=SEVERITY_MINOR, principle="P4",
                title=f"Python 文件缺少编码声明：{py_file.name}",
                description="中文 Windows 环境下建议添加 # -*- coding: utf-8 -*-",
                skill_name=skill.name, skill_env=skill.env,
                fix_suggestion=f"在 {py_file.name} 首行添加 # -*- coding: utf-8 -*-",
            ))
            break  # 只报一次

    # S08: 无空 SKILL.md（仅 frontmatter） [P2]
    body = skill.skill_md_content
    if body.startswith("---"):
        end = re.search(r'\n---\s*\n', body[3:])
        if end:
            body_after_fm = body[end.end() + 3:].strip()
            if len(body_after_fm) < 20:
                result.add(RuleFinding(
                    rule_id="S08", severity=SEVERITY_MAJOR, principle="P2",
                    title="SKILL.md 仅有 frontmatter，缺少正文内容",
                    description="SKILL.md 除了 frontmatter 外应包含具体的指令和使用说明",
                    skill_name=skill.name, skill_env=skill.env,
                ))

    # S09: description 长度合理 [P3]
    desc_len = len(skill.fm_description)
    if 0 < desc_len < 50:
        result.add(RuleFinding(
            rule_id="S09", severity=SEVERITY_MAJOR, principle="P3",
            title=f"description 过短（{desc_len} 字符，建议 ≥ 50）",
            description="过短的描述可能导致 Skill 不被触发",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="增加触发关键词和使用场景描述",
        ))
    elif desc_len > 300:
        result.add(RuleFinding(
            rule_id="S09", severity=SEVERITY_MINOR, principle="P3",
            title=f"description 偏长（{desc_len} 字符，建议 ≤ 300）",
            description="过长的描述会增加每次对话的 context token 消耗",
            skill_name=skill.name, skill_env=skill.env,
        ))

    # S10: 无嵌套 Skill 目录 [P1]
    for sub in skill.subdirs:
        nested_skill_md = skill.path / sub / "SKILL.md"
        if nested_skill_md.exists() and sub not in STANDARD_SUBDIRS:
            result.add(RuleFinding(
                rule_id="S10", severity=SEVERITY_MINOR, principle="P1",
                title=f"检测到嵌套 Skill 目录：{sub}/",
                description=f"子目录 {sub}/ 下存在 SKILL.md，Skill 内部不应嵌套其他 Skill",
                skill_name=skill.name, skill_env=skill.env,
                fix_suggestion=f"将 {sub}/ 移至 Skill 目录外作为独立 Skill",
            ))

    return result
