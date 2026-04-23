# -*- coding: utf-8 -*-
"""跨会话任务持久化工具 (Persistent Task Tracker)

从实施计划初始化任务列表，跟踪进度，支持跨会话恢复。

用法:
    python task_tracker.py init --plan plan.md --title "任务名称" [--dir .tasks]
    python task_tracker.py status [--dir .tasks] [--task-id ID]
    python task_tracker.py update --task-id N --status STATUS [--notes "备注"] [--dir .tasks]
    python task_tracker.py resume [--dir .tasks]
    python task_tracker.py complete [--dir .tasks]
    python task_tracker.py list [--dir .tasks]
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def now_iso():
    """返回当前时间的 ISO 格式字符串"""
    return datetime.now().astimezone().isoformat(timespec='seconds')


def load_state(state_dir):
    """加载最新的任务状态文件"""
    state_dir = Path(state_dir)
    if not state_dir.exists():
        print(f"错误: 任务目录 {state_dir} 不存在。请先运行 init 命令。", file=sys.stderr)
        sys.exit(1)

    state_files = sorted(state_dir.glob("*.task.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not state_files:
        print(f"错误: 目录 {state_dir} 中没有任务文件。请先运行 init 命令。", file=sys.stderr)
        sys.exit(1)

    latest = state_files[0]
    with open(latest, 'r', encoding='utf-8-sig') as f:
        state = json.load(f)
    state['_file'] = str(latest)
    return state


def save_state(state):
    """保存任务状态到文件"""
    file_path = state.pop('_file', None)
    if not file_path:
        print("错误: 状态文件路径丢失", file=sys.stderr)
        sys.exit(1)

    state['updated_at'] = now_iso()

    # 重新计算进度
    tasks = state.get('tasks', [])
    total = len(tasks)
    completed = sum(1 for t in tasks if t['status'] == 'completed')
    in_progress = sum(1 for t in tasks if t['status'] == 'in_progress')
    failed = sum(1 for t in tasks if t['status'] == 'failed')
    skipped = sum(1 for t in tasks if t['status'] == 'skipped')
    pending = total - completed - in_progress - failed - skipped

    state['progress'] = {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'pending': pending,
        'failed': failed,
        'skipped': skipped,
        'percentage': round(completed / total * 100, 1) if total > 0 else 0
    }

    # 更新整体状态
    if completed == total:
        state['status'] = 'completed'
    elif in_progress > 0 or completed > 0:
        state['status'] = 'in_progress'
    elif failed > 0 and pending == 0 and in_progress == 0:
        state['status'] = 'failed'
    else:
        state['status'] = 'pending'

    with open(file_path, 'w', encoding='utf-8-sig') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    state['_file'] = file_path


def parse_plan_tasks(plan_path):
    """从 Markdown 实施计划中解析任务列表"""
    with open(plan_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    # 尝试多种 Markdown 任务格式
    tasks = []
    task_id = 0

    # 格式1: ### Task N: Title 或 ### 任务 N: Title
    pattern1 = re.compile(r'^###\s+(?:Task|任务)\s*(\d+)\s*[:：]\s*(.+)', re.MULTILINE)
    for match in pattern1.finditer(content):
        task_id += 1
        tasks.append({
            'id': task_id,
            'title': match.group(2).strip(),
            'status': 'pending',
            'started_at': None,
            'completed_at': None,
            'notes': '',
            'checkpoint': {}
        })

    # 格式2: - [ ] **步骤 N** 或 - [ ] Step N
    if not tasks:
        pattern2 = re.compile(r'^-\s+\[[ x]\]\s+\*?\*?(?:步骤|Step)\s*(\d+)\s*[:：]?\s*(.+?)(?:\*?\*?\s*)$', re.MULTILINE)
        for match in pattern2.finditer(content):
            task_id += 1
            tasks.append({
                'id': task_id,
                'title': match.group(2).strip().rstrip('*'),
                'status': 'pending',
                'started_at': None,
                'completed_at': None,
                'notes': '',
                'checkpoint': {}
            })

    # 格式3: 以 ## 或 ### 开头的标题行（通用回退）
    if not tasks:
        pattern3 = re.compile(r'^#{2,3}\s+(?:\d+[\.\)]\s*)?(.+)', re.MULTILINE)
        for match in pattern3.finditer(content):
            title = match.group(1).strip()
            # 跳过常见的非任务标题
            if title.lower() in ('overview', '概述', 'goal', '目标', 'architecture',
                                  '架构', 'tech stack', '技术栈', 'verification',
                                  '验证', 'summary', '总结', '---'):
                continue
            task_id += 1
            tasks.append({
                'id': task_id,
                'title': title,
                'status': 'pending',
                'started_at': None,
                'completed_at': None,
                'notes': '',
                'checkpoint': {}
            })

    return tasks


def cmd_init(args):
    """初始化任务跟踪"""
    state_dir = Path(args.dir)
    state_dir.mkdir(parents=True, exist_ok=True)

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"错误: 计划文件 {plan_path} 不存在", file=sys.stderr)
        sys.exit(1)

    tasks = parse_plan_tasks(plan_path)
    if not tasks:
        print(f"警告: 未从 {plan_path} 中解析到任务，将创建空任务列表。", file=sys.stderr)

    timestamp = datetime.now().strftime('%Y-%m-%d')
    title = args.title or plan_path.stem
    task_id = f"{timestamp}_{title.replace(' ', '-')}"

    state = {
        'task_id': task_id,
        'title': title,
        'source_plan': str(plan_path.resolve()),
        'created_at': now_iso(),
        'updated_at': now_iso(),
        'status': 'pending',
        'progress': {
            'total': len(tasks),
            'completed': 0,
            'in_progress': 0,
            'pending': len(tasks),
            'failed': 0,
            'skipped': 0,
            'percentage': 0.0
        },
        'tasks': tasks,
        'context': {
            'working_directory': str(Path.cwd()),
            'key_decisions': []
        }
    }

    file_name = f"{task_id}.task.json"
    file_path = state_dir / file_name

    with open(file_path, 'w', encoding='utf-8-sig') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"✅ 任务已初始化: {file_path}")
    print(f"   任务ID: {task_id}")
    print(f"   任务数: {len(tasks)}")
    for t in tasks:
        print(f"   [{t['id']}] {t['title']}")


def cmd_status(args):
    """显示任务进度"""
    state = load_state(args.dir)
    p = state['progress']

    print(f"📋 {state['title']}")
    print(f"   状态: {state['status']} | 进度: {p['percentage']}%")
    print(f"   ✅ {p['completed']}/{p['total']} 完成", end='')
    if p['in_progress'] > 0:
        print(f" | 🔄 {p['in_progress']} 进行中", end='')
    if p['failed'] > 0:
        print(f" | ❌ {p['failed']} 失败", end='')
    if p['skipped'] > 0:
        print(f" | ⏭ {p['skipped']} 跳过", end='')
    print(f" | ⏳ {p['pending']} 待处理")
    print()

    # 详细显示指定任务或全部
    if args.task_id:
        task = next((t for t in state['tasks'] if t['id'] == args.task_id), None)
        if task:
            _print_task_detail(task)
        else:
            print(f"错误: 未找到任务 #{args.task_id}", file=sys.stderr)
    else:
        status_icons = {'completed': '✅', 'in_progress': '🔄', 'pending': '⏳', 'failed': '❌', 'skipped': '⏭'}
        for t in state['tasks']:
            icon = status_icons.get(t['status'], '❓')
            notes = f" — {t['notes']}" if t.get('notes') else ''
            print(f"   {icon} [{t['id']}] {t['title']}{notes}")


def _print_task_detail(task):
    """打印单个任务的详细信息"""
    status_labels = {'completed': '已完成', 'in_progress': '进行中', 'pending': '待处理', 'failed': '失败', 'skipped': '已跳过'}
    print(f"   任务 #{task['id']}: {task['title']}")
    print(f"   状态: {status_labels.get(task['status'], task['status'])}")
    if task.get('started_at'):
        print(f"   开始: {task['started_at']}")
    if task.get('completed_at'):
        print(f"   完成: {task['completed_at']}")
    if task.get('notes'):
        print(f"   备注: {task['notes']}")
    if task.get('checkpoint'):
        print(f"   检查点: {json.dumps(task['checkpoint'], ensure_ascii=False)}")


def cmd_update(args):
    """更新任务状态"""
    state = load_state(args.dir)

    task = next((t for t in state['tasks'] if t['id'] == args.task_id), None)
    if not task:
        print(f"错误: 未找到任务 #{args.task_id}", file=sys.stderr)
        sys.exit(1)

    valid_statuses = ('pending', 'in_progress', 'completed', 'failed', 'skipped')
    if args.status not in valid_statuses:
        print(f"错误: 无效状态 '{args.status}'，有效值: {', '.join(valid_statuses)}", file=sys.stderr)
        sys.exit(1)

    old_status = task['status']
    task['status'] = args.status

    if args.status == 'in_progress' and not task.get('started_at'):
        task['started_at'] = now_iso()
    elif args.status in ('completed', 'failed', 'skipped'):
        task['completed_at'] = now_iso()

    if args.notes:
        task['notes'] = args.notes

    if args.checkpoint:
        try:
            task['checkpoint'] = json.loads(args.checkpoint)
        except json.JSONDecodeError:
            task['checkpoint'] = {'info': args.checkpoint}

    save_state(state)
    print(f"✅ 任务 #{args.task_id} 状态已更新: {old_status} → {args.status}")


def cmd_resume(args):
    """生成恢复上下文信息"""
    state = load_state(args.dir)
    p = state['progress']

    print("=" * 60)
    print(f"🔄 任务恢复: {state['title']}")
    print(f"   创建于: {state['created_at']}")
    print(f"   上次更新: {state['updated_at']}")
    print(f"   总体进度: {p['percentage']}% ({p['completed']}/{p['total']})")
    print("=" * 60)

    # 显示上下文
    ctx = state.get('context', {})
    if ctx.get('working_directory'):
        print(f"\n📁 工作目录: {ctx['working_directory']}")
    if ctx.get('branch'):
        print(f"🌿 分支: {ctx['branch']}")
    if ctx.get('key_decisions'):
        print(f"\n📌 关键决策:")
        for d in ctx['key_decisions']:
            print(f"   • {d}")

    # 已完成的任务
    completed = [t for t in state['tasks'] if t['status'] == 'completed']
    if completed:
        print(f"\n✅ 已完成 ({len(completed)}):")
        for t in completed:
            print(f"   [{t['id']}] {t['title']}")

    # 当前进行中的任务
    in_progress = [t for t in state['tasks'] if t['status'] == 'in_progress']
    if in_progress:
        print(f"\n🔄 进行中 (从这里继续):")
        for t in in_progress:
            print(f"   [{t['id']}] {t['title']}")
            if t.get('notes'):
                print(f"       备注: {t['notes']}")
            if t.get('checkpoint'):
                print(f"       检查点: {json.dumps(t['checkpoint'], ensure_ascii=False)}")

    # 待完成的任务
    pending = [t for t in state['tasks'] if t['status'] == 'pending']
    if pending:
        print(f"\n⏳ 待完成 ({len(pending)}):")
        for t in pending:
            print(f"   [{t['id']}] {t['title']}")

    # 失败的任务
    failed = [t for t in state['tasks'] if t['status'] == 'failed']
    if failed:
        print(f"\n❌ 失败 ({len(failed)}):")
        for t in failed:
            notes = f" — {t['notes']}" if t.get('notes') else ''
            print(f"   [{t['id']}] {t['title']}{notes}")

    # 给出建议
    print(f"\n💡 建议:")
    if in_progress:
        t = in_progress[0]
        print(f"   继续执行任务 #{t['id']}: {t['title']}")
    elif pending:
        t = pending[0]
        print(f"   开始执行任务 #{t['id']}: {t['title']}")
    elif failed:
        t = failed[0]
        print(f"   重试失败的任务 #{t['id']}: {t['title']}")
    else:
        print(f"   所有任务已完成！运行 complete 命令收尾。")

    if state.get('source_plan'):
        print(f"\n📄 源计划文件: {state['source_plan']}")


def cmd_complete(args):
    """标记整个任务为已完成"""
    state = load_state(args.dir)
    p = state['progress']

    if p['pending'] > 0 or p['in_progress'] > 0:
        print(f"⚠️ 还有 {p['pending']} 个待处理和 {p['in_progress']} 个进行中的任务。")
        print(f"   确定要标记为完成吗？失败和跳过的任务将保持原状。")
        resp = input("   输入 'yes' 确认: ").strip().lower()
        if resp != 'yes':
            print("已取消。")
            return

    state['status'] = 'completed'
    state['completed_at'] = now_iso()
    save_state(state)
    print(f"🎉 任务 '{state['title']}' 已标记为完成！")
    print(f"   完成: {p['completed']}/{p['total']}")


def cmd_list(args):
    """列出所有任务文件"""
    state_dir = Path(args.dir)
    if not state_dir.exists():
        print(f"目录 {state_dir} 不存在", file=sys.stderr)
        sys.exit(1)

    state_files = sorted(state_dir.glob("*.task.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not state_files:
        print("没有任务文件。")
        return

    for sf in state_files:
        with open(sf, 'r', encoding='utf-8-sig') as f:
            s = json.load(f)
        p = s.get('progress', {})
        status_icons = {'completed': '✅', 'in_progress': '🔄', 'pending': '⏳', 'failed': '❌'}
        icon = status_icons.get(s.get('status', ''), '❓')
        pct = p.get('percentage', 0)
        print(f"  {icon} {s.get('title', sf.stem)} — {pct}% ({p.get('completed', 0)}/{p.get('total', 0)}) [{sf.name}]")


def main():
    parser = argparse.ArgumentParser(description='跨会话任务持久化工具')
    sub = parser.add_subparsers(dest='command', help='可用命令')

    # init
    p_init = sub.add_parser('init', help='从计划文件初始化任务')
    p_init.add_argument('--plan', required=True, help='实施计划文件路径 (.md)')
    p_init.add_argument('--title', help='任务标题')
    p_init.add_argument('--dir', default='.tasks', help='状态文件存储目录')

    # status
    p_status = sub.add_parser('status', help='显示当前进度')
    p_status.add_argument('--dir', default='.tasks', help='状态文件存储目录')
    p_status.add_argument('--task-id', type=int, help='查看指定任务详情')

    # update
    p_update = sub.add_parser('update', help='更新任务状态')
    p_update.add_argument('--task-id', type=int, required=True, help='任务编号')
    p_update.add_argument('--status', required=True, help='新状态: pending/in_progress/completed/failed/skipped')
    p_update.add_argument('--notes', help='备注信息')
    p_update.add_argument('--checkpoint', help='检查点数据 (JSON 字符串或纯文本)')
    p_update.add_argument('--dir', default='.tasks', help='状态文件存储目录')

    # resume
    p_resume = sub.add_parser('resume', help='显示恢复上下文')
    p_resume.add_argument('--dir', default='.tasks', help='状态文件存储目录')

    # complete
    p_complete = sub.add_parser('complete', help='标记任务完成')
    p_complete.add_argument('--dir', default='.tasks', help='状态文件存储目录')

    # list
    p_list = sub.add_parser('list', help='列出所有任务')
    p_list.add_argument('--dir', default='.tasks', help='状态文件存储目录')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        'init': cmd_init,
        'status': cmd_status,
        'update': cmd_update,
        'resume': cmd_resume,
        'complete': cmd_complete,
        'list': cmd_list,
    }
    commands[args.command](args)


if __name__ == '__main__':
    main()
