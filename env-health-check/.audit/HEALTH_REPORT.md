# 🏥 Claude 环境健康体检报告

> 生成时间: 2026-04-18T23:52:59+0800
> Skill 版本: 2.0.0

## 📊 跨环境汇总

| 环境 | 问题数 | 预估可回收 Token | 扫描耗时 |
|------|--------|-----------------|----------|
| **Antigravity** | 0 🔴 4 🟡 | ~3,198 | 2.65s |
| **Claude Code CLI** | 0 🔴 5 🟡 | ~3,846 | 0.99s |
| **Claude Code VS Plugin** | 0 🔴 5 🟡 | ~3,846 | 0.97s |

## 🌐 环境详情: Antigravity

| 模块 | 得分 | 问题分布 | 影响 Token |
|------|------|----------|-----------|
| 配置层 (GEMINI/CLAUDE) | 93/100 | 1🟡 1🟢 | ~3,198 |
| Skills 健康度 | 93/100 | 1🟡 1🟢 | — |
| Workflows 一致性 | 100/100 | — | — |
| 资源文件整洁度 | 86/100 | 2🟡 2🟢 | — |
| Knowledge Items | 100/100 | — | — |
| MCP 配置 | 100/100 | — | — |
| 学习记录 | 100/100 | — | — |

### 🟡 Medium 条目

### CFG-002: GEMINI.md 体积偏大 (12.5KB)

- **严重程度**: 🟡 Medium
- **所属模块**: 配置层 (GEMINI/CLAUDE)
- **Token 影响**: ~3,198 tokens
- **详情**:
  GEMINI.md 当前 12.5KB (~3198 tokens)，超过 8.0KB 阈值。建议将详细规则拆分到独立 Skill 中。
- **修复建议**: 精简 GEMINI.md，将具体代码模板迁移到 Skill 中。
- **修复风险**: 🟡 批量确认

### SKL-003: 发现 1 个触发词在多个 Skill 间重叠

- **严重程度**: 🟡 Medium
- **所属模块**: Skills 健康度
- **详情**:

```
触发词重叠可能导致 Skill 选择不稳定:
  'modifying' → docx, pptx, xlsx
```
- **修复建议**: 为每个 Skill 设定更精确的独占触发词，减少歧义。
- **修复风险**: 🟡 批量确认

### RES-001: 发现大体积二进制资源文件

- **严重程度**: 🟡 Medium
- **所属模块**: 资源文件整洁度
- **详情**:

```
大体积文件组:
  .ttf: 54 个文件，合计 5.2MB
  .xsd: 117 个文件，合计 2.8MB

大文件 (>100KB) 前 10 个:
  schemas\ISO-IEC29500-4_2016\dml-main.xsd: 148KB
  schemas\ISO-IEC29500-4_2016\sml.xsd: 237KB
  schemas\ISO-IEC29500-4_2016\wml.xsd: 167KB
  schemas\ISO-IEC29500-4_2016\dml-main.xsd: 148KB
  schemas\ISO-IEC29500-4_2016\sml.xsd: 237KB
  schemas\ISO-IEC29500-4_2016\wml.xsd: 167KB
  skills\theme-factory\theme-showcase.pdf: 121KB
  schemas\ISO-IEC29500-4_2016\dml-main.xsd: 148KB
  schemas\ISO-IEC29500-4_2016\sml.xsd: 237KB
  schemas\ISO-IEC29500-4_2016\wml.xsd: 167KB
```
- **修复建议**: 审查这些文件是否为 Skill 运行所必需，不需要的可以移除。
- **修复风险**: 🟡 批量确认

### RES-002: 发现 127 个疑似孤立资源文件

- **严重程度**: 🟡 Medium
- **所属模块**: 资源文件整洁度
- **详情**:

```
以下资源文件未被同一 Skill 的代码/文档引用（前 15 个）:
  docx\scripts\office\schemas\ecma\fouth-edition\opc-digSig.xsd (3KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-chartDrawing.xsd (7KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-diagram.xsd (50KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-lockedCanvas.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-picture.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-spreadsheetDrawing.xsd (9KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-wordprocessingDrawing.xsd (14KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-additionalCharacteristics.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-bibliography.xsd (7KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-commonSimpleTypes.xsd (6KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-customXmlDataProperties.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-customXmlSchemaProperties.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-documentPropertiesVariantTypes.xsd (7KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-math.xsd (23KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-relationshipReference.xsd (1KB)
```
- **修复建议**: 确认这些文件是否仍需保留，不需要的可以删除。
- **修复风险**: 🟡 批量确认

### 🟢 Low 条目

### CFG-003: GEMINI.md 与 powershell-rules 可能存在冗余
- 检测到 GEMINI.md 中包含大量 PowerShell 规则，建议确认为何不直接使用对应 Skill。
- **修复**: 审查 GEMINI.md 中的相关章节并考虑精简。

### SKL-006: 14 个 Skill 描述超过 200 字符

```
过长的描述会增加 system prompt 中技能列表的 token 消耗:
  doc-coauthoring: 428 字符
  docx: 288 字符
  extracting-knowledge: 241 字符
  frontend-design: 438 字符
  mcp-builder: 316 字符
  parallel-agent-dispatch: 584 字符
  pdf: 272 字符
  pptx: 250 字符
  receiving-code-review: 234 字符
  self-improvement: 446 字符
```
- **修复**: 精简 SKILL.md 的 frontmatter description 字段，保留核心触发信息。

### RES-003: 发现 12 个临时/备份文件 (337.7KB)

```
可清理的文件:
  000003.log (0.1KB)
  000003.log (0.1KB)
  000003.log (0.2KB)
  000003.log (1.2KB)
  000003.log (161.8KB)
  000003.log (121.0KB)
  000003.log (20.8KB)
  000003.log (3.3KB)
  000003.log (27.4KB)
  000003.log (1.1KB)
```
- **修复**: 删除这些临时文件。
- **命令**: `Remove-Item "C:\Users\esun\.gemini\antigravity\skills\wework_drive_report_analyzer\scripts\.browser_data\Default\Extensi`

### RES-003b: 发现 5 个 __pycache__ 目录 (357KB)
- 包含 21 个 .pyc 文件
- **修复**: 清理 __pycache__ 目录。
- **命令**: `Remove-Item -Recurse -Force "C:\Users\esun\.gemini\antigravity\skills\wework_drive_report_analyzer\scripts\__pycache__";`

### ℹ️ Info 条目

### CFG-001: GEMINI.md 正常注入 (3198 tokens)
- GEMINI.md 作为全局规则注入 system prompt。 Editor 或配置文件直接管理此文件。

### CFG-005: 规则文件章节分布

```
## 🌐 核心环境声明: ~295 tokens (9%)
## 🔧 sqlcmd 使用规范（强制）: ~571 tokens (18%)
## 🔀 pwsh 7 vs 5.1 编码差异（强制）: ~316 tokens (10%)
## 🚫 SQL Server 语法禁区: ~183 tokens (6%)
## 🔄 自改进机制（强制）: ~334 tokens (10%)
## 🛡️ 输出长度防护（防截断）: ~516 tokens (16%)
```

### SKL-007: Skills SKILL.md 大小排行 (Top 15/35)

```
  powershell-rules: 19.3KB (~4935 tokens)
  docx: 19.1KB (~4895 tokens)
  understand-anything-understand: 17.8KB (~4546 tokens)
  sqlserver-perf-audit: 17.5KB (~4491 tokens)
  skill-creator: 15.8KB (~4043 tokens)
  doc-coauthoring: 15.4KB (~3953 tokens)
  subagent-driven-development: 12.1KB (~3091 tokens)
  brainstorming: 10.5KB (~2686 tokens)
  xlsx: 10.5KB (~2689 tokens)
  systematic-debugging: 9.9KB (~2525 tokens)
  test-driven-development: 9.9KB (~2546 tokens)
  parallel-agent-dispatch: 9.4KB (~2397 tokens)
  mcp-builder: 8.9KB (~2273 tokens)
  pptx: 8.5KB (~2177 tokens)
  pdf: 7.7KB (~1969 tokens)
```

### WFL-004: Workflows 统计 (5 个，共 12.9KB)

```
  superpowers-execute-plan-parallel: 5.8KB
  superpowers-execute-plan: 3.9KB
  superpowers-write-plan: 1.5KB
  superpowers-brainstorm: 1.2KB
  superpowers-reload: 0.4KB
```

### RES-004: 资源文件类型统计 (共 1173 个文件)

```
  (无扩展名): 296 个, 46.9MB
  .docx: 191 个, 8.3MB
  .ttf: 54 个, 5.2MB
  .xsd: 117 个, 2.8MB
  .py: 140 个, 1.4MB
  .md: 192 个, 1.3MB
  .json: 6 个, 933.3KB
  .html: 10 个, 574.4KB
  .txt: 46 个, 449.7KB
  .sql: 31 个, 407.0KB
  .pyc: 21 个, 356.9KB
  .log: 12 个, 337.7KB
  .pdf: 1 个, 121.4KB
  .db: 2 个, 64.0KB
  .ps1: 5 个, 25.5KB
```

### KNW-003: Knowledge Items 统计 (10 个)

```
  dev-environment: 4.9KB - 当前 Windows 11 开发机的完整环境信息：Antigravity 终端默认 pwsh 7.6.0 (Core),...
  dmv-large-db-strategy: 8.6KB - 针对大型 SQL Server 数据库（>50GB）使用 DMV 诊断时的安全策略和性能规避方案。核心内容：(1) dm...
  large-sql-file-reading: 5.3KB - 在 Windows 中文环境 (GBK/936) + Antigravity 终端中读取大型或非 UTF-8 编码 SQ...
  pb-code-restructure: 4.0KB - e:\PB项目代码重构 项目历史。为 PowerBuilder 2022 R3 + PFC 框架的大型项目创建了完整的 ...
  pb-refactor: 13.7KB - e:\pb_refactor 主工作区的完整项目历史。涵盖 SQL Server 数据库优化（存储过程/函数/触发器）、...
  pwsh7-encoding-traps: 6.7KB - PowerShell 7 (Core) 与 5.1 在文件编码行为上的关键差异，以及由此引发的 CRITICAL 级编译...
  read-url-unicode-bug: 2.4KB - read_url_content 工具下载含 Unicode 特殊字符的文件时，字符会被系统性损坏（如 — → 鈥?, ...
  sqlcmd-column-truncation: 3.7KB - sqlcmd 的 -y 参数默认限制可变长度列（varchar(max)/nvarchar(max)/xml）最大显示宽...
  sqlcmd-safety-checklist: 7.7KB - 整合 5 个工作区中所有 sqlcmd 相关错误（6 个问题，占总问题 27%），形成可复用的安全操作检查清单。覆盖：参...
  sqlserver-syntax-gotchas: 7.2KB - 整合 SQL Server 中容易被误用的语法特性和已知限制，包括：(1) 聚合函数内嵌子查询限制（SUM/COUNT ...
```

### MCP-003: 已配置 1 个 MCP Server
-   mcp-toolbox: C:\Users\esun\toolbox.exe

### LRN-003: .learnings 统计 (2 个文件)

```
  C:\Users\esun\.gemini\antigravity\.learnings: 2 个文件, 8.9KB
    ERRORS.md: 1.8KB
    LEARNINGS.md: 7.2KB
```

## 🌐 环境详情: Claude Code CLI

| 模块 | 得分 | 问题分布 | 影响 Token |
|------|------|----------|-----------|
| 配置层 (GEMINI/CLAUDE) | 93/100 | 1🟡 1🟢 | ~3,846 |
| Skills 健康度 | 88/100 | 2🟡 1🟢 | — |
| 资源文件整洁度 | 86/100 | 2🟡 2🟢 | — |
| MCP 配置 | 100/100 | — | — |
| 学习记录 | 100/100 | — | — |

### 🟡 Medium 条目

### CFG-002: CLAUDE.md 体积偏大 (15.0KB)

- **严重程度**: 🟡 Medium
- **所属模块**: 配置层 (GEMINI/CLAUDE)
- **Token 影响**: ~3,846 tokens
- **详情**:
  CLAUDE.md 当前 15.0KB (~3846 tokens)，超过 12.0KB 阈值。建议将详细规则拆分到独立 Skill 中。
- **修复建议**: 精简 CLAUDE.md，将具体代码模板迁移到 Skill 中。
- **修复风险**: 🟡 批量确认

### SKL-003: 发现 3 个触发词在多个 Skill 间重叠

- **严重程度**: 🟡 Medium
- **所属模块**: Skills 健康度
- **详情**:

```
触发词重叠可能导致 Skill 选择不稳定:
  'modifying' → docx, pptx, xlsx
  'pagination' → superpowers-python-automation, superpowers-rest-automation
  'retries' → superpowers-python-automation, superpowers-rest-automation
```
- **修复建议**: 为每个 Skill 设定更精确的独占触发词，减少歧义。
- **修复风险**: 🟡 批量确认

### SKL-005: 2 个 Skill 含 Windows 环境冲突语法

- **严重程度**: 🟡 Medium
- **所属模块**: Skills 健康度
- **详情**:

```
以下 Skill 包含与 Windows 环境不兼容的语法:
  webapp-testing: 使用 ```bash 代码块; 引用 /tmp/ 路径
  xlsx: 使用 ```bash 代码块
```
- **修复建议**: 将 bash 语法替换为 PowerShell，/tmp/ 替换为 $env:TEMP。
- **修复风险**: 🟡 批量确认

### RES-001: 发现大体积二进制资源文件

- **严重程度**: 🟡 Medium
- **所属模块**: 资源文件整洁度
- **详情**:

```
大体积文件组:
  .ttf: 54 个文件，合计 5.2MB
  .xsd: 117 个文件，合计 2.8MB

大文件 (>100KB) 前 10 个:
  schemas\ISO-IEC29500-4_2016\dml-main.xsd: 148KB
  schemas\ISO-IEC29500-4_2016\sml.xsd: 237KB
  schemas\ISO-IEC29500-4_2016\wml.xsd: 167KB
  schemas\ISO-IEC29500-4_2016\dml-main.xsd: 148KB
  schemas\ISO-IEC29500-4_2016\sml.xsd: 237KB
  schemas\ISO-IEC29500-4_2016\wml.xsd: 167KB
  skills\theme-factory\theme-showcase.pdf: 121KB
  schemas\ISO-IEC29500-4_2016\dml-main.xsd: 148KB
  schemas\ISO-IEC29500-4_2016\sml.xsd: 237KB
  schemas\ISO-IEC29500-4_2016\wml.xsd: 167KB
```
- **修复建议**: 审查这些文件是否为 Skill 运行所必需，不需要的可以移除。
- **修复风险**: 🟡 批量确认

### RES-002: 发现 127 个疑似孤立资源文件

- **严重程度**: 🟡 Medium
- **所属模块**: 资源文件整洁度
- **详情**:

```
以下资源文件未被同一 Skill 的代码/文档引用（前 15 个）:
  docx\scripts\office\schemas\ecma\fouth-edition\opc-digSig.xsd (3KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-chartDrawing.xsd (7KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-diagram.xsd (50KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-lockedCanvas.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-picture.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-spreadsheetDrawing.xsd (9KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-wordprocessingDrawing.xsd (14KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-additionalCharacteristics.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-bibliography.xsd (7KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-commonSimpleTypes.xsd (6KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-customXmlDataProperties.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-customXmlSchemaProperties.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-documentPropertiesVariantTypes.xsd (7KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-math.xsd (23KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-relationshipReference.xsd (1KB)
```
- **修复建议**: 确认这些文件是否仍需保留，不需要的可以删除。
- **修复风险**: 🟡 批量确认

### 🟢 Low 条目

### CFG-003: CLAUDE.md 与 powershell-rules 可能存在冗余
- 检测到 CLAUDE.md 中包含大量 PowerShell 规则，建议确认为何不直接使用对应 Skill。
- **修复**: 审查 CLAUDE.md 中的相关章节并考虑精简。

### SKL-006: 15 个 Skill 描述超过 200 字符

```
过长的描述会增加 system prompt 中技能列表的 token 消耗:
  doc-coauthoring: 428 字符
  docx: 288 字符
  extracting-knowledge: 241 字符
  mcp-builder: 316 字符
  pdf: 272 字符
  pptx: 250 字符
  receiving-code-review: 234 字符
  self-improvement: 446 字符
  superpowers-python-automation: 214 字符
  superpowers-rest-automation: 242 字符
```
- **修复**: 精简 SKILL.md 的 frontmatter description 字段，保留核心触发信息。

### RES-003: 发现 1 个临时/备份文件 (0.1KB)

```
可清理的文件:
  skill-activation.log (0.1KB)
```
- **修复**: 删除这些临时文件。
- **命令**: `Remove-Item "C:\Users\esun\.claude\skills\using-superpowers\e2e_demo\skill-activation.log"`

### RES-003b: 发现 1 个 __pycache__ 目录 (80KB)
- 包含 8 个 .pyc 文件
- **修复**: 清理 __pycache__ 目录。
- **命令**: `Remove-Item -Recurse -Force "C:\Users\esun\.claude\skills\env-health-check\scripts\checks\__pycache__"`

### ℹ️ Info 条目

### CFG-001: CLAUDE.md 正常注入 (3846 tokens)
- CLAUDE.md 作为全局规则注入 system prompt。 Editor 或配置文件直接管理此文件。

### CFG-005: 规则文件章节分布

```
## 🛠️ 工具调用强制规则: ~404 tokens (11%)
## 🧠 Memory 系统使用规范: ~268 tokens (7%)
## 🎯 Plan Mode 使用规范: ~504 tokens (13%)
## 📋 Task 工具使用规范: ~410 tokens (11%)
## 🤖 Agent 工具使用规范: ~476 tokens (12%)
```

### SKL-007: Skills SKILL.md 大小排行 (Top 15/39)

```
  powershell-rules: 19.3KB (~4939 tokens)
  docx: 19.1KB (~4895 tokens)
  understand-anything-understand: 18.7KB (~4779 tokens)
  understand-codebase: 18.7KB (~4784 tokens)
  skill-creator: 15.8KB (~4043 tokens)
  doc-coauthoring: 15.4KB (~3953 tokens)
  subagent-driven-development: 12.2KB (~3110 tokens)
  xlsx: 10.5KB (~2684 tokens)
  brainstorming: 10.4KB (~2674 tokens)
  systematic-debugging: 9.9KB (~2525 tokens)
  test-driven-development: 9.9KB (~2546 tokens)
  mcp-builder: 8.9KB (~2273 tokens)
  pptx: 8.5KB (~2177 tokens)
  pdf: 7.7KB (~1969 tokens)
  dispatching-parallel-agents: 6.4KB (~1636 tokens)
```

### RES-004: 资源文件类型统计 (共 477 个文件)

```
  .ttf: 54 个, 5.2MB
  .xsd: 117 个, 2.8MB
  .md: 139 个, 972.5KB
  .py: 90 个, 613.4KB
  .txt: 45 个, 253.6KB
  .pdf: 1 个, 121.4KB
  .pyc: 8 个, 79.8KB
  .html: 4 个, 78.7KB
  .ps1: 5 个, 25.5KB
  .gz: 1 个, 19.5KB
  .js: 3 个, 15.0KB
  .xml: 6 个, 11.6KB
  .cjs: 1 个, 11.0KB
  .dot: 1 个, 5.8KB
  .ts: 1 个, 4.9KB
```

### MCP-003: 已配置 2 个 MCP Server

```
  pencil: npx
  mcp-toolbox: C:\Users\esun\toolbox.exe
```

### LRN-003: 未发现 .learnings 目录
- 环境 Claude Code CLI 中没有 .learnings 目录

## 🌐 环境详情: Claude Code VS Plugin

| 模块 | 得分 | 问题分布 | 影响 Token |
|------|------|----------|-----------|
| 配置层 (GEMINI/CLAUDE) | 93/100 | 1🟡 1🟢 | ~3,846 |
| Skills 健康度 | 88/100 | 2🟡 1🟢 | — |
| 资源文件整洁度 | 86/100 | 2🟡 2🟢 | — |
| MCP 配置 | 100/100 | — | — |
| 学习记录 | 100/100 | — | — |

### 🟡 Medium 条目

### CFG-002: CLAUDE.md 体积偏大 (15.0KB)

- **严重程度**: 🟡 Medium
- **所属模块**: 配置层 (GEMINI/CLAUDE)
- **Token 影响**: ~3,846 tokens
- **详情**:
  CLAUDE.md 当前 15.0KB (~3846 tokens)，超过 12.0KB 阈值。建议将详细规则拆分到独立 Skill 中。
- **修复建议**: 精简 CLAUDE.md，将具体代码模板迁移到 Skill 中。
- **修复风险**: 🟡 批量确认

### SKL-003: 发现 3 个触发词在多个 Skill 间重叠

- **严重程度**: 🟡 Medium
- **所属模块**: Skills 健康度
- **详情**:

```
触发词重叠可能导致 Skill 选择不稳定:
  'modifying' → docx, pptx, xlsx
  'pagination' → superpowers-python-automation, superpowers-rest-automation
  'retries' → superpowers-python-automation, superpowers-rest-automation
```
- **修复建议**: 为每个 Skill 设定更精确的独占触发词，减少歧义。
- **修复风险**: 🟡 批量确认

### SKL-005: 2 个 Skill 含 Windows 环境冲突语法

- **严重程度**: 🟡 Medium
- **所属模块**: Skills 健康度
- **详情**:

```
以下 Skill 包含与 Windows 环境不兼容的语法:
  webapp-testing: 使用 ```bash 代码块; 引用 /tmp/ 路径
  xlsx: 使用 ```bash 代码块
```
- **修复建议**: 将 bash 语法替换为 PowerShell，/tmp/ 替换为 $env:TEMP。
- **修复风险**: 🟡 批量确认

### RES-001: 发现大体积二进制资源文件

- **严重程度**: 🟡 Medium
- **所属模块**: 资源文件整洁度
- **详情**:

```
大体积文件组:
  .ttf: 54 个文件，合计 5.2MB
  .xsd: 117 个文件，合计 2.8MB

大文件 (>100KB) 前 10 个:
  schemas\ISO-IEC29500-4_2016\dml-main.xsd: 148KB
  schemas\ISO-IEC29500-4_2016\sml.xsd: 237KB
  schemas\ISO-IEC29500-4_2016\wml.xsd: 167KB
  schemas\ISO-IEC29500-4_2016\dml-main.xsd: 148KB
  schemas\ISO-IEC29500-4_2016\sml.xsd: 237KB
  schemas\ISO-IEC29500-4_2016\wml.xsd: 167KB
  skills\theme-factory\theme-showcase.pdf: 121KB
  schemas\ISO-IEC29500-4_2016\dml-main.xsd: 148KB
  schemas\ISO-IEC29500-4_2016\sml.xsd: 237KB
  schemas\ISO-IEC29500-4_2016\wml.xsd: 167KB
```
- **修复建议**: 审查这些文件是否为 Skill 运行所必需，不需要的可以移除。
- **修复风险**: 🟡 批量确认

### RES-002: 发现 127 个疑似孤立资源文件

- **严重程度**: 🟡 Medium
- **所属模块**: 资源文件整洁度
- **详情**:

```
以下资源文件未被同一 Skill 的代码/文档引用（前 15 个）:
  docx\scripts\office\schemas\ecma\fouth-edition\opc-digSig.xsd (3KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-chartDrawing.xsd (7KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-diagram.xsd (50KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-lockedCanvas.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-picture.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-spreadsheetDrawing.xsd (9KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\dml-wordprocessingDrawing.xsd (14KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-additionalCharacteristics.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-bibliography.xsd (7KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-commonSimpleTypes.xsd (6KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-customXmlDataProperties.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-customXmlSchemaProperties.xsd (1KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-documentPropertiesVariantTypes.xsd (7KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-math.xsd (23KB)
  docx\scripts\office\schemas\ISO-IEC29500-4_2016\shared-relationshipReference.xsd (1KB)
```
- **修复建议**: 确认这些文件是否仍需保留，不需要的可以删除。
- **修复风险**: 🟡 批量确认

### 🟢 Low 条目

### CFG-003: CLAUDE.md 与 powershell-rules 可能存在冗余
- 检测到 CLAUDE.md 中包含大量 PowerShell 规则，建议确认为何不直接使用对应 Skill。
- **修复**: 审查 CLAUDE.md 中的相关章节并考虑精简。

### SKL-006: 15 个 Skill 描述超过 200 字符

```
过长的描述会增加 system prompt 中技能列表的 token 消耗:
  doc-coauthoring: 428 字符
  docx: 288 字符
  extracting-knowledge: 241 字符
  mcp-builder: 316 字符
  pdf: 272 字符
  pptx: 250 字符
  receiving-code-review: 234 字符
  self-improvement: 446 字符
  superpowers-python-automation: 214 字符
  superpowers-rest-automation: 242 字符
```
- **修复**: 精简 SKILL.md 的 frontmatter description 字段，保留核心触发信息。

### RES-003: 发现 1 个临时/备份文件 (0.1KB)

```
可清理的文件:
  skill-activation.log (0.1KB)
```
- **修复**: 删除这些临时文件。
- **命令**: `Remove-Item "C:\Users\esun\.claude\skills\using-superpowers\e2e_demo\skill-activation.log"`

### RES-003b: 发现 1 个 __pycache__ 目录 (80KB)
- 包含 8 个 .pyc 文件
- **修复**: 清理 __pycache__ 目录。
- **命令**: `Remove-Item -Recurse -Force "C:\Users\esun\.claude\skills\env-health-check\scripts\checks\__pycache__"`

### ℹ️ Info 条目

### CFG-001: CLAUDE.md 正常注入 (3846 tokens)
- CLAUDE.md 作为全局规则注入 system prompt。 Editor 或配置文件直接管理此文件。

### CFG-005: 规则文件章节分布

```
## 🛠️ 工具调用强制规则: ~404 tokens (11%)
## 🧠 Memory 系统使用规范: ~268 tokens (7%)
## 🎯 Plan Mode 使用规范: ~504 tokens (13%)
## 📋 Task 工具使用规范: ~410 tokens (11%)
## 🤖 Agent 工具使用规范: ~476 tokens (12%)
```

### SKL-007: Skills SKILL.md 大小排行 (Top 15/39)

```
  powershell-rules: 19.3KB (~4939 tokens)
  docx: 19.1KB (~4895 tokens)
  understand-anything-understand: 18.7KB (~4779 tokens)
  understand-codebase: 18.7KB (~4784 tokens)
  skill-creator: 15.8KB (~4043 tokens)
  doc-coauthoring: 15.4KB (~3953 tokens)
  subagent-driven-development: 12.2KB (~3110 tokens)
  xlsx: 10.5KB (~2684 tokens)
  brainstorming: 10.4KB (~2674 tokens)
  systematic-debugging: 9.9KB (~2525 tokens)
  test-driven-development: 9.9KB (~2546 tokens)
  mcp-builder: 8.9KB (~2273 tokens)
  pptx: 8.5KB (~2177 tokens)
  pdf: 7.7KB (~1969 tokens)
  dispatching-parallel-agents: 6.4KB (~1636 tokens)
```

### RES-004: 资源文件类型统计 (共 477 个文件)

```
  .ttf: 54 个, 5.2MB
  .xsd: 117 个, 2.8MB
  .md: 139 个, 972.5KB
  .py: 90 个, 613.4KB
  .txt: 45 个, 253.6KB
  .pdf: 1 个, 121.4KB
  .pyc: 8 个, 79.8KB
  .html: 4 个, 78.7KB
  .ps1: 5 个, 25.5KB
  .gz: 1 个, 19.5KB
  .js: 3 个, 15.0KB
  .xml: 6 个, 11.6KB
  .cjs: 1 个, 11.0KB
  .dot: 1 个, 5.8KB
  .ts: 1 个, 4.9KB
```

### LRN-003: 未发现 .learnings 目录
- 环境 Claude Code VS Plugin 中没有 .learnings 目录
