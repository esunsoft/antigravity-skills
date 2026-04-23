# -*- coding: utf-8 -*-
"""
模块 5：check_security — 安全性审查（8 条规则 SEC01-SEC08）

对应原则：P8 安全性, P5 显式失败
"""

import ast
import re
from pathlib import Path
from typing import List, Set, Tuple

from . import (
    SkillInfo, ModuleResult, RuleFinding,
    SEVERITY_BLOCKER, SEVERITY_MAJOR, SEVERITY_MINOR,
    read_text_safe,
)

# SEC01: 网络调用模块
NETWORK_MODULES = {'requests', 'urllib', 'urllib3', 'httpx', 'aiohttp', 'httplib2'}
NETWORK_FUNCTIONS = {'urlopen', 'urlretrieve', 'Request', 'get', 'post', 'put', 'delete'}
# socket 网络操作模式（排除纯端口检测场景）
SOCKET_NETWORK_PATTERNS = [r'socket\.create_connection', r'\.connect\s*\(\s*\(']  # 真实网络连接
SOCKET_LOCAL_PATTERNS = [r'socket\.socket']  # 需结合上下文判断

# SEC02: 危险文件操作
DANGEROUS_FILE_OPS = {
    'shutil.rmtree', 'os.remove', 'os.unlink', 'os.rmdir',
    'pathlib.Path.unlink', 'shutil.move',
}

# SEC03: 不安全的代码执行
UNSAFE_EXEC_PATTERNS = [
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'os\.system\s*\(',
    r'os\.popen\s*\(',
    r'subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True',
]
# compile() 安全调用前缀白名单（这些不是安全风险）
COMPILE_SAFE_PREFIXES = {
    're.compile', 'regex.compile', 'py_compile.compile',
    'pattern.compile', 'ast.compile',
}

# SEC04: 凭据模式
CREDENTIAL_PATTERNS = [
    r'(?:api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']{10,}["\']',
    r'(?:password|passwd|pwd)\s*[=:]\s*["\'][^"\']{4,}["\']',
    r'(?:secret|token)\s*[=:]\s*["\'][^"\']{10,}["\']',
    r'(?:sk|pk)-[a-zA-Z0-9]{20,}',
    r'Bearer\s+[a-zA-Z0-9_\-.]{20,}',
]


def _analyze_ast_for_network(py_file: Path) -> List[Tuple[str, int]]:
    """分析 Python 文件 AST，检测网络调用，返回 (描述, 行号) 列表"""
    findings = []
    try:
        content = read_text_safe(py_file)
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return findings

    imported_network = set()
    for node in ast.walk(tree):
        # 检查网络模块导入
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] in NETWORK_MODULES:
                    imported_network.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split('.')[0] in NETWORK_MODULES:
                imported_network.add(node.module.split('.')[0])

    if imported_network:
        findings.append((f"导入了网络模块：{', '.join(imported_network)}", 0))

    # 检查 socket 使用 — 仅标记真实网络操作
    for pattern in SOCKET_NETWORK_PATTERNS:
        matches = re.finditer(pattern, content)
        for m in matches:
            line_no = content[:m.start()].count('\n') + 1
            findings.append((f"使用了 socket 网络操作：{m.group()}", line_no))

    # socket.socket 需要结合上下文判断：检查是否有 connect/send/recv 等网络动作
    for m in re.finditer(r'socket\.socket', content):
        line_no = content[:m.start()].count('\n') + 1
        # 检查后续 20 行中是否有真实的网络连接操作
        remaining = content[m.start():m.start() + 2000]  # 向后看 2000 字符
        has_network_action = bool(re.search(
            r'\.(?:connect|send|sendall|recv|recvfrom|makefile)\s*\(', remaining
        ))
        if has_network_action:
            findings.append((f"使用了 socket 网络操作：socket.socket + connect/send", line_no))
        # 纯端口检测（bind + listen / 仅 close）不标记

    return findings


def _analyze_ast_for_dangerous_ops(py_file: Path) -> List[Tuple[str, int]]:
    """检测危险的文件操作"""
    findings = []
    try:
        content = read_text_safe(py_file)
    except Exception:
        return findings

    for op in DANGEROUS_FILE_OPS:
        pattern = re.escape(op).replace(r'\.', r'\.')
        for m in re.finditer(pattern, content):
            line_no = content[:m.start()].count('\n') + 1
            findings.append((f"使用了危险操作：{op}", line_no))

    return findings


def check(skill: SkillInfo, all_skills: List[SkillInfo]) -> ModuleResult:
    """执行安全性审查"""
    result = ModuleResult(module="security")

    # === 对脚本文件进行安全扫描 ===
    for py_file in skill.py_files:
        content = read_text_safe(py_file)
        if not content:
            continue
        fname = py_file.name

        # SEC01: 异常网络调用检测 [P8]
        net_findings = _analyze_ast_for_network(py_file)
        if net_findings:
            # 检查 Skill 是否声明了网络功能
            desc_lower = skill.fm_description.lower()
            name_lower = skill.name.lower()
            network_declared = any(kw in desc_lower or kw in name_lower
                                   for kw in ['url', 'http', 'web', 'api', 'fetch',
                                              'download', 'request', '网络', '下载'])
            if not network_declared:
                details = '; '.join(d for d, _ in net_findings[:3])
                result.add(RuleFinding(
                    rule_id="SEC01", severity=SEVERITY_BLOCKER, principle="P8",
                    title=f"未声明的网络调用：{fname}",
                    description=f"脚本包含网络调用但 Skill 未声明网络功能。{details}",
                    skill_name=skill.name, skill_env=skill.env,
                    fix_suggestion="如果网络调用是必需的，在 description 中声明；否则移除",
                ))

        # SEC02: 危险文件操作检测 [P8]
        danger_findings = _analyze_ast_for_dangerous_ops(py_file)
        if danger_findings:
            # 检查是否操作了安全目录（TEMP 等）
            uses_temp = 'TEMP' in content or 'tempfile' in content or 'tmp' in content.lower()
            if not uses_temp:
                details = '; '.join(d for d, _ in danger_findings[:3])
                result.add(RuleFinding(
                    rule_id="SEC02", severity=SEVERITY_BLOCKER, principle="P8",
                    title=f"危险文件操作：{fname}",
                    description=f"脚本包含破坏性文件操作且未限制在临时目录。{details}",
                    skill_name=skill.name, skill_env=skill.env,
                    fix_suggestion="将文件操作限制在临时目录，或添加用户确认步骤",
                ))

        # SEC03: 不安全的命令执行 [P8]
        sec03_triggered = False
        for pattern in UNSAFE_EXEC_PATTERNS:
            matches = list(re.finditer(pattern, content))
            if matches:
                match_text = matches[0].group()[:60]
                result.add(RuleFinding(
                    rule_id="SEC03", severity=SEVERITY_BLOCKER, principle="P8",
                    title=f"不安全的代码执行：{fname}",
                    description=f"检测到不安全的执行模式：{match_text}",
                    skill_name=skill.name, skill_env=skill.env,
                    fix_suggestion="使用 subprocess.run(列表参数) 替代 shell=True，避免 eval/exec",
                ))
                sec03_triggered = True
                break

        # SEC03 补充检查：裸 compile() 调用（排除 re.compile 等安全用法）
        if not sec03_triggered:
            for m in re.finditer(r'\bcompile\s*\(', content):
                # 排除注释行中的匹配
                line_start = content.rfind('\n', 0, m.start()) + 1
                line_text = content[line_start:m.start()].lstrip()
                if line_text.startswith('#'):
                    continue
                # 排除字符串常量中的匹配（简单检查：前面有奇数个引号）
                prefix_to_match = content[line_start:m.start()]
                if prefix_to_match.count("'") % 2 == 1 or prefix_to_match.count('"') % 2 == 1:
                    continue
                # 回溯检查前缀
                start = max(0, m.start() - 30)
                prefix_text = content[start:m.start()].rstrip()
                # 检查是否有安全前缀（如 re.compile, py_compile.compile）
                is_safe = False
                for safe_prefix in COMPILE_SAFE_PREFIXES:
                    parts = safe_prefix.rsplit('.', 1)
                    if len(parts) == 2 and prefix_text.endswith(parts[0] + '.'):
                        is_safe = True
                        break
                if not is_safe:
                    # 裸 compile() 确实是安全风险
                    match_text = content[m.start():m.start() + 60]
                    result.add(RuleFinding(
                        rule_id="SEC03", severity=SEVERITY_BLOCKER, principle="P8",
                        title=f"不安全的代码执行：{fname}",
                        description=f"检测到不安全的执行模式：{match_text}",
                        skill_name=skill.name, skill_env=skill.env,
                        fix_suggestion="使用 subprocess.run(列表参数) 替代 shell=True，避免 eval/exec",
                    ))
                    break

        # SEC04: 硬编码凭据检测 [P8]
        for pattern in CREDENTIAL_PATTERNS:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                # 排除注释和字符串示例
                match_line = content[:matches[0].start()].count('\n') + 1
                result.add(RuleFinding(
                    rule_id="SEC04", severity=SEVERITY_BLOCKER, principle="P8",
                    title=f"疑似硬编码凭据：{fname} 第 {match_line} 行",
                    description="检测到可能的 API Key/密码/Token 硬编码",
                    skill_name=skill.name, skill_env=skill.env,
                    fix_suggestion="使用环境变量存储敏感信息",
                ))
                break

        # SEC05: 外部 URL 数据获取风险 [P8]
        url_fetches = re.findall(r'(?:urlopen|get|fetch|download)\s*\(\s*["\']https?://', content)
        if url_fetches:
            result.add(RuleFinding(
                rule_id="SEC05", severity=SEVERITY_MAJOR, principle="P8",
                title=f"外部 URL 数据获取：{fname}",
                description="脚本从外部 URL 获取数据，获取的内容可能包含恶意指令",
                skill_name=skill.name, skill_env=skill.env,
                fix_suggestion="验证获取内容的完整性，添加超时和大小限制",
            ))

        # SEC06: 数据泄露模式检测 [P8]
        reads_files = bool(re.search(r'(?:open|read_text|read_bytes)\s*\(', content))
        sends_data = bool(re.search(r'(?:post|put|send|upload)\s*\(', content))
        if reads_files and sends_data:
            result.add(RuleFinding(
                rule_id="SEC06", severity=SEVERITY_MAJOR, principle="P8",
                title=f"潜在数据泄露模式：{fname}",
                description="脚本同时包含文件读取和数据发送操作，存在数据外泄风险",
                skill_name=skill.name, skill_env=skill.env,
                fix_suggestion="审查数据流向，确保敏感数据不被发送到外部",
            ))

    # SEC07: 写操作审批门禁 [P8, P5]
    content = skill.skill_md_content
    write_keywords = ['删除', 'delete', '修改', 'modify', '覆盖', 'overwrite',
                      '写入', 'write', '更新', 'update', '移除', 'remove']
    approval_keywords = ['确认', 'confirm', '批准', 'approve', '询问', 'ask',
                         '用户同意', 'user consent', '审批', 'review']
    has_write = any(kw in content.lower() for kw in write_keywords)
    has_approval = any(kw in content.lower() for kw in approval_keywords)
    if has_write and not has_approval:
        result.add(RuleFinding(
            rule_id="SEC07", severity=SEVERITY_MAJOR, principle="P8, P5",
            title="执行写操作但未要求用户确认",
            description="SKILL.md 中描述了写/删除操作，但未包含用户确认/审批机制",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="在执行写操作前添加用户确认步骤",
        ))

    # SEC08: Skill 来源可信度 [P8]
    has_license = any(f.stem.upper() in ('LICENSE', 'LICENCE') for f in skill.all_files)
    # 仅作为 Minor 级信息记录
    if not has_license and len(skill.py_files) > 5:
        result.add(RuleFinding(
            rule_id="SEC08", severity=SEVERITY_MINOR, principle="P8",
            title="缺少 LICENSE 文件",
            description="包含较多脚本文件但没有 LICENSE，来源可信度难以评估",
            skill_name=skill.name, skill_env=skill.env,
            fix_suggestion="添加 LICENSE 文件说明来源和许可",
        ))

    return result
