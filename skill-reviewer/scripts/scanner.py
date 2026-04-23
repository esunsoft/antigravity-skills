# -*- coding: utf-8 -*-
"""
skill-reviewer 环境发现与 Skill 扫描器

自动探测 Antigravity 和 Claude Code CLI 两个环境的 Skills 目录，
递归扫描含 SKILL.md 的目录，解析元数据，输出 SkillInfo 列表。
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# 将 scripts 目录加入 sys.path 以支持相对导入
sys.path.insert(0, str(Path(__file__).parent))

from checks import (
    SkillInfo, ENV_ANTIGRAVITY, ENV_CLAUDE, ENV_PATHS,
    read_text_safe, parse_yaml_frontmatter
)


def scan_skill_dir(skill_dir: Path, env: str, is_archived: bool = False) -> Optional[SkillInfo]:
    """扫描单个 Skill 目录，返回 SkillInfo 或 None"""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None

    content = read_text_safe(skill_md)
    frontmatter = parse_yaml_frontmatter(content)

    # 收集文件信息
    all_files = [f for f in skill_dir.rglob("*") if f.is_file()]
    py_files = [f for f in all_files if f.suffix == ".py"]
    md_files = [f for f in all_files if f.suffix == ".md"]

    # 直接子目录
    subdirs = [d.name for d in skill_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

    return SkillInfo(
        name=skill_dir.name,
        path=skill_dir,
        env=env,
        is_archived=is_archived,
        skill_md_path=skill_md,
        skill_md_content=content,
        skill_md_lines=len(content.splitlines()),
        frontmatter=frontmatter,
        fm_name=frontmatter.get("name", ""),
        fm_description=frontmatter.get("description", ""),
        all_files=all_files,
        py_files=py_files,
        md_files=md_files,
        subdirs=subdirs,
    )


def scan_environment(env: str, env_path: Path) -> List[SkillInfo]:
    """扫描单个环境下的所有 Skills"""
    skills = []
    if not env_path.exists():
        return skills

    for item in sorted(env_path.iterdir()):
        if not item.is_dir():
            continue
        if item.name.startswith('.'):
            continue

        # _archived 目录下的 Skill 递归处理
        if item.name == "_archived":
            for archived_item in sorted(item.iterdir()):
                if archived_item.is_dir():
                    info = scan_skill_dir(archived_item, env, is_archived=True)
                    if info:
                        skills.append(info)
            continue

        info = scan_skill_dir(item, env)
        if info:
            skills.append(info)

    return skills


def scan_all(envs: Optional[List[str]] = None, custom_path: Optional[str] = None) -> List[SkillInfo]:
    """扫描所有环境（或指定环境）的 Skills

    Args:
        envs: 要扫描的环境列表，None 表示全部
        custom_path: 自定义路径，如果指定则只扫描该路径
    """
    all_skills = []

    # 自定义路径模式：直接扫描指定目录
    if custom_path:
        custom_dir = Path(custom_path).resolve()
        if not custom_dir.exists():
            return []

        # 判断是单个 Skill 目录还是包含多个 Skills 的父目录
        if (custom_dir / "SKILL.md").exists():
            # 单个 Skill
            info = scan_skill_dir(custom_dir, "custom")
            if info:
                all_skills.append(info)
        else:
            # 多个 Skills 的父目录
            all_skills.extend(scan_environment("custom", custom_dir))

        return all_skills

    # 标准环境扫描
    target_envs = envs or [ENV_ANTIGRAVITY, ENV_CLAUDE]

    for env_name in target_envs:
        env_path = ENV_PATHS.get(env_name)
        if env_path:
            all_skills.extend(scan_environment(env_name, env_path))

    return all_skills


def main():
    parser = argparse.ArgumentParser(description="扫描 Skill 目录并输出元数据")
    parser.add_argument("--env", choices=[ENV_ANTIGRAVITY, ENV_CLAUDE],
                        help="仅扫描指定环境")
    parser.add_argument("--path", type=str, help="自定义 Skill 路径（单个 Skill 或包含多个 Skills 的目录）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--active-only", action="store_true", help="仅显示活跃 Skill")
    args = parser.parse_args()

    envs = [args.env] if args.env else None
    skills = scan_all(envs, custom_path=args.path)

    if args.active_only:
        skills = [s for s in skills if not s.is_archived]

    if args.json:
        data = [s.to_dict() for s in skills]
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        # 按环境分组输出
        for env_name in [ENV_ANTIGRAVITY, ENV_CLAUDE]:
            env_skills = [s for s in skills if s.env == env_name]
            if not env_skills:
                continue
            active = [s for s in env_skills if not s.is_archived]
            archived = [s for s in env_skills if s.is_archived]
            env_path = ENV_PATHS.get(env_name, "?")
            print(f"\n{'='*60}")
            print(f"Environment: {env_name} ({env_path})")
            print(f"  Active: {len(active)} | Archived: {len(archived)}")
            print(f"{'='*60}")
            for s in active:
                py_count = len(s.py_files)
                print(f"  [{s.fm_name or s.name}] {s.skill_md_lines} lines"
                      f" | {len(s.all_files)} files"
                      f" | {py_count} py"
                      f" | desc={len(s.fm_description)} chars")


if __name__ == "__main__":
    main()
