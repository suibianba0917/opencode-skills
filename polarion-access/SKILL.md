---
name: polarion-access
description: 访问 Polarion ALM/PLM 项目管理工具。使用场景：(1) 查询 Work Items（需求、缺陷、测试用例等），(2) 管理文档和模块，(3) 创建/更新工作项，(4) 查询测试运行结果，(5) 管理项目计划和审批流程。
---

# Polarion 访问 Skill

## 配置（首次使用必做）

### 方法1: 环境变量（推荐）

**PowerShell:**
```powershell
$env:POLARION_URL="https://polarion.intranet.vwg-cea.cn/polarion"
$env:POLARION_TOKEN="your_jwt_token_here"
```

**Bash:**
```bash
export POLARION_URL="https://polarion.intranet.vwg-cea.cn/polarion"
export POLARION_TOKEN="your_jwt_token_here"
```

### 方法2: 永久设置（PowerShell）

```powershell
[Environment]::SetEnvironmentVariable("POLARION_URL", "https://polarion.intranet.vwg-cea.cn/polarion", "User")
[Environment]::SetEnvironmentVariable("POLARION_TOKEN", "your_jwt_token_here", "User")
```

### 如何获取 Token

1. 登录 Polarion Web UI
2. 点击右上角用户头像 → Personal Settings
3. 选择 "Personal Access Tokens" 或 "API Tokens"
4. 点击 "Create new token"
5. 输入名称和过期时间，点击 "Create"
6. **立即复制 token**（JWT 格式，只显示一次）

## 快速开始

### 查看所有项目

```bash
python scripts/list_projects.py
```

### 查询 Work Items

```bash
python scripts/query_workitems.py --project CEA2.0 --query "type:requirement"
```

### 获取项目详情

```bash
python scripts/get_project.py CEA2.0
```

详见 [references/](references/) 目录下的详细文档。

## 认证方式

- **Token**: JWT Bearer Token
- **Header**: `Authorization: Bearer <token>`
- **API 版本**: REST API v1

## 主要功能模块

### 1. 项目管理 (Projects)

| 操作 | 端点 | 方法 |
|------|------|------|
| 获取项目列表 | `/rest/v1/projects` | GET |
| 获取项目详情 | `/rest/v1/projects/{projectId}` | GET |
| 创建项目 | `/rest/v1/projects/actions/createProject` | POST |
| 更新项目 | `/rest/v1/projects/{projectId}` | PATCH |
| 删除项目 | `/rest/v1/projects/{projectId}` | DELETE |

### 2. 工作项管理 (Work Items)

| 操作 | 端点 | 方法 |
|------|------|------|
| 查询工作项 | `/rest/v1/projects/{projectId}/workitems` | GET |
| 获取单个工作项 | `/rest/v1/projects/{projectId}/workitems/{workItemId}` | GET |
| 创建工作项 | `/rest/v1/projects/{projectId}/workitems` | POST |
| 更新工作项 | `/rest/v1/projects/{projectId}/workitems/{workItemId}` | PATCH |
| 批量更新工作项 | `/rest/v1/projects/{projectId}/workitems` | PATCH |
| 删除工作项 | `/rest/v1/projects/{projectId}/workitems/{workItemId}` | DELETE |
| 获取审批列表 | `/rest/v1/projects/{projectId}/workitems/{workItemId}/approvals` | GET |
| 添加审批 | `/rest/v1/projects/{projectId}/workitems/{workItemId}/approvals` | POST |
| 获取链接工作项 | `/rest/v1/projects/{projectId}/workitems/{workItemId}/linkedworkitems` | GET |
| 获取工作流操作 | `/rest/v1/projects/{projectId}/workitems/{workItemId}/actions/getWorkflowActions` | GET |

### 3. 文档管理 (Documents)

| 操作 | 端点 | 方法 |
|------|------|------|
| 获取空间列表 | `/rest/v1/projects/{projectId}/spaces` | GET |
| 获取文档列表 | `/rest/v1/projects/{projectId}/spaces/{spaceId}/documents` | GET |
| 获取文档详情 | `/rest/v1/projects/{projectId}/spaces/{spaceId}/documents/{documentName}` | GET |
| 创建文档 | `/rest/v1/projects/{projectId}/spaces/{spaceId}/documents` | POST |
| 分支文档 | `/rest/v1/all/documents/actions/branch` | POST |
| 获取文档附件 | `/rest/v1/projects/{projectId}/spaces/{spaceId}/documents/{documentName}/attachments` | GET |
| 获取文档评论 | `/rest/v1/projects/{projectId}/spaces/{spaceId}/documents/{documentName}/comments` | GET |

### 4. 测试管理 (Test Runs)

| 操作 | 端点 | 方法 |
|------|------|------|
| 获取测试运行列表 | `/rest/v1/projects/{projectId}/testruns` | GET |
| 获取测试运行详情 | `/rest/v1/projects/{projectId}/testruns/{testRunId}` | GET |
| 创建测试运行 | `/rest/v1/projects/{projectId}/testruns` | POST |
| 更新测试运行 | `/rest/v1/projects/{projectId}/testruns/{testRunId}` | PATCH |
| 获取测试记录 | `/rest/v1/projects/{projectId}/testruns/{testRunId}/testrecords` | GET |
| 导出测试到 Excel | `/rest/v1/projects/{projectId}/testruns/{testRunId}/actions/exportTestsToExcel` | POST |
| 导入 Excel 结果 | `/rest/v1/projects/{projectId}/testruns/{testRunId}/actions/importExcelTestResults` | POST |

### 5. 计划管理 (Plans)

| 操作 | 端点 | 方法 |
|------|------|------|
| 获取计划列表 | `/rest/v1/projects/{projectId}/plans` | GET |
| 获取计划详情 | `/rest/v1/projects/{projectId}/plans/{planId}` | GET |
| 创建计划 | `/rest/v1/projects/{projectId}/plans` | POST |
| 更新计划 | `/rest/v1/projects/{projectId}/plans/{planId}` | PATCH |
| 删除计划 | `/rest/v1/projects/{projectId}/plans/{planId}` | DELETE |

### 6. 用户管理 (Users)

| 操作 | 端点 | 方法 |
|------|------|------|
| 获取用户列表 | `/rest/v1/users` | GET |
| 获取用户详情 | `/rest/v1/users/{userId}` | GET |
| 获取用户头像 | `/rest/v1/users/{userId}/actions/getAvatar` | GET |

### 7. 枚举和图标 (Enumerations)

| 操作 | 端点 | 方法 |
|------|------|------|
| 获取枚举值 | `/rest/v1/enumerations/{enumContext}/{enumName}/{targetType}` | GET |
| 更新枚举 | `/rest/v1/enumerations/{enumContext}/{enumName}/{targetType}` | PATCH |
| 获取图标列表 | `/rest/v1/enumerations/icons` | GET |

## 查询语法

### 基础查询

```python
# 按类型查询
"type:requirement"

# 按状态查询
"status:open"

# 按标题模糊查询
"title:测试"

# 组合查询
"type:requirement AND status:open"
```

### 高级查询参数

| 参数 | 说明 |
|------|------|
| `query` | 查询条件字符串 |
| `fields[workitems]` | 返回字段列表 |
| `page[size]` | 每页数量（默认 10） |
| `page[number]` | 页码 |
| `revision` | 指定版本 |
| `include` | 包含关联资源 |

**URL 编码注意事项：**

在 curl 命令中，方括号 `[]` 需要编码：
- `[` → `%5B`
- `]` → `%5D`

示例：
```bash
# 错误：方括号未编码（curl 会报错 "bad range in URL"）
curl "https://.../workitems?fields[workitems]=title"

# 正确：方括号已编码
curl "https://.../workitems?fields%5Bworkitems%5D=title"
```

### include 参数

使用 `include` 参数可以在一次请求中获取关联资源：

```bash
# 获取工作项及其关联的审批、评论、链接
curl -s "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems/CEA-SysR-36913?include=approvals,comments,linkedWorkItems&fields[workitems]=title,description" \
  -H "Authorization: Bearer $TOKEN"
```

可用的 include 值：
- `approvals` - 审批信息
- `attachments` - 附件
- `author` - 作者
- `assignee` - 处理人
- `categories` - 分类
- `comments` - 评论
- `linkedWorkItems` - 链接的工作项
- `backlinkedWorkItems` - 反向链接的工作项
- `externallyLinkedWorkItems` - 外部链接的工作项

### 字段选择示例

```
fields[workitems]=title,status,type,severity,assignee
```

### 获取工作项描述内容

**重要说明：** `description` 字段是复杂类型，需要使用 `fields[workitems]` 参数显式请求：

```bash
# 获取工作项完整信息（包括描述）
# 注意：方括号需要 URL 编码为 %5B 和 %5D
curl -s -k "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems/CEA-SysR-36183?fields%5Bworkitems%5D=id,title,type,status,severity,description,created,updated" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

**description 字段结构：**
```json
{
  "description": {
    "type": "text/html",
    "value": "<span style=\"font-weight: bold;\">需求描述内容...</span>"
  }
}
```

- `type`: 内容类型，可选值：
  - `text/html` - HTML 格式（默认）
  - `text/plain` - 纯文本格式
- `value`: 实际描述内容（HTML 格式时包含完整 HTML 标签）

**实战示例 - 完整请求与响应：**

请求：
```bash
TOKEN="your_jwt_token"
curl -s -k "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems/CEA-SysR-36183?fields%5Bworkitems%5D=id,title,type,status,severity,description,created,updated" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

响应：
```json
{
  "links": {
    "self": "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems/CEA-SysR-36183?..."
  },
  "data": {
    "type": "workitems",
    "id": "CEA2.0/CEA-SysR-36183",
    "attributes": {
      "id": "CEA-SysR-36183",
      "type": "systemRequirement",
      "title": "外开关控制尾门（AGT临时方案，仅实现外开关解锁尾门功能）",
      "description": {
        "type": "text/html",
        "value": "<span style=\"font-weight: bold;\">1、尾门开关检测</span><br/>..."
      },
      "severity": "normal",
      "status": "reviewed",
      "created": "2025-07-28T03:19:33.987Z",
      "updated": "2025-08-04T02:58:32.658Z"
    },
    "links": {
      "self": "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems/CEA-SysR-36183",
      "portal": "https://polarion.intranet.vwg-cea.cn/polarion/redirect/project/CEA2.0/workitem?id=CEA-SysR-36183"
    }
  }
}
```

### 工作项可用字段列表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 工作项 ID |
| `title` | string | 标题 |
| `type` | string | 类型 (requirement/defect/task 等) |
| `status` | string | 状态 |
| `severity` | string | 严重程度 |
| `priority` | string | 优先级 |
| `description` | object | **描述内容（复杂类型）** |
| `created` | datetime | 创建时间 |
| `updated` | datetime | 更新时间 |
| `dueDate` | date | 截止日期 |
| `resolution` | string | 解决方案 |
| `resolvedOn` | datetime | 解决时间 |
| `initialEstimate` | string | 初始估算 |
| `remainingEstimate` | string | 剩余估算 |
| `timeSpent` | string | 已花费时间 |
| `plannedStart` | datetime | 计划开始时间 |
| `plannedEnd` | datetime | 计划结束时间 |
| `outlineNumber` | string | 大纲编号 |
| `hyperlinks` | array | 超链接列表 |

## 脚本说明

### scripts/list_projects.py

获取所有可访问的项目列表。

```bash
python scripts/list_projects.py
```

输出：
- JSON 文件: `projects.json`
- 控制台打印项目列表

### scripts/query_workitems.py

查询项目中的工作项。

```bash
python scripts/query_workitems.py --project CEA2.0 --query "type:requirement"
python scripts/query_workitems.py --project VEEA --query "status:open" --limit 50
```

参数：
- `--project`: 项目 ID（必填）
- `--query`: 查询条件
- `--fields`: 返回字段（逗号分隔）
- `--limit`: 返回数量限制
- `--offset`: 偏移量

### scripts/get_workitem.py

获取单个工作项详情。

```bash
# 基本用法（不包含描述）
python scripts/get_workitem.py --project CEA2.0 --id CEA-SysR-36183

# 获取完整内容（包括描述）- 需要指定 fields 参数
python scripts/get_workitem.py --project CEA2.0 --id CEA-SysR-36183 --fields id,title,type,status,severity,description,created,updated
```

参数：
- `--project`: 项目 ID（必填）
- `--id`: 工作项 ID（必填）
- `--fields`: 返回字段（逗号分隔），**必须包含 description 才能获取描述内容**

### scripts/create_workitem.py

创建新工作项。

```bash
python scripts/create_workitem.py --project CEA2.0 --type requirement --title "新需求标题" --description "需求描述"
```

参数：
- `--project`: 项目 ID（必填）
- `--type`: 类型（requirement/defect/task/testcase 等）
- `--title`: 标题（必填）
- `--description`: 描述
- `--severity`: 严重程度
- `--assignee`: 处理人

### scripts/list_documents.py

获取项目文档列表。

```bash
python scripts/list_documents.py --project CEA2.0
```

### scripts/get_document.py

获取文档详情和内容。

```bash
python scripts/get_document.py --project CEA2.0 --space Specification --document SRS
```

### scripts/list_testruns.py

获取测试运行列表。

```bash
python scripts/list_testruns.py --project CEA2.0
```

## 常用 Work Item 类型

| 类型 | 说明 |
|------|------|
| `requirement` | 需求 |
| `defect` | 缺陷 |
| `task` | 任务 |
| `testcase` | 测试用例 |
| `changeRequest` | 变更请求 |
| `feature` | 功能特性 |
| `epic` | 史诗 |
| `userstory` | 用户故事 |

## 常用状态值

| 状态 | 说明 |
|------|------|
| `open` | 打开 |
| `in_progress` | 进行中 |
| `resolved` | 已解决 |
| `closed` | 已关闭 |
| `verified` | 已验证 |
| `rejected` | 已拒绝 |

## API 响应格式

Polarion REST API 使用 JSON:API 规范：

```json
{
  "data": {
    "type": "workitems",
    "id": "CEA2.0/REQ-001",
    "attributes": {
      "title": "需求标题",
      "status": "open",
      "type": "requirement"
    },
    "relationships": {
      "project": {
        "data": {"type": "projects", "id": "CEA2.0"}
      }
    }
  },
  "links": {
    "self": "https://..."
  }
}
```

## 故障排除

### 常见错误及解决方案

#### 1. 401 Unauthorized - "No valid personal access token found"

**错误信息：**
```json
{"errors":[{"status":"401","title":"Unauthorized","detail":"No valid personal access token found"}]}
```

**原因：** Token 格式不正确或认证方式错误

**解决方案：**
- 确保使用 **JWT Bearer Token** 格式（不是简单的 API key）
- Header 必须使用：`Authorization: Bearer <your_jwt_token>`
- 完整示例：
```bash
curl -X GET "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9..." \
  -H "Accept: application/json"
```

#### 2. 401 Unauthorized - "No access token"

**错误信息：**
```json
{"errors":[{"status":"401","title":"Unauthorized","detail":"No access token"}]}
```

**原因：** 可能尝试了错误的 Header 格式

**注意：** 以下 Header 格式都是错误的：
- ❌ `Polarion-Access-Token: <token>`
- ❌ `X-Polarion-Access-Token: <token>`
- ❌ `Access-Token: <token>`
- ❌ `Authorization: Token <token>`

正确格式只有：
- ✅ `Authorization: Bearer <jwt_token>`

#### 3. 400 Bad Request - "Unparseable query"

**错误信息：**
```json
{"errors":[{"status":"400","title":"Bad Request","detail":"Unparseable query: (project.id:CEA2.0 AND (title:??))"}]}
```

**原因：** URL 编码问题

**解决方案：**
- 中文字符需要 URL 编码
- 使用 `--data-urlencode` 或手动编码
- 示例：`云端` → `%E4%BA%91%E7%AB%AF`

#### 4. 其他常见错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| **403 Forbidden** | 没有访问该项目/资源的权限 | 检查用户权限 |
| **404 Not Found** | 项目 ID 或工作项 ID 不存在 | 确认 ID 正确性 |
| **413 Payload Too Large** | 请求体过大 | 减少批量操作数量 |
| **网络超时** | 网络连接问题 | 检查 VPN/内网连接 |

### 认证调试技巧

#### 验证 Token 是否有效

```bash
# 解码 JWT 查看过期时间 (需要 jq 工具)
# 方法1: 使用 base64 解码
echo "eyJzdWIiOiJHQUtBMFBVIiwiaWQiOiI..." | cut -d '.' -f2 | base64 -d 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); from datetime import datetime; print('Token 过期时间:', datetime.fromtimestamp(d.get('exp', 0)))"

# 方法2: 直接调用 API 测试
curl -s "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects" \
  -H "Authorization: Bearer $POLARION_TOKEN" \
  -H "Accept: application/json" | head -100
```

如果返回 `{"errors":[{"status":"401"...}]}` 说明 Token 已过期，需要重新获取。

#### 测试 API 连接

```bash
# 先测试获取项目列表
curl -s "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects" \
  -H "Authorization: Bearer $POLARION_TOKEN" \
  -H "Accept: application/json"
```

如果返回 JSON 数据（包含 `{"data":[...]}`），则认证成功。

## 直接使用 curl 调用（无需 Python 环境）

### 基础认证方式

```bash
# 设置 Token 变量
TOKEN="your_jwt_token_here"

# 获取项目列表
curl -s "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

### 查询工作项

```bash
# 查询 CEA2.0 项目中的需求
curl -s "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems?query=type:requirement&page%5Bsize%5D=20" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"

# 获取单个工作项详情
curl -s "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems/CEA-SysR-36913" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

### 中文查询（需要 URL 编码）

```bash
# 查询标题包含"云端"的工作项
curl -s "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems?query=title:%E4%BA%91%E7%AB%AF&page%5Bsize%5D=20" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"

# 查询标题包含"OTA"的工作项
curl -s "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems?query=title:OTA&page%5Bsize%5D=20" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

### 创建工作项

```bash
curl -X POST "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "data": {
      "type": "workitems",
      "attributes": {
        "type": "requirement",
        "title": "新需求标题",
        "description": {
          "type": "text/html",
          "value": "<p>需求描述</p>"
        }
      }
    }
  }'
```

## API 文档

- REST API 文档: `{POLARION_URL}/sdk/doc/rest/index.html`
- OpenAPI 规范: `{POLARION_URL}/sdk/doc/rest/polarionrest.json`
