---
name: powershell-rules
description: Windows 环境下的脚本编写规范（路径处理、编码规则、语法对照）。触发关键词：Windows 脚本、PowerShell、Python Windows、路径处理、编码问题
---

# Windows 开发环境规范

## 适用场景

当需要生成或执行 Python 脚本、PowerShell 命令，或涉及文件 I/O、路径处理、编码相关操作时激活此技能。

## 环境声明

你正在 **Windows 11 简体中文** 操作系统上运行。所有 shell 命令必须使用 **PowerShell** 语法（非 cmd.exe，非 Bash）。当前 PowerShell 版本为 7+（PowerShell Core）。

---

## 一、路径处理规范

### 1.1 禁止使用 Linux 路径

❌ 绝对禁止:
`/tmp`, `/home`, `/usr`, `/etc`, `/var`, `/opt`, `/dev/null`, `~/.config`

✅ Windows 正确替代:

| Linux 路径 | Windows 替代 | 典型值 |
|------------|-------------|--------|
| `/tmp` | `$env:TEMP` | `C:\Users\<用户名>\AppData\Local\Temp` |
| `/home/<user>` | `$env:USERPROFILE` | `C:\Users\<用户名>` |
| `/dev/null` | `$null`（PowerShell）或 `NUL`（CMD） | — |
| `~/.config` | `$env:APPDATA` | `C:\Users\<用户名>\AppData\Roaming` |
| `/usr/local` | `$env:LOCALAPPDATA` | `C:\Users\<用户名>\AppData\Local` |

### 1.2 路径写法规则

```python
# ❌ 错误 - 硬编码 Linux 路径
temp_dir = "/tmp"
config_path = "~/.config/myapp"

# ✅ 正确 - 使用跨平台方式
import tempfile, os, pathlib

temp_dir = tempfile.gettempdir()                          # 自动适配系统
config_path = pathlib.Path.home() / ".config" / "myapp"   # 跨平台
project_root = pathlib.Path(__file__).parent.resolve()     # 项目相对路径
```

```powershell
# ❌ 错误
$path = "/tmp/output.txt"

# ✅ 正确
$path = Join-Path $env:TEMP "output.txt"
```

### 1.3 路径中的中文和空格

```python
# ❌ 危险 - 路径拼接可能因空格/中文断裂
os.system(f'python {script_path}')

# ✅ 安全 - 用引号包裹或用列表传参
subprocess.run(['python', str(script_path)], check=True)
# 或在 shell 模式下:
subprocess.run(f'python "{script_path}"', shell=True, check=True)
```

### 1.4 始终使用 pathlib 或 os.path

```python
# ❌ 字符串拼接路径
path = folder + "/" + filename          # Linux 风格
path = folder + "\\" + filename         # 转义容易出错

# ✅ 正确方式
from pathlib import Path
path = Path(folder) / filename

# 或
import os
path = os.path.join(folder, filename)
```

### 1.5 PowerShell 路径处理

- 始终使用反斜杠 `\` 作为路径分隔符
- 包含空格的路径必须用引号包裹：`"C:\Program Files\app\file.txt"`
- 使用 `Join-Path` 拼接路径，而非字符串拼接
- 使用 `$env:USERPROFILE` 代替 `~`（在某些上下文中 `~` 不被正确解析）
- 使用 `$PSScriptRoot` 获取脚本所在目录

---

## 二、编码规范

### 2.1 Python 文件 I/O — 永远显式指定 encoding

```python
# ❌ 大忌 - 在中文 Windows 上默认编码是 GBK，不是 UTF-8！
with open("data.txt", "r") as f:
    content = f.read()                  # 读 UTF-8 文件会乱码或报错

# ✅ 必须这样写
with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()

# ✅ 写文件同理
with open("output.txt", "w", encoding="utf-8") as f:
    f.write("你好世界")

# ✅ 如果需要兼容 Excel 打开 CSV，使用 utf-8-sig (带 BOM)
with open("data.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(data)

# ✅ 读取未知编码的文件，做容错处理
with open("unknown.txt", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()
```

### 2.2 Python 标准输出编码

```python
# 如果脚本涉及打印中文到控制台，在脚本开头添加:
import sys, io

# 方法一: 强制 stdout/stderr 使用 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 方法二: 设置环境变量 (推荐在运行命令时设置)
# $env:PYTHONIOENCODING = "utf-8"
```

### 2.3 subprocess 中的编码

```python
# ❌ 中文 Windows 下 subprocess 默认返回 GBK 编码
result = subprocess.run(["ipconfig"], capture_output=True, text=True)

# ✅ 显式指定编码
result = subprocess.run(
    ["ipconfig"],
    capture_output=True,
    text=True,
    encoding="utf-8",       # 或 "gbk"，取决于被调用程序的输出编码
    errors="replace"         # 容错
)

# ⚠️ 注意: Windows 系统命令(ipconfig, dir 等)输出通常是 GBK
# 第三方工具(git, node, python 等)输出通常是 UTF-8
# 需要根据实际情况选择 encoding="gbk" 或 encoding="utf-8"
```

### 2.4 PowerShell 编码设置

```powershell
# 在执行涉及中文的操作前，设置控制台编码:
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 读写文件指定编码:
# ❌ 可能乱码
Get-Content "file.txt"

# ✅ 指定 UTF-8
Get-Content "file.txt" -Encoding UTF8
Set-Content "file.txt" -Value "你好" -Encoding UTF8

# ✅ PowerShell 7+ 写入无 BOM 的 UTF-8
$content | Out-File "file.txt" -Encoding utf8NoBOM

# ✅ 如果需要无 BOM 的 UTF-8（PowerShell 5.1）:
[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))
```

### 2.5 JSON 处理中的编码

```python
import json

# ❌ 中文被转义为 \uXXXX
json.dumps(data)

# ✅ 保持中文可读
json.dumps(data, ensure_ascii=False, indent=2)

# ✅ 写入 JSON 文件
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## 三、Python 脚本规范

### 3.1 Python 调用命令

```powershell
# ❌ Windows 上通常没有 python3 命令
python3 script.py

# ✅ Windows 上使用
python script.py

# ✅ 或使用 Python Launcher (如果安装了多版本)
py script.py
py -3 script.py
py -3.11 script.py
```

### 3.2 脚本首行（Shebang）

```python
# ❌ Windows 不认识 shebang (但保留也不会报错，只是无用)
#!/usr/bin/env python3

# ✅ 在 Windows 上，shebang 行可以保留但不要依赖它来执行脚本
# 始终通过 python script.py 显式调用
```

### 3.3 Windows 中文环境兼容性模板

```python
"""
Windows 11 中文环境兼容性模板
在脚本开头引入以下设置
"""
import sys
import os
import io
import locale

# ── 编码修复 ──
if sys.platform == "win32":
    # 强制 UTF-8 输出
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    # 设置环境变量
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")

# ── 临时目录修复 ──
import tempfile
TEMP_DIR = tempfile.gettempdir()  # 不要硬编码 /tmp

# ── 路径处理 ──
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.resolve()
```

### 3.4 错误处理推荐模板

```python
# Python 错误处理推荐模板
import sys
import traceback

def safe_main():
    """带完整错误处理的主函数"""
    try:
        main()
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}", file=sys.stderr)
        print(f"   提示: 请检查路径是否正确，Windows 路径使用反斜杠 \\", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"❌ 编码错误: {e}", file=sys.stderr)
        print(f"   提示: 尝试使用 encoding='gbk' 或 encoding='utf-8-sig'", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"❌ 权限不足: {e}", file=sys.stderr)
        print(f"   提示: 尝试以管理员身份运行，或检查文件是否被占用", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 未预期的错误: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    safe_main()
```

### 3.5 创建临时文件的标准做法

```python
import tempfile
from pathlib import Path

# ❌ 绝对禁止
tmp_file = "/tmp/my_temp_file.txt"

# ✅ 方法一: 使用 tempfile 模块（推荐）
with tempfile.NamedTemporaryFile(
    mode='w',
    suffix='.txt',
    prefix='myapp_',
    encoding='utf-8',
    delete=False           # Windows 上需要 delete=False 才能被其他进程读取
) as f:
    f.write("临时数据")
    temp_path = f.name
# 用完后手动删除
Path(temp_path).unlink(missing_ok=True)

# ✅ 方法二: 使用临时目录
with tempfile.TemporaryDirectory(prefix='myapp_') as tmpdir:
    output_file = Path(tmpdir) / "output.txt"
    output_file.write_text("临时数据", encoding="utf-8")
    # tmpdir 退出 with 块后自动清理
```

---

## 四、PowerShell 脚本规范

### 4.1 绝对禁止的写法

- ❌ 禁止使用 Linux/Bash 命令：`ls -la`, `grep`, `cat`, `rm -rf`, `chmod`, `sudo`, `apt`, `curl`（Bash 版本）, `wget`（Linux 版本）, `sed`, `awk`, `find`（Linux 版本）, `export VAR=value`, `source`, `&&` 连接命令
- ❌ 禁止使用 cmd.exe 语法：`dir /s`, `del /f`, `copy`, `set VAR=value`, `%VAR%`
- ❌ 禁止在字符串中使用未转义的 `$` 符号（在双引号中 `$` 会被解析为变量）
- ❌ 禁止假设命令输出是纯文本（PowerShell 管道传递的是 .NET 对象）
- ❌ 禁止使用 `&&` 或 `||` 连接命令（PowerShell 5.1 不支持）

### 4.2 与 Bash 的语法差异对照表

| 用途               | Bash / Linux         | PowerShell (Windows)       |
|--------------------|----------------------|----------------------------|
| 列出文件           | `ls -la`               | `Get-ChildItem -Force`      |
| 查看文件内容       | `cat file.txt`         | `Get-Content file.txt`       |
| 文本搜索           | `grep "text" file`     | `Select-String "text" file`  |
| 查找命令位置       | `which python`         | `Get-Command python`         |
| 环境变量           | `$HOME`                | `$env:USERPROFILE`           |
| 设置环境变量       | `export KEY=VALUE`     | `$env:KEY = "VALUE"`         |
| 命令替换           | `$(command)`           | `$(command)` ✅ 一样          |
| 管道传文本         | `cmd \| grep x`         | `cmd \| Select-String x`      |
| 丢弃输出           | `cmd > /dev/null`      | `cmd > $null` 或 `cmd \| Out-Null` |
| 后台运行           | `cmd &`                | `Start-Process cmd`          |
| 逻辑与             | `cmd1 && cmd2`         | `cmd1; if($?) { cmd2 }` 或 (pwsh 7+) `cmd1 && cmd2` |
| 逻辑或             | `cmd1 \|\| cmd2`         | `cmd1; if(!$?) { cmd2 }`     |
| 多行字符串         | `cat << 'EOF'`         | `@" ... "@`                  |
| 进程列表           | `ps aux`               | `Get-Process`                |
| 杀进程             | `kill PID`             | `Stop-Process -Id PID`       |
| 下载文件           | `curl/wget URL`        | `Invoke-WebRequest URL -OutFile file.txt` |
| 创建目录           | `mkdir -p dir/sub`     | `New-Item -ItemType Directory -Path dir/sub -Force` |
| 删除文件/目录      | `rm -rf dir`           | `Remove-Item dir -Recurse -Force` |
| 文件是否存在       | `test -f file`         | `Test-Path file`             |
| 字符串包含         | `[[ $s == *"sub"* ]]`  | `$s -like "*sub*"` 或 `$s.Contains("sub")` |
| 当前目录           | `pwd`                  | `Get-Location` (或 `pwd`)    |
| 文件权限           | `chmod +x file`        | ⚠️ Windows无此概念            |
| 查找文件           | `find / -name "*.txt"` | `Get-ChildItem -Path C:\ -Filter "*.txt" -Recurse` |
| 追加写入           | `echo "text" >> file`  | `Add-Content -Path "file" -Value "text"` |
| Null 设备          | `/dev/null`            | `$null`                      |
| 路径拼接           | `"$dir/$file"`         | `Join-Path -Path $dir -ChildPath $file` |

### 4.3 PowerShell 引号规则

```powershell
# 双引号: 会展开变量和转义字符
$name = "世界"
Write-Host "你好 $name"           # 输出: 你好 世界

# 单引号: 原样输出，不展开变量
Write-Host '你好 $name'           # 输出: 你好 $name

# 转义字符用反引号 ` (不是反斜杠 \)
Write-Host "第一行`n第二行"        # `n = 换行
Write-Host "制表符`t分隔"          # `t = Tab

# ❌ 不要用 bash 风格转义
Write-Host "line1\nline2"          # 输出原样，不会换行

# Here-String (多行文本)
$text = @"
这是第一行
这是第二行 包含 "引号" 也没问题
变量也会展开: $name
"@
```

### 4.4 PowerShell 常见错误预防

```powershell
# ❌ 错误: 使用 bash 的 && 连接 (PowerShell 5.1 不支持)
cd project && python main.py

# ✅ PowerShell 5.1 兼容写法
Set-Location project; if ($?) { python main.py }

# ✅ 最安全的写法:
Push-Location project
try {
    python main.py
} finally {
    Pop-Location
}

# ──────────────────────────────────

# ❌ 错误: 比较运算符用错
if ($a == $b) { }     # == 不是 PowerShell 比较运算符!
if ($a > 5) { }       # > 是重定向运算符!

# ✅ PowerShell 比较运算符
if ($a -eq $b) { }    # 等于
if ($a -ne $b) { }    # 不等于
if ($a -gt 5) { }     # 大于
if ($a -lt 5) { }     # 小于
if ($a -ge 5) { }     # 大于等于
if ($a -le 5) { }     # 小于等于
if ($a -like "*.txt") { }    # 通配符匹配
if ($a -match "regex") { }   # 正则匹配

# ──────────────────────────────────

# ❌ 错误: 用 bash 语法设置变量
export MY_VAR="hello"
MY_VAR=hello

# ✅ PowerShell 设置变量
$MY_VAR = "hello"                    # PowerShell 变量
$env:MY_VAR = "hello"               # 环境变量

# ──────────────────────────────────

# ❌ 错误: 管道传递的是文本行（bash 思维）
# ✅ PowerShell 管道传递的是**对象**，善用属性

# 示例: 查找占用端口的进程
# bash 思维 (不推荐):  netstat -ano | findstr ":8080"
# PowerShell 思维 (推荐):
Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue |
    Select-Object LocalPort, OwningProcess, State
```

### 4.5 执行策略

```powershell
# 如果 .ps1 脚本无法执行，先检查策略:
Get-ExecutionPolicy

# 设置为允许本地脚本 (仅当前用户):
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 临时绕过 (单次执行):
powershell -ExecutionPolicy Bypass -File script.ps1
```

---

## 五、常见工具命令的 Windows 适配

### 5.1 Git

```powershell
# Git 中文文件名显示为数字转义
# ❌  \346\226\260\345\273\272\346\226\207\344\273\266.txt

# ✅ 修复:
git config --global core.quotepath false

# Git 换行符设置 (避免 CRLF/LF 冲突):
git config --global core.autocrlf true       # Windows 推荐
```

### 5.2 Node.js

```powershell
# Node.js 中文输出乱码修复:
$env:NODE_OPTIONS = "--experimental-vm-modules"
chcp 65001

# 或在 node 脚本中:
# process.stdout.setEncoding('utf-8');
```

### 5.3 Docker

```powershell
# 路径挂载格式不同
# ❌ Linux 格式
docker run -v /home/user/app:/app image

# ✅ Windows 格式
docker run -v "${PWD}:/app" image
docker run -v "C:\Users\username\app:/app" image
```

### 5.4 curl / wget

```powershell
# ⚠️ PowerShell 中 curl 是 Invoke-WebRequest 的别名，行为不同！

# 如果要用真正的 curl.exe:
curl.exe https://example.com

# PowerShell 原生下载:
Invoke-WebRequest -Uri "https://example.com/file.zip" -OutFile "file.zip"

# 或简写:
iwr "https://example.com/file.zip" -OutFile "file.zip"
```

---

## 六、调试速查

### 6.1 常见错误信息与解决方案

| 错误信息 | 原因 | 修复方案 |
|----------|------|----------|
| `FileNotFoundError: [Errno 2] No such file or directory: '/tmp/xxx'` | 使用了 Linux 路径 | 改用 `tempfile.gettempdir()` 或 `$env:TEMP` |
| `UnicodeDecodeError: 'gbk' codec can't decode byte 0x...` | Windows 默认用 GBK 解码 UTF-8 文件 | `open()` 加 `encoding='utf-8'` |
| `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x...` | 文件实际是 GBK/GB2312 编码 | `open()` 改 `encoding='gbk'` 或 `encoding='gb2312'` |
| `'python3' 不是内部或外部命令` | Windows 没有 `python3` 别名 | 使用 `python` 或 `py -3` |
| `无法加载文件 xxx.ps1，因为在此系统上禁止运行脚本` | PowerShell 执行策略限制 | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `The term 'xxx' is not recognized` (在 `&&` 之后) | PowerShell 5.1 不支持 `&&` 运算符 | 使用分号和 `$?` 判断，或升级到 PowerShell 7 |
| `OSError: [WinError 1314] 客户端没有所需的特权` | 创建符号链接需要管理员权限 | 以管理员身份运行，或改用复制/快捷方式 |
| `PermissionError: [WinError 32] 另一个程序正在使用此文件` | 文件被其他进程锁定 | 关闭占用进程，或使用 `delete=False` 的临时文件 |

### 6.2 环境诊断命令

```powershell
# 一键检查开发环境（可直接在终端执行）:
Write-Host "=== 系统信息 ===" -ForegroundColor Cyan
Write-Host "OS: $([System.Environment]::OSVersion)"
Write-Host "PowerShell: $($PSVersionTable.PSVersion)"
Write-Host "编码: $([Console]::OutputEncoding.EncodingName)"
Write-Host ""
Write-Host "=== 开发工具 ===" -ForegroundColor Cyan
@("python", "py", "node", "npm", "git", "docker", "code") | ForEach-Object {
    $cmd = Get-Command $_ -ErrorAction SilentlyContinue
    if ($cmd) {
        Write-Host "✅ $_ : $($cmd.Source)"
    } else {
        Write-Host "❌ $_ : 未安装" -ForegroundColor Red
    }
}
Write-Host ""
Write-Host "=== Python 信息 ===" -ForegroundColor Cyan
python -c "import sys; print(f'版本: {sys.version}'); print(f'默认编码: {sys.getdefaultencoding()}'); print(f'文件系统编码: {sys.getfilesystemencoding()}'); print(f'stdout编码: {sys.stdout.encoding}')"
Write-Host ""
Write-Host "=== 关键路径 ===" -ForegroundColor Cyan
Write-Host "TEMP: $env:TEMP"
Write-Host "HOME: $env:USERPROFILE"
Write-Host "APPDATA: $env:APPDATA"
Write-Host "PWD: $(Get-Location)"
```

---

## 七、代码生成自检清单

每次生成代码时，AI 必须自检以下事项:

- [ ] 文件路径是否使用了 `pathlib.Path` 或 `os.path.join`？
- [ ] 是否有 `/tmp`, `/home`, `/dev/null` 等 Linux 路径？→ 替换！
- [ ] `open()` 是否显式指定了 `encoding="utf-8"`？
- [ ] `json.dumps()` 是否设置了 `ensure_ascii=False`？
- [ ] `subprocess` 是否指定了 `encoding` 参数？
- [ ] 是否使用了 `python3` 命令？→ 改为 `python`！
- [ ] Shell 命令是否是 PowerShell 语法（不是 bash）？
- [ ] 是否用了 `&&` 连接命令？→ 改为 `; if($?){}` 或分开写！
- [ ] 是否用了 `chmod`, `source`, `export` 等纯 Linux 命令？→ 替换！
- [ ] 是否有 `#!` shebang 并依赖它执行？→ 不要依赖！
- [ ] CSV 文件是否用了 `utf-8-sig` 编码（需要 Excel 打开时）？
- [ ] 是否有 `multiprocessing` 但缺少 `if __name__ == "__main__"` guard？

## 核心约束（不可违反）

1. **所有命令必须是 PowerShell 语法**
2. **路径使用反斜杠 `\`**
3. **文件写入使用 UTF-8 编码**
4. **不使用 Bash/cmd.exe 命令**
5. **所有代码注释使用中文**（除非注释内容是英文术语）
6. **生成 `.py` 文件时加 `# -*- coding: utf-8 -*-`**
