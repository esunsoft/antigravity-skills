# 条目示例

具体的格式化条目示例，包含所有字段。

## Learning: Correction

```markdown
## [LRN-20260322-001] correction

**Logged**: 2026-03-22T10:30:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
错误地假设存储过程中 NOCOUNT 已默认开启

### Details
编写存储过程时，假设 NOCOUNT 已在数据库级别默认开启。
用户指出当前数据库未设置此选项，必须在每个存储过程中
显式添加 SET NOCOUNT ON 以避免返回多余的行计数消息。

### Suggested Action
在所有新建存储过程中始终添加 SET NOCOUNT ON，
检查现有存储过程是否缺少此设置。

### Metadata
- Source: user_feedback
- Related Files: 存储过程源码
- Tags: sql-server, stored-procedure, performance

---
```

## Learning: Knowledge Gap (Resolved)

```markdown
## [LRN-20260322-002] knowledge_gap

**Logged**: 2026-03-22T14:22:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: config

### Summary
PowerBuilder 2022 R3 的 DataWindow 导出格式变更

### Details
尝试用旧版解析逻辑处理 .srd 文件，发现 PB 2022 R3
的 DataWindow 导出格式与 PB 2019 存在差异。

### Suggested Action
更新解析脚本以适配 PB 2022 R3 格式。

### Metadata
- Source: error
- Related Files: *.srd
- Tags: powerbuilder, datawindow, migration

### Resolution
- **Resolved**: 2026-03-22T15:00:00+08:00
- **Notes**: 更新了解析正则表达式以处理新格式

---
```

## Learning: Promoted to KI

```markdown
## [LRN-20260322-003] best_practice

**Logged**: 2026-03-22T16:00:00+08:00
**Priority**: high
**Status**: promoted
**Promoted**: Knowledge Item
**Area**: backend

### Summary
SQL Server 存储过程必须使用 TRY-CATCH 包裹事务

### Details
发现多个存储过程在事务内执行操作但未使用 TRY-CATCH。
当中间步骤失败时，事务未被正确回滚，导致锁等待和数据不一致。

### Suggested Action
所有包含事务的存储过程都应使用 BEGIN TRY...END TRY
BEGIN CATCH...END CATCH 结构。

### Metadata
- Source: error
- Related Files: 存储过程
- Tags: sql-server, transaction, error-handling

---
```

## Error Entry

```markdown
## [ERR-20260322-A3F] python_encoding

**Logged**: 2026-03-22T09:15:00+08:00
**Priority**: high
**Status**: resolved
**Area**: config

### Summary
Python 脚本在 Windows 中文环境下读取 UTF-8 文件报 UnicodeDecodeError

### Error
```
UnicodeDecodeError: 'gbk' codec can't decode byte 0xef in position 0
```

### Context
- 命令: `python process_data.py`
- 文件编码为 UTF-8，但 Windows 中文系统默认使用 GBK
- open() 调用未指定 encoding 参数

### Suggested Fix
所有 open() 调用必须显式指定 encoding='utf-8'

### Metadata
- Reproducible: yes
- Related Files: process_data.py

### Resolution
- **Resolved**: 2026-03-22T09:30:00+08:00
- **Notes**: 添加 encoding='utf-8' 参数，已提升为全局规则

---
```

## Feature Request

```markdown
## [FEAT-20260322-001] batch_dw_check

**Logged**: 2026-03-22T16:45:00+08:00
**Priority**: medium
**Status**: pending
**Area**: docs

### Requested Capability
批量检查所有 DataWindow 的 Tab Order 是否符合规范

### User Context
项目中有数千个 .srd 文件，手动逐一检查 Tab Order
效率极低。需要自动化工具批量扫描并生成报告。

### Complexity Estimate
medium

### Suggested Implementation
编写 Python 脚本扫描所有 .srd 文件，提取控件的 tab order
属性，检查是否按从上到下、从左到右顺序递增。

### Metadata
- Frequency: recurring
- Related Features: DataWindow 质量检查

---
```
