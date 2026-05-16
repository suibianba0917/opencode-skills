---
name: jira-access
description: 访问 JIRA 项目管理工具 + JIRA 附件下载。使用场景：(1) 查看/搜索/创建 JIRA issues，(2) 管理 Sprint，(3) 下载附件（支持分卷合并）。分析任务由各 debug skill（如 ccc-debug）负责。
---

# JIRA 访问 Skill

## 架构说明

```
Jira_access (基础设施)
├── scripts/download/
│   ├── download_jira_attachments.py   # JIRA 附件下载 + 7z 分卷合并
│   └── batch_debug.py                  # 批量调度入口 → 调用 ccc-debug
└── scripts/                           # JIRA 操作脚本

各 debug skill (分析逻辑)
└── ccc-debug/scripts/analyze.py    # 规则匹配 + 故障分类 + AI 分析
```

> **职责划分**：Jira_access 负责下载/解压/调度，分析逻辑下沉到各 debug skill（如 ccc-debug、iccoa-debug 等）。

## 配置（首次使用必做）

### 方法1: 环境变量（推荐）

**PowerShell:**
```powershell
$env:JIRA_URL="https://your-company.com/jira"
$env:JIRA_TOKEN="your_token_here"
```

**Bash:**
```bash
export JIRA_URL="https://your-company.com/jira"
export JIRA_TOKEN="your_token_here"
```

### 方法2: 永久设置（PowerShell）

```powershell
[Environment]::SetEnvironmentVariable("JIRA_URL", "https://your-company.com/jira", "User")
[Environment]::SetEnvironmentVariable("JIRA_TOKEN", "your_token_here", "User")
```

### 如何获取 Token

1. 登录 JIRA
2. 点击右上角头像 → Profile
3. 左侧菜单选择 Personal Access Tokens
4. 点击 "Create token"
5. 输入名称，点击 "Create"
6. **立即复制 token**（只显示一次）

## 快速开始

### 查看我的 Tickets

```bash
python scripts/my_tickets.py
```

### 搜索 Tickets

```bash
python scripts/search_tickets.py "text ~ 一键备车"
python scripts/search_tickets.py "text ~ CCC钱包钥匙" --max 50
```

### 查看 Ticket 详情

```bash
python scripts/get_ticket_detail.py VCTCEM-26376
```
（包含基本信息、描述、评论、变更历史）

### 创建 Ticket

```bash
python scripts/create_ticket.py --project OBAS --summary "测试任务" --description "任务描述"
```

详见 [references/](references/) 目录。

### 快速创建并添加到 Sprint

```bash
# 使用 Sprint 名称（推荐）
python scripts/create_ticket.py --project EP --summary "任务标题" --description "描述" --sprint "EP Sprint 2606"

# 使用 Sprint ID
python scripts/create_ticket.py --project EP --summary "任务标题" --description "描述" --sprint 8837
```

## 认证方式

- **Token**: Bearer Token (Personal Access Token)
- **方式**: 需要先访问 `/login.jsp` 获取 session，再用 Bearer Token

## 脚本说明

### scripts/my_tickets.py

获取当前用户未解决的 tickets。

```bash
python scripts/my_tickets.py
```

输出：
- JSON 文件: `my_tickets.json`
- 控制台打印 tickets 列表

### scripts/search_tickets.py

搜索 JIRA issues。

```bash
python scripts/search_tickets.py "project = OBAS AND status = Open"
python scripts/search_tickets.py "text ~ RVC"
python scripts/search_tickets.py "text ~ CCC钱包钥匙" --max 100
```

参数：
- `--max`: 最大结果数（默认: 100）

### scripts/get_ticket_detail.py

获取 ticket 完整信息（基本信息、描述、评论、变更历史）。

```bash
python scripts/get_ticket_detail.py VCTCEM-26376
```

输出内容：
- 基本信息：状态、优先级、类型、负责人、创建/更新时间
- 摘要：标题
- 描述：详细的问题描述
- 评论：所有评论及时间线
- 变更历史：最近10条变更记录

### scripts/create_ticket.py

创建新 ticket。

```bash
python scripts/create_ticket.py --project OBAS --summary "任务标题" --description "描述" --type Task
```

参数：
- `--project`: 项目 key (默认: OBAS)
- `--summary`: 标题
- `--description`: 描述
- `--type`: 类型 (Task/Story/Bug/Epic/Sub-task)
- `--assignee`: 处理人
- `--sprint`: Sprint 名称（如 "EP Sprint 2606"）或 Sprint ID（如 8837）
- `--priority`: 优先级（如 A1, Highest, High）
- `--parent`: 父任务 key（创建子任务时使用）

### scripts/board_sprints.py

查看和管理 Sprint。

```bash
# 查看 Sprint
python scripts/board_sprints.py --board 4307

# 创建 Sprint
python scripts/board_sprints.py --board 4307 --create "EP Sprint 2612"
```

### scripts/add_to_sprint.py

添加 ticket 到 sprint。

```bash
# 添加单个 ticket
python scripts/add_to_sprint.py --ticket EP-184 --sprint 8838

# 添加多个 tickets
python scripts/add_to_sprint.py --ticket EP-184 EP-185 --sprint 8838
```

参数：
- `--ticket`: Ticket key(s)，支持多个
- `--sprint`: Sprint ID（数字）

### scripts/update_ticket.py

更新 ticket 信息。

```bash
# 更新描述
python scripts/update_ticket.py --ticket EP-138 --description "新的描述内容"

# 更新优先级
python scripts/update_ticket.py --ticket EP-184 --priority A1

# 更新标题
python scripts/update_ticket.py --ticket EP-184 --summary "新标题"
```

参数：
- `--ticket`: Ticket key
- `--summary`: 新标题
- `--description`: 新描述
- `--priority`: 优先级
- `--assignee`: 处理人用户名

### scripts/get_sprint_issues.py

查看 Sprint 中的所有 issues。

```bash
# 查看 Sprint 中的 issues
python scripts/get_sprint_issues.py --sprint 8837

# 保存到文件
python scripts/get_sprint_issues.py --sprint 8837 --output sprint_2606.json
```

参数：
- `--sprint`: Sprint ID
- `--output`: 输出文件路径（可选）

### scripts/transition_ticket.py

Ticket 状态流转。

```bash
# 查看可用的状态流转
python scripts/transition_ticket.py --ticket EP-184 --list

# 通过名称流转
python scripts/transition_ticket.py --ticket EP-184 --transition "In Progress"
python scripts/transition_ticket.py --ticket EP-184 --transition "Done"

# 通过 ID 流转
python scripts/transition_ticket.py --ticket EP-184 --id 21
```

参数：
- `--ticket`: Ticket key
- `--transition`: 状态名称（如 "In Progress", "Done"）
- `--id`: 状态 ID
- `--list`: 列出可用的状态流转

### scripts/create_subtask.py

创建子任务。

```bash
# 创建子任务
python scripts/create_subtask.py --parent EP-184 --summary "子任务标题"

# 带描述和优先级
python scripts/create_subtask.py --parent EP-184 --summary "子任务标题" --description "描述" --priority A1
```

参数：
- `--parent`: 父任务 key
- `--summary`: 子任务标题
- `--description`: 描述（可选）
- `--assignee`: 处理人（可选）
- `--priority`: 优先级（可选）

> 提示：也可以使用 `create_ticket.py --parent EP-184` 创建子任务

## 高级用法

### 常用 Board ID 参考

| Project | Board ID | Board Name |
|---------|----------|------------|
| EP | 4307 | EP board |

### Sprint ID 参考

| Sprint Name | Sprint ID |
|-------------|-----------|
| EP Sprint 2605 | 8836 |
| EP Sprint 2606 | 8837 |
| EP Sprint 2607 | 8838 |

> 注：Sprint ID 会随新 Sprint 创建而变化，可通过 `board_sprints.py` 查询最新 ID。

### JQL 查询语法

```jql
# 我的未解决 tickets
assignee = currentUser() AND resolution = Unresolved

# 项目搜索
project = OBAS AND status = Open

# 文本搜索
text ~ "RVC"

# 组合
project = OBAS AND issuetype = Story AND status = "In Progress"

# Sprint
sprint = "EP Sprint 2610"
```

### Issue Type

- `Epic` - 史诗
- `Story` - 用户故事
- `Task` - 任务
- `Sub-task` - 子任务
- `Bug` - 缺陷

### API 端点

| 操作 | 端点 | 方法 |
|------|------|------|
| 当前用户 | `/rest/api/2/myself` | GET |
| 搜索 | `/rest/api/2/search?jql=...` | GET |
| 创建 issue | `/rest/api/2/issue` | POST |
| 获取 issue | `/rest/api/2/issue/{key}` | GET |
| 更新 issue | `/rest/api/2/issue/{key}` | PUT |
| 获取 Sprint | `/rest/agile/1.0/board/{id}/sprint` | GET |
| 创建 Sprint | `/rest/agile/1.0/sprint` | POST |
| 添加 issue 到 Sprint | `/rest/agile/1.0/sprint/{id}/issue` | POST |
| 获取 Sprint 中的 issues | `/rest/agile/1.0/sprint/{id}/issue` | GET |

## 故障排除

- **Warning: JIRA_TOKEN not configured**: 未设置环境变量，按上方配置说明设置
- **401 错误**: Token 可能过期，重新生成
- **403 错误**: 没有权限
- **session 失效**: 确保先访问 `/login.jsp`
