# -*- coding: utf-8 -*-
"""任务调度与自动重试工具 (Task Scheduler)

支持自动重试、批量执行、后台监控和定时执行。

用法:
    python scheduler.py retry --cmd "命令" [--max-retries 3] [--base-delay 5] [--timeout 600]
    python scheduler.py batch --commands commands.json [--on-error continue|stop]
    python scheduler.py watch --pid PID [--interval 30] [--timeout 3600]
    python scheduler.py schedule --cmd "命令" --interval 60 [--count 10] [--until-success]
"""

import argparse
import json
import os
import random
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


def now_iso():
    """返回当前时间的 ISO 格式字符串"""
    return datetime.now().astimezone().isoformat(timespec='seconds')


def log_msg(msg, level="INFO"):
    """输出带时间戳的日志"""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] [{level}] {msg}", flush=True)


def run_with_timeout(cmd, timeout_seconds, encoding='utf-8'):
    """执行命令并带超时控制（Windows 兼容）"""
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding=encoding,
            errors='replace'
        )

        timer = None
        timed_out = [False]

        if timeout_seconds and timeout_seconds > 0:
            def kill_proc():
                timed_out[0] = True
                try:
                    proc.terminate()
                    time.sleep(5)
                    if proc.poll() is None:
                        proc.kill()
                except Exception:
                    pass

            timer = threading.Timer(timeout_seconds, kill_proc)
            timer.start()

        output, _ = proc.communicate()

        if timer:
            timer.cancel()

        return {
            'exit_code': proc.returncode,
            'output': output or '',
            'timed_out': timed_out[0]
        }
    except Exception as e:
        return {
            'exit_code': -1,
            'output': str(e),
            'timed_out': False
        }


def cmd_retry(args):
    """自动重试执行命令"""
    max_retries = args.max_retries
    base_delay = args.base_delay
    timeout = args.timeout
    cmd = args.cmd
    retry_on_codes = None
    if args.retry_on:
        retry_on_codes = [int(c.strip()) for c in args.retry_on.split(',')]

    log_msg(f"开始执行: {cmd}")
    log_msg(f"重试策略: 最多 {max_retries} 次, 基础延迟 {base_delay}s, 超时 {timeout}s")

    history = []
    start_time = now_iso()

    for attempt in range(1, max_retries + 2):  # +1 for initial attempt + retries
        log_msg(f"第 {attempt} 次执行...")
        attempt_start = time.time()

        result = run_with_timeout(cmd, timeout)
        elapsed = round(time.time() - attempt_start, 1)

        entry = {
            'attempt': attempt,
            'exit_code': result['exit_code'],
            'elapsed_seconds': elapsed,
            'timed_out': result['timed_out'],
            'output_tail': result['output'][-500:] if result['output'] else ''
        }
        history.append(entry)

        if result['exit_code'] == 0:
            log_msg(f"✅ 执行成功 (耗时 {elapsed}s)")
            break

        if result['timed_out']:
            log_msg(f"⏰ 执行超时 ({timeout}s)", "WARN")
        else:
            log_msg(f"❌ 执行失败 (退出码: {result['exit_code']}, 耗时 {elapsed}s)", "WARN")

        # 判断是否需要重试
        should_retry = True
        if retry_on_codes and result['exit_code'] not in retry_on_codes:
            log_msg(f"退出码 {result['exit_code']} 不在重试列表中，停止重试", "WARN")
            should_retry = False

        if attempt > max_retries or not should_retry:
            log_msg(f"已达到最大重试次数或不可重试，任务失败", "ERROR")
            break

        # 计算延迟（指数退避 + 随机抖动）
        delay = base_delay * (2 ** (attempt - 1))
        jitter = random.uniform(0, delay * 0.4)
        actual_delay = round(delay + jitter, 1)
        log_msg(f"等待 {actual_delay}s 后重试...")
        time.sleep(actual_delay)

    # 输出结果
    final = history[-1]
    report = {
        'task': cmd,
        'start_time': start_time,
        'end_time': now_iso(),
        'attempts': len(history),
        'final_status': 'success' if final['exit_code'] == 0 else ('timeout' if final['timed_out'] else 'failed'),
        'exit_code': final['exit_code'],
        'duration_seconds': sum(h['elapsed_seconds'] for h in history),
        'history': history
    }

    if args.log:
        log_path = Path(args.log)
        with open(log_path, 'w', encoding='utf-8-sig') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        log_msg(f"结果已保存到 {log_path}")

    return 0 if final['exit_code'] == 0 else 1


def cmd_batch(args):
    """批量顺序执行命令"""
    cmd_file = Path(args.commands)
    if not cmd_file.exists():
        log_msg(f"命令文件不存在: {cmd_file}", "ERROR")
        sys.exit(1)

    with open(cmd_file, 'r', encoding='utf-8-sig') as f:
        commands = json.load(f)

    on_error = args.on_error
    results = []
    completed_names = set()

    log_msg(f"开始批量执行 {len(commands)} 个命令 (on_error={on_error})")

    for i, cmd_spec in enumerate(commands, 1):
        name = cmd_spec.get('name', f'命令{i}')
        cmd = cmd_spec.get('cmd', '')
        timeout = cmd_spec.get('timeout', 600)
        retry_count = cmd_spec.get('retry', 0)
        depends_on = cmd_spec.get('depends_on')

        # 检查依赖
        if depends_on and depends_on not in completed_names:
            log_msg(f"⏭ [{i}/{len(commands)}] {name} — 跳过（依赖 '{depends_on}' 未完成）", "WARN")
            results.append({'name': name, 'status': 'skipped', 'reason': f'依赖 {depends_on} 未完成'})
            continue

        log_msg(f"🔄 [{i}/{len(commands)}] {name}")

        best_result = None
        for attempt in range(1, retry_count + 2):
            if attempt > 1:
                delay = 5 * (2 ** (attempt - 2))
                log_msg(f"  重试 {attempt - 1}/{retry_count}, 等待 {delay}s...")
                time.sleep(delay)

            result = run_with_timeout(cmd, timeout)
            best_result = result

            if result['exit_code'] == 0:
                break

        entry = {
            'name': name,
            'cmd': cmd,
            'exit_code': best_result['exit_code'],
            'status': 'success' if best_result['exit_code'] == 0 else 'failed',
            'timed_out': best_result['timed_out'],
            'attempts': min(retry_count + 1, retry_count + 1),
            'output_tail': best_result['output'][-200:] if best_result['output'] else ''
        }
        results.append(entry)

        if best_result['exit_code'] == 0:
            completed_names.add(name)
            log_msg(f"  ✅ {name} 成功")
        else:
            log_msg(f"  ❌ {name} 失败 (退出码: {best_result['exit_code']})", "ERROR")
            if on_error == 'stop':
                log_msg("on_error=stop, 终止批量执行", "ERROR")
                break

    # 汇总
    success = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'failed')
    skipped = sum(1 for r in results if r['status'] == 'skipped')
    log_msg(f"批量执行完成: ✅ {success} 成功, ❌ {failed} 失败, ⏭ {skipped} 跳过")

    if args.log:
        log_path = Path(args.log)
        with open(log_path, 'w', encoding='utf-8-sig') as f:
            json.dump({'results': results, 'summary': {'success': success, 'failed': failed, 'skipped': skipped}},
                      f, ensure_ascii=False, indent=2)
        log_msg(f"结果已保存到 {log_path}")

    return 0 if failed == 0 else 1


def cmd_watch(args):
    """监控后台进程"""
    pid = args.pid
    interval = args.interval
    timeout = args.timeout
    start_time = time.time()

    log_msg(f"开始监控进程 PID={pid}, 间隔={interval}s, 超时={timeout}s")

    while True:
        elapsed = time.time() - start_time

        # 检查进程是否存在
        try:
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                capture_output=True, encoding='gbk', errors='replace', timeout=10
            )
            proc_exists = str(pid) in result.stdout
        except Exception:
            proc_exists = False

        if not proc_exists:
            log_msg(f"进程 PID={pid} 已结束 (运行 {round(elapsed)}s)")
            break

        # 获取进程信息
        try:
            info_result = subprocess.run(
                ['wmic', 'process', 'where', f'ProcessId={pid}', 'get',
                 'WorkingSetSize,KernelModeTime,UserModeTime', '/format:csv'],
                capture_output=True, encoding='gbk', errors='replace', timeout=10
            )
            log_msg(f"进程 PID={pid} 运行中 ({round(elapsed)}s)")
        except Exception:
            log_msg(f"进程 PID={pid} 运行中 ({round(elapsed)}s)")

        # 超时检查
        if timeout and elapsed >= timeout:
            log_msg(f"监控超时 ({timeout}s)，停止监控", "WARN")
            break

        time.sleep(interval)

    log_msg("监控结束")


def cmd_schedule(args):
    """定时执行命令"""
    cmd = args.cmd
    interval = args.interval
    max_count = args.count
    until_success = args.until_success

    log_msg(f"定时执行: {cmd}")
    log_msg(f"间隔: {interval}s, 最大次数: {max_count or '无限'}, 成功即停: {until_success}")

    count = 0
    while True:
        count += 1
        log_msg(f"第 {count} 次执行...")

        result = run_with_timeout(cmd, args.timeout)

        if result['exit_code'] == 0:
            log_msg(f"✅ 执行成功")
            if until_success:
                log_msg("until_success=True, 停止调度")
                break
        else:
            log_msg(f"❌ 执行失败 (退出码: {result['exit_code']})", "WARN")

        if max_count and count >= max_count:
            log_msg(f"已达到最大执行次数 ({max_count}), 停止调度")
            break

        log_msg(f"等待 {interval}s...")
        time.sleep(interval)

    log_msg("调度结束")


def main():
    parser = argparse.ArgumentParser(description='任务调度与自动重试工具')
    sub = parser.add_subparsers(dest='command', help='可用命令')

    # retry
    p_retry = sub.add_parser('retry', help='自动重试执行命令')
    p_retry.add_argument('--cmd', required=True, help='要执行的命令')
    p_retry.add_argument('--max-retries', type=int, default=3, help='最大重试次数 (默认 3)')
    p_retry.add_argument('--base-delay', type=float, default=5, help='基础延迟秒数 (默认 5)')
    p_retry.add_argument('--timeout', type=int, default=600, help='单次超时秒数 (默认 600)')
    p_retry.add_argument('--retry-on', help='触发重试的退出码 (逗号分隔)')
    p_retry.add_argument('--log', help='结果日志文件路径')

    # batch
    p_batch = sub.add_parser('batch', help='批量顺序执行命令')
    p_batch.add_argument('--commands', required=True, help='命令列表 JSON 文件')
    p_batch.add_argument('--on-error', choices=['continue', 'stop'], default='continue', help='错误处理策略')
    p_batch.add_argument('--log', help='结果日志文件路径')

    # watch
    p_watch = sub.add_parser('watch', help='监控后台进程')
    p_watch.add_argument('--pid', type=int, required=True, help='进程 PID')
    p_watch.add_argument('--interval', type=int, default=30, help='检查间隔秒数 (默认 30)')
    p_watch.add_argument('--timeout', type=int, default=3600, help='监控超时秒数 (默认 3600)')

    # schedule
    p_schedule = sub.add_parser('schedule', help='定时执行命令')
    p_schedule.add_argument('--cmd', required=True, help='要执行的命令')
    p_schedule.add_argument('--interval', type=int, default=60, help='执行间隔秒数 (默认 60)')
    p_schedule.add_argument('--count', type=int, help='最大执行次数')
    p_schedule.add_argument('--until-success', action='store_true', help='成功后停止')
    p_schedule.add_argument('--timeout', type=int, default=300, help='单次超时秒数 (默认 300)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        'retry': cmd_retry,
        'batch': cmd_batch,
        'watch': cmd_watch,
        'schedule': cmd_schedule,
    }
    exit_code = commands[args.command](args)
    sys.exit(exit_code or 0)


if __name__ == '__main__':
    main()
