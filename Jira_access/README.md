# JIRA Access Skill

JIRA 基础设施脚本集合（附件下载），分析任务由各 debug skill 负责。

## 功能

- 查看/搜索/创建 JIRA issues
- JIRA 附件下载（支持 .001 分卷合并）
- 管理 Sprint
- **首次使用自动引导配置**
- **CCC 数字钥匙专项搜索（VCTCEM 项目，AVC/AV 域）**

## 安装

### 依赖

```bash
pip install requests
```

### 安装 Skill

将 `jira-access` 文件夹复制到你的 opencode skills 目录：

```
~/.config/opencode/skills/jira-access/
```

## 配置

### 方式1：交互式配置（推荐，首次运行自动引导）

直接运行任意脚本，首次会自动提示配置：

```bash
cd scripts
python my_tickets.py
```

输出示例：
```
==================================================
JIRA 配置向导
==================================================

首次使用需要配置 JIRA 连接信息

请输入 JIRA 地址:
  示例: https://your-company.atlassian.net
  或内网地址: https://jira.your-company.com

JIRA URL: https://your-company.atlassian.net

请输入 JIRA Personal Access Token:
  获取方式: 登录 JIRA → 头像 → Profile → Personal Access Tokens → Create token

JIRA Token: xxxxxxxx

配置信息:
  URL:   https://your-company.atlassian.net
  Token: ********1234

确认保存? (y/n): y

✓ 配置已保存到: .jira_config
  如需修改，请删除该文件重新运行或手动编辑
```

### 方式2：环境变量配置

**PowerShell（临时）:**
```powershell
$env:JIRA_URL="https://your-company.atlassian.net"
$env:JIRA_TOKEN="your_personal_access_token"
```

**PowerShell（永久）:**
```powershell
[Environment]::SetEnvironmentVariable("JIRA_URL", "https://your-company.atlassian.net", "User")
[Environment]::SetEnvironmentVariable("JIRA_TOKEN", "your_token", "User")
```

**Bash:**
```bash
export JIRA_URL="https://your-company.atlassian.net"
export JIRA_TOKEN="your_token"

# 永久设置
echo 'export JIRA_URL="https://your-company.atlassian.net"' >> ~/.bashrc
echo 'export JIRA_TOKEN="your_token"' >> ~/.bashrc
```

### 获取 Token

1. 登录 JIRA
2. 点击右上角头像 → **Profile**
3. 左侧菜单选择 **Personal Access Tokens**
4. 点击 **Create token**
5. 输入名称，点击 **Create**
6. **立即复制 token**（只显示一次）

## 使用方法

### 查看我的 Tickets

```bash
cd scripts
python my_tickets.py
```

输出示例：
```
=== User: 张三 ===

=== Found 5 open tickets ===

[OBAS-123] Task - High
  实现一键备车功能
  Status: In Progress
```

### 搜索 Tickets

```bash
python scripts/search_tickets.py "project = OBAS AND status = Open"
python scripts/search_tickets.py "text ~ 备车"
```

### CCC 数字钥匙专项搜索

```bash
python scripts/jira_search_ccc.py
```

搜索 VCTCEM 项目中与 CCC 相关的非 Open 状态 tickets，包含 AVC/AV 域、Solver/Tester Domain 或指定负责人/报告人的过滤条件。

### 创建 Ticket

```bash
python scripts/create_ticket.py --project OBAS --summary "任务标题" --description "任务描述"

# 创建并添加到 Sprint
python scripts/create_ticket.py --project EP --summary "任务标题" --sprint "EP Sprint 2606"

# 创建子任务
python scripts/create_ticket.py --parent EP-184 --summary "子任务标题"
```

### 创建子任务

```bash
python scripts/create_subtask.py --parent EP-184 --summary "子任务标题"
```

### 更新 Ticket

```bash
# 更新描述
python scripts/update_ticket.py --ticket EP-184 --description "新描述"

# 更新优先级
python scripts/update_ticket.py --ticket EP-184 --priority A1
```

### 状态流转

```bash
# 查看可用状态
python scripts/transition_ticket.py --ticket EP-184 --list

# 流转到指定状态
python scripts/transition_ticket.py --ticket EP-184 --transition "In Progress"
python scripts/transition_ticket.py --ticket EP-184 --transition "Done"
```

### 管理 Sprint

```bash
# 查看 Sprints
python scripts/board_sprints.py --board 4307

# 创建 Sprint
python scripts/board_sprints.py --board 4307 --create "Sprint 2024-01"

# 添加 ticket 到 Sprint
python scripts/add_to_sprint.py --ticket EP-184 --sprint 8837

# 查看 Sprint 中的 issues
python scripts/get_sprint_issues.py --sprint 8837
```

## 配置文件

配置保存在 `config/.jira_config` 文件中：

```
# JIRA Configuration
JIRA_URL=https://your-company.atlassian.net
JIRA_TOKEN=your_token
```

**修改配置：** 删除 `.jira_config` 文件后重新运行任意脚本即可重新配置

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| 配置向导不出现 | 已有配置文件，删除 `.jira_config` 重新配置 |
| 401 错误 | Token 过期或无效，重新生成 |
| 403 错误 | 没有权限，联系管理员 |
| 连接超时 | 检查 VPN 或网络连接 |

## 安全提示

- 配置文件 `.jira_config` 包含敏感信息，**不要提交到 Git**
- 建议添加到 `.gitignore`: `echo '.jira_config' >> .gitignore`
- Token 具有账号权限，请妥善保管

## License

MIT
