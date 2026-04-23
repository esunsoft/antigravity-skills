# -*- coding: utf-8 -*-
"""长任务执行框架 (Long Task Executor)

支持前台/后台执行、进度追踪、超时管理、资源监控。

用法:
    python executor.py run --cmd "命令" [--timeout 3600] [--progress-pattern REGEX] [--log FILE]
    python executor.py start --cmd "命令" [--timeout 7200] [--state DIR] [--log FILE]
    python executor.py status [--state DIR]
    python executor.py tail [--state DIR] [--lines 50]
    python executor.py abort [--state DIR]
    python executor.py chunked --cmd-template "CMD {offset} {limit}" --total N [--chunk-size 500]
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


def now_iso():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def log_msg(msg, level="INFO", log_file=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    if log_file:
        try:
            with open(log_file, 'a', encoding='utf-8-sig') as f:
                f.write(line + '\n')
        except Exception:
            pass


def get_process_info(pid):
    """获取进程资源使用信息（Windows）"""
    info = {'exists': False, 'cpu_percent': 0, 'memory_mb': 0}
    try:
        result = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
            capture_output=True, encoding='gbk', errors='replace', timeout=5
        )
        if str(pid) in result.stdout:
            info['exists'] = True
            # 解析内存（tasklist 输出格式: "进程名","PID","会话名","会话#","内存使用"）
            for line in result.stdout.strip().splitlines():
                parts = line.strip('"').split('","')
                if len(parts) >= 5:
                    mem_str = parts[4].replace('"', '').replace(',', '').replace(' K', '').replace(' ', '')
                    try:
                        info['memory_mb'] = round(int(mem_str) / 1024, 1)
                    except ValueError:
                        pass
    except Exception:
        pass
    return info


def cmd_run(args):
    """前台执行长任务，实时输出日志"""
    cmd = args.cmd
    timeout = args.timeout
    log_file = args.log
    progress_pattern = re.compile(args.progress_pattern) if args.progress_pattern else None

    log_msg(f"启动任务: {cmd}", log_file=log_file)
    log_msg(f"超时: {timeout}s", log_file=log_file)

    start_time = time.time()
    progress_current = 0
    progress_total = 0

    try:
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            encoding='utf-8', errors='replace',
            bufsize=1
        )
    except Exception as e:
        log_msg(f"启动失败: {e}", "ERROR", log_file)
        return 1

    # 超时管理
    timed_out = [False]
    timer = None
    warn_timer = None

    if timeout and timeout > 0:
        def warn_timeout():
            log_msg(f"⚠️ 已使用 80% 超时时间 ({int(timeout * 0.8)}s)", "WARN", log_file)

        def do_timeout():
            timed_out[0] = True
            log_msg(f"⏰ 超时 ({timeout}s)，发送终止信号...", "WARN", log_file)
            try:
                proc.terminate()
            except Exception:
                pass
            # 给30秒优雅退出
            threading.Timer(30, lambda: _force_kill(proc)).start()

        warn_timer = threading.Timer(timeout * 0.8, warn_timeout)
        warn_timer.start()
        timer = threading.Timer(timeout, do_timeout)
        timer.start()

    # 实时读取输出
    try:
        for line in proc.stdout:
            line = line.rstrip('\n\r')
            elapsed = round(time.time() - start_time, 1)

            # 检测进度
            if progress_pattern:
                match = progress_pattern.search(line)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        progress_current = int(groups[0])
                        progress_total = int(groups[1])
                        pct = round(progress_current / progress_total * 100, 1) if progress_total > 0 else 0
                        estimated_remaining = round((elapsed / progress_current) * (progress_total - progress_current), 0) if progress_current > 0 else 0
                        log_msg(f"[PROGRESS] {pct}% ({progress_current}/{progress_total}), "
                                f"预计剩余: {int(estimated_remaining // 60)}m{int(estimated_remaining % 60)}s",
                                log_file=log_file)
                        continue
                    elif len(groups) >= 1:
                        try:
                            pct = float(groups[0])
                            log_msg(f"[PROGRESS] {pct}%", log_file=log_file)
                            continue
                        except ValueError:
                            pass

            # 普通输出
            log_msg(f"[STDOUT] {line}", log_file=log_file)

    except Exception as e:
        log_msg(f"读取输出错误: {e}", "ERROR", log_file)

    proc.wait()

    if timer:
        timer.cancel()
    if warn_timer:
        warn_timer.cancel()

    elapsed = round(time.time() - start_time, 1)
    exit_code = proc.returncode

    if timed_out[0]:
        log_msg(f"任务超时终止, 耗时: {elapsed}s", "ERROR", log_file)
    elif exit_code == 0:
        log_msg(f"✅ 任务完成, 耗时: {elapsed}s", log_file=log_file)
    else:
        log_msg(f"❌ 任务失败 (退出码: {exit_code}), 耗时: {elapsed}s", "ERROR", log_file)

    return exit_code


def cmd_start(args):
    """后台启动长任务"""
    cmd = args.cmd
    state_dir = Path(args.state)
    state_dir.mkdir(parents=True, exist_ok=True)

    log_file = args.log or str(state_dir / "output.log")

    # 启动后台进程
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(log_file, 'w', encoding='utf-8-sig') as lf:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=lf, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
    except Exception as e:
        print(f"启动失败: {e}", file=sys.stderr)
        return 1

    # 保存状态
    state = {
        'task_id': f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'command': cmd,
        'pid': proc.pid,
        'status': 'running',
        'started_at': now_iso(),
        'timeout_seconds': args.timeout,
        'log_file': str(log_path.resolve()),
        'progress': {}
    }

    state_file = state_dir / "state.json"
    with open(state_file, 'w', encoding='utf-8-sig') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"✅ 后台任务已启动")
    print(f"   PID: {proc.pid}")
    print(f"   日志: {log_file}")
    print(f"   状态: {state_file}")
    print(f"   查询: python executor.py status --state \"{state_dir}\"")

    return 0


def cmd_status(args):
    """查询后台任务状态"""
    state_dir = Path(args.state)
    state_file = state_dir / "state.json"

    if not state_file.exists():
        print(f"未找到任务状态文件: {state_file}", file=sys.stderr)
        return 1

    with open(state_file, 'r', encoding='utf-8-sig') as f:
        state = json.load(f)

    pid = state.get('pid')
    proc_info = get_process_info(pid) if pid else {'exists': False}

    # 更新状态
    if not proc_info['exists'] and state['status'] == 'running':
        state['status'] = 'completed'
        state['completed_at'] = now_iso()
        with open(state_file, 'w', encoding='utf-8-sig') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    elapsed = ''
    if state.get('started_at'):
        try:
            start = datetime.fromisoformat(state['started_at'])
            diff = datetime.now().astimezone() - start
            elapsed = f"{int(diff.total_seconds())}s"
        except Exception:
            pass

    status_icons = {'running': '🔄', 'completed': '✅', 'failed': '❌', 'aborted': '🛑'}
    icon = status_icons.get(state['status'], '❓')

    print(f"{icon} 任务状态: {state['status']}")
    print(f"   命令: {state.get('command', 'N/A')}")
    print(f"   PID: {pid} ({'运行中' if proc_info['exists'] else '已结束'})")
    print(f"   开始时间: {state.get('started_at', 'N/A')}")
    if elapsed:
        print(f"   已运行: {elapsed}")
    if proc_info.get('memory_mb'):
        print(f"   内存: {proc_info['memory_mb']} MB")
    if state.get('log_file'):
        print(f"   日志: {state['log_file']}")

    # 显示日志尾部
    log_file = state.get('log_file')
    if log_file and Path(log_file).exists():
        try:
            with open(log_file, 'r', encoding='utf-8-sig', errors='replace') as f:
                lines = f.readlines()
            tail = lines[-5:] if len(lines) > 5 else lines
            print(f"\n   最近输出:")
            for line in tail:
                print(f"   > {line.rstrip()}")
        except Exception:
            pass

    return 0


def cmd_tail(args):
    """查看后台任务输出尾部"""
    state_dir = Path(args.state)
    state_file = state_dir / "state.json"

    if not state_file.exists():
        print(f"未找到任务状态文件: {state_file}", file=sys.stderr)
        return 1

    with open(state_file, 'r', encoding='utf-8-sig') as f:
        state = json.load(f)

    log_file = state.get('log_file')
    if not log_file or not Path(log_file).exists():
        print("日志文件不存在", file=sys.stderr)
        return 1

    with open(log_file, 'r', encoding='utf-8-sig', errors='replace') as f:
        lines = f.readlines()

    n = args.lines
    tail = lines[-n:] if len(lines) > n else lines
    for line in tail:
        print(line.rstrip())

    return 0


def cmd_abort(args):
    """终止后台任务"""
    state_dir = Path(args.state)
    state_file = state_dir / "state.json"

    if not state_file.exists():
        print(f"未找到任务状态文件: {state_file}", file=sys.stderr)
        return 1

    with open(state_file, 'r', encoding='utf-8-sig') as f:
        state = json.load(f)

    pid = state.get('pid')
    if not pid:
        print("未找到 PID 信息", file=sys.stderr)
        return 1

    proc_info = get_process_info(pid)
    if not proc_info['exists']:
        print(f"进程 PID={pid} 已不存在")
        state['status'] = 'completed'
    else:
        print(f"正在终止进程 PID={pid}...")
        try:
            # Windows: 先尝试 CTRL+BREAK，再强制终止
            os.kill(pid, signal.CTRL_BREAK_EVENT)
            time.sleep(5)

            proc_info = get_process_info(pid)
            if proc_info['exists']:
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, timeout=10)
                print(f"已强制终止进程 PID={pid}")
            else:
                print(f"进程已优雅退出")

            state['status'] = 'aborted'
        except Exception as e:
            print(f"终止失败: {e}", file=sys.stderr)
            # 尝试 taskkill
            try:
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, timeout=10)
                state['status'] = 'aborted'
            except Exception:
                return 1

    state['completed_at'] = now_iso()
    with open(state_file, 'w', encoding='utf-8-sig') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"🛑 任务已终止")
    return 0


def cmd_chunked(args):
    """分片执行大任务"""
    cmd_template = args.cmd_template
    total = args.total
    chunk_size = args.chunk_size
    delay = args.delay
    log_file = args.log

    chunks = []
    offset = 0
    while offset < total:
        limit = min(chunk_size, total - offset)
        chunks.append({'offset': offset, 'limit': limit})
        offset += limit

    log_msg(f"分片执行: 总量 {total}, 每批 {chunk_size}, 共 {len(chunks)} 批")
    results = []

    for i, chunk in enumerate(chunks, 1):
        cmd = cmd_template.format(offset=chunk['offset'], limit=chunk['limit'])
        log_msg(f"[{i}/{len(chunks)}] 偏移 {chunk['offset']}, 数量 {chunk['limit']}")
        log_msg(f"  命令: {cmd}")

        start_time = time.time()
        result = subprocess.run(
            cmd, shell=True,
            capture_output=True, encoding='utf-8', errors='replace',
            timeout=args.timeout if args.timeout else None
        )
        elapsed = round(time.time() - start_time, 1)

        entry = {
            'chunk': i,
            'offset': chunk['offset'],
            'limit': chunk['limit'],
            'exit_code': result.returncode,
            'elapsed_seconds': elapsed,
            'output_tail': (result.stdout or '')[-200:]
        }
        results.append(entry)

        if result.returncode == 0:
            pct = round(min(chunk['offset'] + chunk['limit'], total) / total * 100, 1)
            log_msg(f"  ✅ 成功 ({elapsed}s) — 总进度: {pct}%")
        else:
            log_msg(f"  ❌ 失败 (退出码: {result.returncode}, {elapsed}s)", "ERROR")
            if args.stop_on_error:
                log_msg("stop-on-error 启用，终止分片执行", "ERROR")
                break

        if delay and i < len(chunks):
            log_msg(f"  等待 {delay}s...")
            time.sleep(delay)

    # 汇总
    success = sum(1 for r in results if r['exit_code'] == 0)
    failed = sum(1 for r in results if r['exit_code'] != 0)
    total_time = sum(r['elapsed_seconds'] for r in results)
    log_msg(f"分片执行完成: ✅ {success}/{len(chunks)} 成功, ❌ {failed} 失败, 总耗时 {round(total_time, 1)}s")

    if log_file:
        with open(log_file, 'w', encoding='utf-8-sig') as f:
            json.dump({
                'total': total,
                'chunk_size': chunk_size,
                'chunks_total': len(chunks),
                'success': success,
                'failed': failed,
                'total_seconds': total_time,
                'results': results
            }, f, ensure_ascii=False, indent=2)
        log_msg(f"结果已保存到 {log_file}")

    return 0 if failed == 0 else 1


def _force_kill(proc):
    """强制终止进程"""
    try:
        if proc.poll() is None:
            proc.kill()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description='长任务执行框架')
    sub = parser.add_subparsers(dest='command', help='可用命令')

    # run
    p_run = sub.add_parser('run', help='前台执行长任务')
    p_run.add_argument('--cmd', required=True, help='要执行的命令')
    p_run.add_argument('--timeout', type=int, default=3600, help='超时秒数 (默认 3600)')
    p_run.add_argument('--progress-pattern', help='进度正则表达式')
    p_run.add_argument('--log', help='日志文件路径')

    # start
    p_start = sub.add_parser('start', help='后台启动长任务')
    p_start.add_argument('--cmd', required=True, help='要执行的命令')
    p_start.add_argument('--timeout', type=int, default=7200, help='超时秒数 (默认 7200)')
    p_start.add_argument('--state', default='.tasks/executor', help='状态文件目录')
    p_start.add_argument('--log', help='日志文件路径')

    # status
    p_status = sub.add_parser('status', help='查询后台任务状态')
    p_status.add_argument('--state', default='.tasks/executor', help='状态文件目录')

    # tail
    p_tail = sub.add_parser('tail', help='查看输出尾部')
    p_tail.add_argument('--state', default='.tasks/executor', help='状态文件目录')
    p_tail.add_argument('--lines', type=int, default=50, help='显示行数 (默认 50)')

    # abort
    p_abort = sub.add_parser('abort', help='终止后台任务')
    p_abort.add_argument('--state', default='.tasks/executor', help='状态文件目录')

    # chunked
    p_chunked = sub.add_parser('chunked', help='分片执行大任务')
    p_chunked.add_argument('--cmd-template', required=True, help='命令模板，含 {offset} 和 {limit} 占位符')
    p_chunked.add_argument('--total', type=int, required=True, help='总数据量')
    p_chunked.add_argument('--chunk-size', type=int, default=500, help='每批大小 (默认 500)')
    p_chunked.add_argument('--delay', type=int, default=0, help='批次间延迟秒数')
    p_chunked.add_argument('--timeout', type=int, default=600, help='单批超时秒数 (默认 600)')
    p_chunked.add_argument('--stop-on-error', action='store_true', help='出错时停止')
    p_chunked.add_argument('--log', help='结果日志文件路径')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        'run': cmd_run,
        'start': cmd_start,
        'status': cmd_status,
        'tail': cmd_tail,
        'abort': cmd_abort,
        'chunked': cmd_chunked,
    }
    exit_code = commands[args.command](args)
    sys.exit(exit_code or 0)


if __name__ == '__main__':
    main()
