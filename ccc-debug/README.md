# CCC Debug Skill

CCC CarKey 数字钥匙配对失败日志分析工具，精准定位手机端/车端/车企后台/苹果后台故障根因。

## 功能

- 日志类型识别 (iOS/Android/CAN/Backend)
- 关键词匹配分析
- 故障分类（11 种故障模式）
- DBC 预解析缓存（225 条 CAN 消息）
- 规则报告生成 + AI 深度分析（调用 opencode AI）

## 目录结构

```
ccc-debug/
├── SKILL.md                 # Skill 入口定义
├── README.md                # 使用说明
├── CHANGELOG.md              # 版本变更记录（迭代简史 + 遗留问题）
├── knowledge/               # 知识层（故障域文档）
│   ├── 00_索引.md           # 知识库索引
│   ├── nfc_ecp.md           # NFC 刷卡 / ECP 配置问题
│   ├── uwb_ranging.md       # UWB 测距 / UWB定位值 / 乒乓问题 / 启停策略
│   ├── ccc_pairing.md       # 配对 5 阶段 / 钥匙分享 / iOS 证书 / 配对阶段状态机
│   ├── mdk_ops.md           # (辅助) MDK 操作 / 大屏注销 / CAN 日志分析 / TBOX环境配置
│   └── ble_connection.md    # BLE 连接(配对+车控) / Polling 策略 / CAN信号路由
├── scripts/
│   ├── analyze.py           # 分析引擎（核心逻辑）
│   ├── analyze_debug.py     # 入口脚本
│   ├── parse_dbc.py         # DBC 解析脚本
│   └── cache/
│       └── dbc_cache.json   # DBC 预解析缓存
├── templates/
│   └── 分析报告模板.md      # 报告模板（已弃用，模板已嵌入代码）
├── config/
│   └── config.ini           # 配置文件
└── references/              # 参考文档
    ├── Apple规范/
    ├── CCC联盟/
    └── 公司内部/
```

## 知识分层原则

- **官方权威**：Apple/CCC 规范定义的协议行为、流程节点、技术要求。遇到协议类问题时，**以 Apple Spec R4 为准**。
- **内部补充**：内部调试发现的具体日志标记、TCI 值、故障模式、操作技巧。

详见 `knowledge/00_索引.md` 中的「官方参考文档」章节。

## 知识库

详细故障域知识见 `knowledge/` 目录。按问题类型组织，新增故障模式只需添加文档，无需修改核心代码。

## 使用方法

### 方式1：完整流程（推荐）

```bash
python "C:\Users\WP6KCF2\.config\opencode\skills\ccc-debug\scripts\analyze_debug.py" VCTCEM-23462
```

流程：JIRA 信息获取 → 下载附件 → 解压 → 规则分析 → AI 深度分析

### 方式2：跳过 JIRA 获取，直接分析已解压日志

```bash
python "C:\Users\WP6KCF2\.config\opencode\skills\ccc-debug\scripts\analyze.py" VCTCEM-23462 --extracted-dir "Y:\JIRA_Logs\VCTCEM-23462\extracted" --output-dir "Y:\JIRA_Logs\VCTCEM-23462\分析过程"
```

用于快速调试 prompt 或分析本地日志。

## 工作流程

1. **JIRA 信息获取** → `get_ticket_detail.py --json` 获取 Summary/Description/Comments/Issue Analysis
2. **下载附件** → 使用 `Jira_access` skill 下载 JIRA 附件
3. **解压日志** → `analyze_debug.py` 自动解压 .zip/.tar.gz/.001/.7z 分卷压缩包
4. **规则分析** → `analyze.py` 关键词匹配 → 生成 `规则分析报告_时间戳.md`
5. **AI 深度分析** → 调用 opencode AI（prompt 含 JIRA+日志+DBC缓存，300KB 截断保护） → 生成 `完整分析报告_时间戳.md`

## 输出文件

- `分析过程/规则分析报告_YYYY-MM-DD_HH-MM-SS.md` - 规则引擎分析报告（关键词匹配结果）
- `分析过程/完整分析报告_YYYY-MM-DD_HH-MM-SS.md` - AI 深度分析报告（结构化完整报告，按时间戳存档）

## 性能参考

运行 `analyze_debug.py` 时会打印各步骤实际耗时，典型耗时分布（VCTCEM-16673 实测）：

| 步骤 | 典型耗时 |
|------|----------|
| JIRA 信息获取 | ~2s |
| 规则报告生成（5个日志函数 + 故障分类 + 写文件） | ~4s |
| AI 深度分析（扫描 + 读内容 + opencode推理） | ~50-60s（网络波动） |
| **总耗时** | **~60s** |

`analyze_backend_logs` 对大文件（>5MB）有过滤，规则引擎各函数最多取前 15 条匹配，不影响分析质量。

- Python 3.7+
- 7-Zip (用于解压 .001/.7z 分卷压缩包)
- opencode (用于 AI 分析)


