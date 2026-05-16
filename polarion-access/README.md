# Polarion 访问工具

通过 REST API 访问 Polarion ALM/PLM 系统，查询和管理 Work Items（需求、缺陷、测试用例等）。

## 快速开始

### 1. 配置 Token

```powershell
# PowerShell（临时）
$env:POLARION_TOKEN = "your_jwt_token_here"

# PowerShell（永久）
[Environment]::SetEnvironmentVariable("POLARION_TOKEN", "your_jwt_token", "User")
```

### 2. 获取 Token 方法

1. 登录 Polarion: https://polarion.intranet.vwg-cea.cn/polarion/
2. 右上角头像 → Personal Settings → Personal Access Tokens
3. Create new token → 复制 JWT token

### 3. 常用命令

```bash
# 查看所有项目
python scripts/polarion_api.py list-projects

# 查询需求（CEA2.0 项目）
python scripts/query_workitems.py --project CEA2.0 --query "type:requirement" --limit 20

# 获取需求详情（含描述）
python scripts/get_workitem.py --project CEA2.0 --id CEA-SysR-36183 --fields id,title,type,status,description

# 创建新需求
python scripts/create_workitem.py --project CEA2.0 --type requirement --title "新需求标题" --description "需求描述"
```

## 项目结构

```
polarion-access/
├── SKILL.md              # 完整文档
├── README.md             # 本文件
├── scripts/
│   ├── polarion_api.py   # 核心 API 客户端
│   ├── list_projects.py  # 列出项目
│   ├── query_workitems.py # 查询工作项
│   ├── get_workitem.py   # 获取工作项
│   ├── create_workitem.py # 创建工作项
│   ├── list_documents.py # 列出文档
│   └── list_testruns.py  # 列出测试运行
└── references/
    ├── api_endpoints.md  # API 端点参考
    ├── query_syntax.md   # 查询语法
    └── usage_examples.md # 使用示例
```

## 核心功能

| 功能 | 命令 |
|------|------|
| 列出项目 | `python scripts/polarion_api.py list-projects` |
| 查询工作项 | `python scripts/query_workitems.py --project CEA2.0 --query "type:requirement"` |
| 获取详情 | `python scripts/get_workitem.py --project CEA2.0 --id REQ-001 --fields title,description` |
| 创建工作项 | `python scripts/create_workitem.py --project CEA2.0 --type requirement --title "标题"` |

## 常见问题

**Q: 401 错误？**  
A: Token 过期或不正确，重新获取 JWT token。

**Q: 获取不到描述内容？**  
A: 必须使用 `--fields` 参数包含 `description`，如：`--fields id,title,description`

**Q: 中文搜索失败？**  
A: 需要 URL 编码，如"云端"→`%E4%BA%91%E7%AB%AF`

## 直接使用 curl

```bash
TOKEN="your_jwt_token"

# 列出项目
curl -s "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects" \
  -H "Authorization: Bearer $TOKEN"

# 查询需求（注意方括号需要编码）
curl -s "https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/CEA2.0/workitems?query=type:requirement&page%5Bsize%5D=10" \
  -H "Authorization: Bearer $TOKEN"
```

---
完整文档见 [SKILL.md](SKILL.md)
