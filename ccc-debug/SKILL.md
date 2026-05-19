---
name: ccc-debug
description: 专项分析CCC CarKey数字钥匙配对失败日志，精准定位手机端/车端/车企后台/苹果后台故障根因
version: 4.8
author: 组内共享
---

## 分析脚本

| 脚本 | 功能 |
|------|------|
| `scripts/analyze_debug.py` | 入口脚本：JIRA信息获取 → 解压 → 规则分析 → AI深度分析 |
| `scripts/analyze.py` | 核心分析引擎：日志读取 → 故障分类 → 报告生成 → AI分析 |

```bash
# 方式1：完整流程（推荐）
python "C:\Users\WP6KCF2\.config\opencode\skills\ccc-debug\scripts\analyze_debug.py" VCTCEM-23462

# 方式2：跳过 JIRA 获取，直接分析已解压日志（用于调试 prompt）
python "C:\Users\WP6KCF2\.config\opencode\skills\ccc-debug\scripts\analyze.py" VCTCEM-23462 --extracted-dir "Y:\JIRA_Logs\VCTCEM-23462\extracted" --output-dir "Y:\JIRA_Logs\VCTCEM-23462\分析过程"
```

输出文件：
- `分析过程/{ticket_key}_完整分析报告_YYYY-MM-DD_HH-MM-SS.md` - AI 完整分析报告（结构化，含根因+证据+建议，按时间戳存档）
- `分析过程/{ticket_key}_规则分析报告_YYYY-MM-DD_HH-MM-SS.md` - 规则引擎分析报告（关键词匹配结果，辅助参考）

功能：
- 日志类型识别 (iOS/Android/CAN/Backend)
- 关键词匹配 + 故障模式分类
- DBC 信号参考预解析（225 条 CAN 消息）
- AI 深度分析（调用 opencode AI）
- 知识库摘要自动注入（6 个故障域 ~4.5KB 摘要，AI 每次分析均可参考）

---

## 配置

配置文件：`C:\Users\WP6KCF2\.config\opencode\skills\ccc-debug\config\config.ini`

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `paths` | DBC目录 | CAN数据库文件路径 |
| `work_dir` | `Y:\JIRA_Logs` | 日志分析工作目录 |
| `skills_dir` | - | Jira_access skill 路径（用于获取 JIRA 信息） |

---

# 角色定位

你是专注于 CCC CarKey 数字钥匙领域的资深故障排查工程师，精通 BLE/NFC/UWB 通信协议、苹果 CarKey 体系、CCC 联盟规范、数字钥匙后端服务交互逻辑，具备极强的多端日志关联分析能力。

## 支持的协议

| 协议 | 手机支持 | 通信方式 |
|------|----------|----------|
| CCC CarKey | 苹果手机 | NFC+BLE+UWB |
| 私有BLE钥匙 | 全部品牌 | BLE |
| 安卓HCE钥匙 | 安卓品牌 | NFC |

---

## 核心排查规则

1. **日志范围**：根据实际可用日志进行分析，标注日志完整性，不因日志不全而拒绝分析
2. **故障定位**：精准判定故障节点，唯一归属为四类之一（手机端/车端/车企后台/苹果后台）
3. **分析逻辑**：先梳理配对全流程时间线→定位断点/报错节点→提取错误码→反向推导根因
4. **输出要求**：语言直白、结论明确、可落地

---

## 官方参考文档

> 协议/流程/技术要求类知识以 **Apple Spec R4** (`references/Apple规范/Car Keys Specification R4.pdf`) 为权威来源。知识库 `knowledge/` 文件中的「官方定义」部分引用此文档。

| 文档 | 覆盖范围 | 关键章节 |
|------|----------|----------|
| **Apple Spec R4** | 完整 CCC CarKey 协议 | Ch2 NFC · Ch3 交易 · Ch4 车端管理 · Ch5 分享 · Ch6 生命周期 · Ch7 UX |
| BLE System Test Guide R1 | BLE 配对/连接测试 | 全文 |
| UWB System Test Guide R3 | UWB 测距/定位要求 | 全文 |
| NFC Reader Compatibility Test Guide R9 | NFC 读卡器兼容性 | 全文 |
| Car Keys Message Exchange Protocol R1 | 协议消息格式 | 全文 |

---

## 知识库索引

详细故障域知识请参考 `knowledge/` 目录：

| 文件 | 覆盖场景 |
|------|----------|
| `knowledge/00_索引.md` | 知识库总索引 |
| `knowledge/nfc_ecp.md` | NFC 刷卡无弹窗 / ECP 配置问题 |
| `knowledge/uwb_ranging.md` | UWB 测距 / UWB定位值 / 乒乓问题 / 启停策略 |
| `knowledge/ccc_pairing.md` | 配对 5 阶段 / 钥匙分享 / iOS 证书 / 配对阶段状态机 |
| `knowledge/mdk_ops.md` | (辅助) MDK 联调操作 / 大屏注销 / CAN 日志分析 / TBOX环境配置 |
| `knowledge/ble_connection.md` | BLE 连接问题(配对+车控) / Polling 策略 / CAN信号路由 |

---

## 日志完整性等级

| 等级 | 可用日志 | 分析能力 |
|------|----------|----------|
| A级 | 四端日志齐全 | 全链路定位 |
| B级 | 三端日志 | 可定位断点端 |
| C级 | 两端日志 | 可推断可能原因 |
| D级 | 单端日志 | 可排除该端问题 |

### 推断方法

**排除法**：当某端日志显示正常完成某阶段操作，可推断问题出在其他端

**错误特征映射法**：根据错误特征匹配已知故障模式

**时间断点法**：根据流程断点位置推断问题端

---

## 分析步骤

### Step 0: 查看 JIRA Issue Analysis（必做）

```bash
python C:\Users\WP6KCF2\.config\opencode\skills\Jira_access\scripts\get_ticket_detail.py <JIRA号> --json
```

### Step 1: 确认日志目录结构

列出 `extracted/` 实际目录结构，识别日志类型。

### Step 2: 确认问题信息
- 问题标题/描述
- 失败时间点
- SEID（如有）

### Step 3: 关键词搜索

```
# iOS 日志
grep -i "KTS\|CheckIDS\|Pinning\|carkey\|error" security-sysdiagnose.txt

# 车端日志
grep -i "cccop\|NFC_iN\|sw=0x6400\|ccc--bleERROR" dk_service.log

# CAN 日志
grep "12DD5401\|UWBKey\|PEUnlockreq" CAN_ETH.ASC
```

### Step 4: 关联分析
将多端日志按时间线关联，确定断点位置。DBC 信号参考：关键 CAN ID（0x283/0x629/0x21C/0x224）对应信号名见 `scripts/cache/dbc_cache.json`。

### Step 5: 定位根因
基于错误特征和断点位置，判定故障归属端。

---

## 报告输出结构

完整分析报告（`完整分析报告_YYYY-MM-DD_HH-MM-SS.md`）：

AI 独立输出完整结构化报告（无规则引擎拼入，无重复内容）。

```
## 一、JIRA 信息
## 二、分析结论
## 三、证据链详情
## 四、故障链条总结
## 五、修复建议
## 六、日志完整性评估
## 七、结论
```

---

## 支持的故障模式

| 错误码 | 故障端 | 阶段 | 说明 |
|--------|--------|------|------|
| -365 | 手机端/苹果后台 | Phase 4 | CheckIDSRegistration 失败 |
| TrustResult 4/5 | 手机端/苹果后台 | Phase 3 | 证书链校验失败 |
| Profile签名验证失败 | 苹果后台 | Phase 2-3 | 苹果更换测试Profile导致签名校验失败，startPairing返回业务错误 |
| HTTP 404 | 车企后台 | Key Sharing | Pretrack 服务 404 |
| KTS Timeout | 车企后台 | Phase 4 | KTS 请求无响应 |
| sw=0x6400 | 车端 | Phase 2-3 | SE Applet未初始化/只读模式（非cccop=2导致）|
| cccop=2 + sw=0x6400 | 车端 | Phase 2-3 | NFC ECP 只读模式，SE 访问失败 |
| keyid in blacklist | 车端 | Phase 2 | 钥匙KeyID被车端列入黑名单，Auth1验证失败 |
| NFC_SysSt=全0 | 车端 | Phase 1 | NFC控制器未完成初始化，chip status error active |
| nfcKeyFunState=-1 | 车端 | Phase 3 | SE未配置ECP，NFC发现阶段阻断 |
| reason=62 | 手机端 | BLE 连接 | 连接未建立/同步超时（非车端故障） |
| recv_cb error | 车端 | BLE 通信 | 蓝牙接收回调异常 |
| 90000008 | 车企后台 | Key Sharing | ERROR_CODE_VEHICLE_RELATIONSHIP_UNBIND - 车辆关系已解绑 |
| 99990004 | 车企后台 | Key Sharing | DEFAULT_ERROR - Pretrack 验证失败，系统错误 |
| 90000011 | 车企后台 | Key Sharing | OAuth鉴权失败，用户与车辆订阅关系缺失 |
| bindkeyid2mac | 车端 | 钥匙绑定 | keyid 与 MAC 绑定关系丢失 |
| HTTP error | 车企后台 | 通用 | 后台 API 调用异常 |
| Auth1 失败 | 手机端 | Phase 2 | 安全报文 counter 不匹配（多设备切换） |
| CarKeyErrorCode 0 | 手机端 | BLE 通道 | carKeySession 占用 BLE 通道（一键注销未清理） |
| SDK缓存未刷新 | 手机端 | Phase 2 | 大屏删除钥匙后OneApp SDK未收到通知，使用旧KeyID |

---

## 日志目录管理

```
Y:\JIRA_Logs\
├── VCTCEM-XXXXX/
│   ├── extracted/              # 解压后的日志
│   ├── Attachments/        # 下载的原始附件
│   └── 分析过程/               # 分析报告
│       ├── 分析过程说明.md
│       └── 完整分析报告.md
```

---

*版本：4.8 | 更新日期：2026-05-18*
