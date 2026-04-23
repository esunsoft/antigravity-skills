# -*- coding: utf-8 -*-
"""
review_learnings.py — .learnings/ 目录统计与审查工具

功能：
  - 统计各日志文件中 pending/resolved/promoted 条目数量
  - 列出高优先级待处理条目
  - 按区域/类别过滤

用法：
  python review_learnings.py --dir .learnings
  python review_learnings.py --dir .learnings --priority high
  python review_learnings.py --dir .learnings --area backend
"""

import argparse
import re
import sys
from pathlib import Path


def parse_entries(filepath: Path) -> list[dict]:
    """解析一个 .learnings Markdown 文件，提取所有条目。"""
    if not filepath.exists():
        return []

    text = filepath.read_text(encoding='utf-8')
    # 按 ## [TYPE-YYYYMMDD-XXX] 分割
    entry_pattern = re.compile(
        r'^## \[([A-Z]+-\d{8}-\w+)\]\s*(.*?)$',
        re.MULTILINE
    )

    entries = []
    matches = list(entry_pattern.finditer(text))

    for i, match in enumerate(matches):
        entry_id = match.group(1)
        category = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]

        # 提取字段
        status = _extract_field(body, 'Status')
        priority = _extract_field(body, 'Priority')
        area = _extract_field(body, 'Area')
        summary = _extract_section(body, 'Summary')

        entries.append({
            'id': entry_id,
            'category': category,
            'status': status or 'unknown',
            'priority': priority or 'unknown',
            'area': area or 'unknown',
            'summary': summary or '(无摘要)',
            'file': filepath.name,
        })

    return entries


def _extract_field(body: str, field_name: str) -> str | None:
    """提取 **FieldName**: value 格式的字段值。"""
    pattern = re.compile(rf'\*\*{field_name}\*\*:\s*(.+)', re.IGNORECASE)
    m = pattern.search(body)
    return m.group(1).strip() if m else None


def _extract_section(body: str, section_name: str) -> str | None:
    """提取 ### SectionName 下的第一行内容。"""
    pattern = re.compile(
        rf'^###\s+{section_name}\s*\n(.+)',
        re.MULTILINE | re.IGNORECASE
    )
    m = pattern.search(body)
    return m.group(1).strip() if m else None


def print_stats(all_entries: list[dict]) -> None:
    """打印统计摘要。"""
    if not all_entries:
        print('📊 .learnings/ 统计：无条目')
        return

    # 按状态统计
    status_counts: dict[str, int] = {}
    for e in all_entries:
        status_counts[e['status']] = status_counts.get(e['status'], 0) + 1

    # 按文件统计
    file_counts: dict[str, int] = {}
    for e in all_entries:
        file_counts[e['file']] = file_counts.get(e['file'], 0) + 1

    print('📊 .learnings/ 统计')
    print('=' * 40)
    print(f'  总条目数: {len(all_entries)}')
    print()
    print('  按状态:')
    for status, count in sorted(status_counts.items()):
        print(f'    {status}: {count}')
    print()
    print('  按文件:')
    for fname, count in sorted(file_counts.items()):
        print(f'    {fname}: {count}')


def print_pending(all_entries: list[dict], priority: str | None = None, area: str | None = None) -> None:
    """打印待处理条目，可按优先级和区域过滤。"""
    filtered = [e for e in all_entries if e['status'] == 'pending']

    if priority:
        filtered = [e for e in filtered if e['priority'] == priority]

    if area:
        filtered = [e for e in filtered if e['area'] == area]

    if not filtered:
        print('\n✅ 无待处理条目' + (f'（过滤: priority={priority}, area={area}）' if priority or area else ''))
        return

    print(f'\n⏳ 待处理条目 ({len(filtered)})')
    print('-' * 60)
    for e in filtered:
        icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(e['priority'], '⚪')
        print(f'  {icon} [{e["id"]}] ({e["priority"]}) {e["summary"]}')
        print(f'     文件: {e["file"]}  区域: {e["area"]}  类别: {e["category"]}')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='.learnings/ 目录统计与审查工具'
    )
    parser.add_argument(
        '--dir', type=str, default='.learnings',
        help='.learnings 目录路径（默认: .learnings）'
    )
    parser.add_argument(
        '--priority', type=str, choices=['critical', 'high', 'medium', 'low'],
        help='按优先级过滤待处理条目'
    )
    parser.add_argument(
        '--area', type=str,
        choices=['frontend', 'backend', 'infra', 'tests', 'docs', 'config'],
        help='按区域过滤待处理条目'
    )
    args = parser.parse_args()

    learnings_dir = Path(args.dir)
    if not learnings_dir.exists():
        print(f'❌ 目录不存在: {learnings_dir}')
        print(f'   请先创建: New-Item -ItemType Directory -Path "{learnings_dir}" -Force')
        sys.exit(1)

    # 收集所有条目
    all_entries: list[dict] = []
    for md_file in sorted(learnings_dir.glob('*.md')):
        all_entries.extend(parse_entries(md_file))

    print_stats(all_entries)
    print_pending(all_entries, priority=args.priority, area=args.area)


if __name__ == '__main__':
    main()
