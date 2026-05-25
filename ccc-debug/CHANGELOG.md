# CCC Debug Skill CHANGELOG

> 本文档为开发记录，实际 debug 过程请参考 **SKILL.md**

---

## 当前状态（v4.11）

- **版本**：v4.11（2026-05-21）
- **前版本**：v4.10（2026-05-20）
- **核心脚本**：`scripts/analyze.py` / `scripts/analyze_debug.py`
- **知识库**：`knowledge/` 目录（6 个故障域文档）
- **知识摘要**：`scripts/cache/knowledge_summaries.json`（6 文件 ~5KB 摘要，按问题类型按需注入）
- **DBC 缓存**：`scripts/cache/dbc_cache.json`（225 条 CAN 消息，按需加载）
- **AI 模型**：`LiteLLM/MiniMax-M2.5`（timeout 900s）
- **时间过滤**：L2 自适应窗口（精确时间 → ±5min → ±15min）
- **日志优化**：日志文本为 0 时跳过 AI；按需选择性注入知识库和 DBC
- **Prompt 精简**：知识摘要按问题类型 + DBC 按需判断，预期减少 50% prompt 体积
- **JIRA 强依赖**：JIRA 获取失败（超时/解析错误）直接退出，不再跳过继续

---

## 迭代简史

| 版本 | 日期 | 里程碑 |
|------|------|--------|
| v4.12 | 2026-05-22 | **预置证书检测**：新增 `DK_SERVICE_PATTERNS` 关键词 `factory/certificate/preset`、`vehicleCert`、`ccc preset`、`ble preset`；新增 `backend.md` 预置证书章节，含 API 路径、日志特征、成功/失败判断<br>**BugFix**：`analyze_debug.py` 函数内 `import os` 导致变量覆盖错误 |
| v4.11 | 2026-05-21 | **JIRA 强依赖**：JIRA 获取失败（超时/解析错误/脚本缺失）直接 `sys.exit(1)` 退出，不再跳过继续分析<br>**时间过滤优化**：解析到精确时间后，结束时间增加 1 分钟缓冲，确保包含结束分钟的日志<br>**批量验证**：10 个 tickets 重跑验证（配对失败 3 个、钥匙分享 3 个、NFC刷卡 3 个、UWB测距 1 个），平均耗时 54s |
| v4.10 | 2026-05-20 | **时间过滤 L2 自适应窗口**：从 JIRA 提取精确时间段（16:33-16:34），精确够用则停止，不够再扩展（±5min → ±15min）<br>新增 `parse_time_range_from_str()` 解析时间段格式<br>`detect_issue_type_from_jira()` 从 JIRA 摘要关键词兜底检测问题类型<br>**AI Prompt 按需注入**：知识摘要按问题类型选择（只注入 1-2 个相关文件）<br>DBC 按需判断（问题涉及 CAN + 日志有 ASC/BLF 才加载）<br>Snippets > 30 行时减少原始日志读取（15文件→5文件）<br>**流式时间过滤**：逐行流式读取 + 行号索引，解决 37MB CAN 超时问题<br>**AI 重试机制**：最多 3 次指数退避重试（5s/10s）<br>验证 VCTCEM-13403：总耗时 135s（AI 127s），prompt 21KB |
| v4.9 | 2026-05-19 | **模型优化**：指定 `--model LiteLLM/MiniMax-M2.5`，timeout 900s<br>**日志优化**：日志文本为 0 时跳过 AI 分析，直接生成规则报告<br>日志 < 1KB 时使用简化 prompt<br>**时间过滤 v1**：新增 `extract_problem_time()` + `is_in_time_window()`，5 个日志读取函数支持时间窗口过滤<br>**批量完成**：配对/创建失败 25 个全部完成，其中 20 个有根因定位<br>**API Key**：切换到 `sk-A0faKwUmUjLP9xFt_eRyiA` |
| v4.8 | 2026-05-18 | **知识库验证与修正**：通过 VCTCEM-6549/10825/14321 三个 ticket 交叉验证，修正 `ccc_pairing.md` 知识库<br>803C 状态码从 4 个扩展到 11 个，新增 1002/4088/4081/4082/01B0/0100/0000<br>新增 Control Flow p1/p2 状态码表（8 种状态）<br>修正 ecp[4] 值描述（平台相关：多数=8，VW MEB=1）<br>**BugFix**：`knowledge_summaries.json` 读取编码修复（utf-8 → utf-8-sig）<br>**邮件功能**：分析完成后自动发送 HTML 邮件（含 JIRA 超链接）<br>**AI 约束增强**：新增第 10-12 条强制填写真实内容<br>**批量验证**：已完成 19/25 |
| v4.7 | 2026-05-16 | 新增知识库摘要自动注入：6个 knowledge 文件生成 ~4KB 摘要<br>每个知识域/章节标注 reliability (high/medium/low) + source 来源<br>AI prompt 新增约束第8条（引用知识库章节）+ 可信度提示<br>`analyze.py` 新增 `load_knowledge_summaries()` 函数<br>**BugFix**：`analyze.py` opencode 路径错误修复（`node opencode` → `opencode.exe`）<br>**BugFix**：`Jira_access/get_ticket_detail.py` 评论获取添加分页参数<br>**优化**：`analyze_debug.py` 评论取全部 + 标注"[需日志验证]"<br>AI prompt 新增约束第9条：评论仅供参考，需结合日志交叉验证 |
| v4.6 | 2026-05-15 | 根因分布修正：配对失败26个重跑（车企后台12/车端7/手机端3/苹果后台1/双重2）<br>修正4个根因（6549/10825/14482/20667）<br>重跑后7章完整 |
| v4.5 | 2026-05-14 | 修复二进制 VW 文件导致乱码（排除 .vw）<br>扩展跳章节修复<br>批量验证钥匙分享失败 9 个（8 OK / 1 WARN）<br>知识库更新：新增 90000008/99990004 错误码、车端脏数据、LocalPassNotFound、nginx 配置遗漏<br>修复 knowledge-platform debug.py 路径<br>增强 AI header 禁止 think 输出<br>新增后处理过滤 Chinese think 文本（"让我先查看"等）<br>批量下载配对/创建失败 26 个 tickets |
| v4.4 | 2026-05-14 | 修复 AI 跳过"一、JIRA 信息"章节：自动前置 JIRA 上下文<br>验证 VCTCEM-22690 + VCTCEM-19212（无日志模式） |
| v4.3 | 2026-05-12 | Ticket 全量分类（66条/13类）<br>`ccc_pairing.md` 重构为6章结构<br>新增 ECP cccop/bindkeyid2mac 知识点<br>新增 `backend.md`（数字钥匙后端服务配置问题）<br>路径 `原始Attachments` 统一改为 `Attachments`<br>AI prompt 加格式强制约束（7章节+日志路径必须带完整路径） |
| v4.2 | 2026-05-12 | 固定 AI 报告7章节模板<br>归一化后处理（`###` → `##`）<br>Python 3.15 全角标点替换（全文件 `：` `，` → ASCII） |
| v4.1 | 2026-05-11 | 耗时埋点统计<br>`analyze_backend_logs` 优化（34s→0.4s）<br>AI 报告过滤 `` 思考块+开篇废话 |
| v4.0 | 2026-05-11 | 知识库重构 |
| v3.x | 2026-05-10 | analyze.py 多问题支持 + 证据分类 + DBC 缓存 |
| v3.0 | 2026-05-09 | knowledge/ 目录拆分，SKILL.md 精简 |
| v2.6 | 2026-05-09 之前 | 单文件 SKILL.md（737行） |

---

## Ticket 分类（CCC Sync 66条，全量）

> 注：后台/URL配置错误（2条）不建知识库，属于数字钥匙后端服务配置问题，非CCC协议层调试范畴。

| 类型              | 数量 | 占比 | Tickets |
|-------------------|------|------|---------|
| 配对/创建失败       | 25   | 38%  | 6549, 7900, 9461, 10130, 10825, 14321, 14482, 14519, 17212, 17996, 19504, 20449, 20667, 20677, 21031, 21967, 22135, 27525, 28325, 30734, 22248, 35791, 13300, 14346, 15923 |
| 钥匙分享失败       | 9    | 14%  | 7531, 9314, 9316, 14302, 22233, 22690, 26376, 29194, 11021 |
| NFC刷卡/启动无提醒  | 3    | 5%   | 10551, 12821, 16673 |
| 车控失败           | 2    | 3%   | 14281, 24495 |
| UWB异常            | 5    | 8%   | 13343, 13403, 21405, 11016, 11018 |
| PE/Polling启停异常  | 5    | 8%   | 11017, 11019, 11020, 13342, 19212 |
| 钥匙注销/删除异常   | 3    | 5%   | 28261, 29187, 12144 |
| 后台/URL配置错误    | 2    | 3%   | 29351, 36257 |
| BLE入口异常        | 2    | 3%   | 14342, 14381 |
| 物理钥匙FOB        | 1    | 2%   | 13323 |
| 非CCC问题          | 9    | 14%  | 11193, 12620, 15023, 16263, 16265, 29144, 25315, 22234, 24235 |

### PE/Polling启停异常（5个）批量验证详情

| Ticket | 附件数 | 解压数 | 日志情况 | 质量 | 问题端 | v4.11 根因 |
|--------|-------:|-------:|----------|:----:|:------:|:----------:|
| VCTCEM-11017 | 3 | 0 | 7z分卷(缺.004) | 无效 | 日志缺失 | 分卷压缩不完整，无法解压 |
| VCTCEM-11019 | 2 | 1 | CAN .asc | OK | 待分析 | 车端 - CAN chip status error active，BLE通信异常 (267.4s) |
| VCTCEM-11020 | - | - | - | - | - | 待验证 |
| VCTCEM-13342 | - | - | - | - | - | 待验证 |
| VCTCEM-19212 | 0 | 0 | 无附件 | 无日志 | 日志缺失 | |

### NFC刷卡/启动无提醒（3个）批量验证详情

| Ticket | 附件数 | 解压数 | 日志情况 | 质量 | 问题端 | v4.11 根因 |
|--------|-------:|-------:|----------|:----:|:------:|:----------:|
| VCTCEM-10551 | 1 | 0 | 无附件 | 无日志 | - | 日志缺失 - 车内NFC TCI值不匹配（010383 vs 010673）(2.8s) |
| VCTCEM-12821 | 2 | 1 | VW二进制 | 无效 | 日志缺失 | 日志缺失 - 二进制日志无可读文本 (3.6s) |
| VCTCEM-16673 | 12 | 5 | .log+.clog+.txt+.vw | OK | 车端 | 车端 - NFC SE访问失败(sw=0x6400) + ECP未配置/TBOX刷写问题 (114.5s) |

### UWB测距（5个）批量验证详情

| Ticket | 附件数 | 解压数 | 日志情况 | 质量 | 问题端 | v4.11 根因 |
|--------|-------:|-------:|----------|:----:|:------:|:----------:|
| VCTCEM-13403 | - | - | - | OK | 待分析 | （已验证通过，无变化）(135s) |

### 钥匙分享失败（9个）批量验证详情

| Ticket | 附件数 | 解压数 | 日志情况 | 章节 | 大小 | 质量 | v4.10 根因 | v4.11 根因 |
|--------|-------:|-------:|----------|:----:|-----:|:----:|:----------:|:----------:|
| VCTCEM-7531 | 12 | 1 | VW二进制(470MB) | 3/7 | 2.4KB | OK(简化) | 车企后台 Pretrack 服务未将分享钥匙的 keyId 下发到车端 | 手机端 - 小米手机keyId生成问题，verify_friendattestation时keyId不匹配 (65.0s) |
| VCTCEM-9314 | 4 | 0 | OneApp.log+HTML+截图 | 7/7 | 2.8KB | OK | | 日志缺失 - 车端脏数据问题（shareAttestationTlv slotId与预置不符，JIRA评论已定位）(4.9s) |
| VCTCEM-9316 | 8 | 0 | 8张截图 | 7/7 | 2.8KB | OK | | |
| VCTCEM-14302 | 0 | 0 | 无附件 | 7/7 | 3.2KB | OK | | |
| VCTCEM-22233 | 12 | 0 | 7z分卷(800MB)+视频+zip | 7/7 | 2.5KB | OK | | |
| VCTCEM-22690 | 12 | 31 | VW+OneApp+Flutter+TouchGo | 8/7 | 3.8KB | OK | | |
| VCTCEM-26376 | 5 | 0 | dk_service.log+截图+视频 | 7/7 | 2.7KB | OK | | |
| VCTCEM-29194 | 22 | 6 | OneApp+Flutter+TouchGo | 7/7 | 7.0KB | OK | | |
| VCTCEM-11021 | 1 | 0 | 1张截图 | 7/7 | 2.5KB | OK | | 日志缺失 - 钥匙数量显示问题（最多5对显示，超出不显示） (2.7s) |

> 2026-05-14 批量验证钥匙分享失败9个，8 OK / 1 WARN。7531=二进制VW仅3章；29194=重跑后7章节完整。
>
> 2026-05-21 v4.11 批量验证：配对失败3个 ✓、钥匙分享3个（N/A2 + 无日志1）、NFC刷卡3个（N/A2 + 待分析1）、UWB测距1个 ✓。平均耗时54s（含AI分析）。


### 配对/创建失败（25个）批量验证详情

| Ticket | 附件数 | 提取数 | 日志类型 | 大小 | 质量 | 问题端 | v4.10 根因 | v4.11 根因 |
|:-------|-------:|-------:|---------|-----:|:----:|:------:|:----------:|:----------:|
| **v4.11 重跑验证（3个）** | | | | | | | | |
| VCTCEM-6549 | 15 | 4 | .vw+.log+.asc+.ubin | 4.2KB | OK | 手机端 | 车端 - NFC ECP cccop=2只读模式，sw=0x6400，Phase2失败 | 手机端 - Android设备发起OOB配对，与CCC CarKey协议不兼容 (55.8s) |
| VCTCEM-10825 | 11 | 9 | .vw+.log+.ubin+.asc | 3.5KB | OK | 车端 | 车端 - 配置字cccop=2 + CWCD v08检测逻辑错误(已修复) | 车端+车企后台 - NFC ECP只读模式(cccop=2) + CWCD状态异常(08→01) + 后台API异常(HTTP error) (95.0s) |
| VCTCEM-14321 | 6 | 65 | .log+.clog+.txt | 2.7KB | OK | 车端 | 车端 - NFC ECP cccop=2只读模式，sw=0x6400，Phase2失败 | 车端+手机端 - TouchGo模块Backend URL配置错误(http://localhost) + 车端BLE通信异常(recv_cb error) (137.8s) |
| **已验证** | | | | | | | | |
| VCTCEM-10130 | 8 | 13 | .log+.clog+.txt | 4.0KB | OK | 车企后台 | 后台 - Pretrack服务返回99990004 DEFAULT_ERROR，data:false | |
| VCTCEM-7900 | 3 | 0 | 截图+xlsx | 2.8KB | 无日志 | 车端 | 车端 - NFC天线距离不满足MFi要求(≥4cm)，硬件设计问题 | |
| VCTCEM-9461 | 3 | 0 | csv+html | 2.5KB | 无日志 | 车端 | 车端 - NFC使用旧版本(007)，VR36/013版本才支持CCC spec | |
| VCTCEM-14482 | 2 | 1 | .log | 1.5KB | OK | 车端 | 车端 - sw=0x6400 SE访问失败，cccop=2只读模式 | |
| VCTCEM-14519 | 5 | 114 | .log+.clog+.txt | 3.3KB | OK | 手机端 | 手机端 - SDK缓存未刷新，删除钥匙后仍使用旧KeyID发起配对 | |
| VCTCEM-17212 | 9 | 9 | .log+.clog+.txt+.vw | 1.4KB | 简化 | 车企后台 | 后台 - 90000008 人车关系不存在，解绑后无法配对 | |
| VCTCEM-17996 | 12 | 17 | 多类型 | 158KB | OK | 车企后台 | 后台 - 90000008 人车关系不存在（Issue: 待复现后再提） | |
| VCTCEM-19504 | 4 | 169 | 多类型 | 1.5KB | 简化 | 车企后台 | 后台 - 90000008 人车关系不存在 | |
| VCTCEM-20449 | 1 | 1 | .log | 9.1KB | OK | 车企后台 | 后台 - TBOX DNS解析失败(xmart.uat.cn-vwa.volkswagen-cea.com)，配置获取阶段失败 | |
| VCTCEM-20667 | 9 | 14 | .log+.clog+.txt+.vw | 4.0KB | OK | 车端+车企后台 | 车端 - Profile未配置 + nfcKeyFunState=-1(SE未配置ECP) + 后台90000011(订阅关系缺失) | |
| VCTCEM-20677 | 15 | 18 | .vw+.log+.clog+.txt+.ubin | 3.7KB | WARN | 车企后台 | 后台 - 90000008/90000011 钥匙分享(First Friend)绑定关系解绑 | |
| VCTCEM-21031 | 4 | 2 | .log+.txt | 3.4KB | OK | 车企后台 | 后台 - 90000008 人车关系不存在 | |
| VCTCEM-21967 | 8 | 52 | .log+.clog+.txt | 4.0KB | OK | 车端+车企后台 | 车端 - nfcKeyFunState=-1(SE未配置ECP) + 后台90000011(订阅关系缺失) | |
| VCTCEM-22135 | 14 | 5 | .ubin+.log+.txt | 3.5KB | OK | 车企后台 | 后台 - 90000011 OAuth鉴权失败，订阅关系缺失 | |
| VCTCEM-28325 | 7 | 12 | .vw+.log+.clog+.txt | 3.0KB | OK | 手机端 | 手机端 - 后台返回data:false，配对API失败，日志过简无法准确定位 | |
| VCTCEM-30734 | 13 | 1 | .vw | 2.3KB | 日志缺失 | 日志缺失 | 日志为二进制.vw，无可读文本，无法定位 | |
| VCTCEM-27525 | 5 | 7 | .log+.txt | 0.8KB | 简化 | 车企后台 | 后台 - REJECTED_BY_BACKEND，后台拒绝加载车辆数据 | |
| VCTCEM-22248 | 3 | 9 | .log+.clog+.txt | 2.4KB | WARN | 日志缺失 | 仅有OneApp前端日志，无CCC配对关键日志（D级），无法定位 | |
| VCTCEM-35791 | 2 | 12 | .log | 2.8KB | OK | 手机端 | 手机端 - ICS SDK permission check失败，后台权限不足 | |
| VCTCEM-13300 | 10 | 1 | .vw | 3.8KB | OK | 车企后台 | 后台 - 90000008 人车关系不存在（配对过程中被其他设备解绑） | |
| VCTCEM-14346 | 12 | 1 | .vw | 1.3KB | 日志缺失 | 日志缺失 | 日志为二进制.vw，无可读文本，无法定位 | |
| VCTCEM-15923 | 9 | 1 | .ubin | 0.9KB | 日志缺失 | 日志缺失 | 日志为二进制.ubin，无可读文本，无法定位 | |
| VCTCEM-7900 | 3 | 0 | 截图+xlsx | 2.8KB | 无日志 | 车端 | 车端 - NFC天线距离不满足MFi要求(≥4cm)，硬件设计问题 |
| VCTCEM-9461 | 3 | 0 | csv+html | 2.5KB | 无日志 | 车端 | 车端 - NFC使用旧版本(007)，VR36/013版本才支持CCC spec |
| VCTCEM-14482 | 2 | 1 | .log | 1.5KB | OK | 车端 | 车端 - sw=0x6400 SE访问失败，cccop=2只读模式 |
| VCTCEM-14519 | 5 | 114 | .log+.clog+.txt | 3.3KB | OK | 手机端 | 手机端 - SDK缓存未刷新，删除钥匙后仍使用旧KeyID发起配对 |
| VCTCEM-17212 | 9 | 9 | .log+.clog+.txt+.vw | 1.4KB | 简化 | 车企后台 | 后台 - 90000008 人车关系不存在，解绑后无法配对 |
| VCTCEM-17996 | 12 | 17 | 多类型 | 158KB | OK | 车企后台 | 后台 - 90000008 人车关系不存在（Issue: 待复现后再提） |
| VCTCEM-19504 | 4 | 169 | 多类型 | 1.5KB | 简化 | 车企后台 | 后台 - 90000008 人车关系不存在 |
| VCTCEM-20449 | 1 | 1 | .log | 9.1KB | OK | 车企后台 | 后台 - TBOX DNS解析失败(xmart.uat.cn-vwa.volkswagen-cea.com)，配置获取阶段失败 |
| VCTCEM-20667 | 9 | 14 | .log+.clog+.txt+.vw | 4.0KB | OK | 车端+车企后台 | 车端 - Profile未配置 + nfcKeyFunState=-1(SE未配置ECP) + 后台90000011(订阅关系缺失) |
| VCTCEM-20677 | 15 | 18 | .vw+.log+.clog+.txt+.ubin | 3.7KB | WARN | 车企后台 | 后台 - 90000008/90000011 钥匙分享(First Friend)绑定关系解绑 |
| VCTCEM-21031 | 4 | 2 | .log+.txt | 3.4KB | OK | 车企后台 | 后台 - 90000008 人车关系不存在 |
| VCTCEM-21967 | 8 | 52 | .log+.clog+.txt | 4.0KB | OK | 车端+车企后台 | 车端 - nfcKeyFunState=-1(SE未配置ECP) + 后台90000011(订阅关系缺失) |
| VCTCEM-22135 | 14 | 5 | .ubin+.log+.txt | 3.5KB | OK | 车企后台 | 后台 - 90000011 OAuth鉴权失败，订阅关系缺失 |
| VCTCEM-28325 | 7 | 12 | .vw+.log+.clog+.txt | 3.0KB | OK | 手机端 | 手机端 - 后台返回data:false，配对API失败，日志过简无法准确定位 |
| VCTCEM-30734 | 13 | 1 | .vw | 2.3KB | 日志缺失 | 日志缺失 | 日志为二进制.vw，无可读文本，无法定位 |
| VCTCEM-27525 | 5 | 7 | .log+.txt | 0.8KB | 简化 | 车企后台 | 后台 - REJECTED_BY_BACKEND，后台拒绝加载车辆数据 |
| VCTCEM-22248 | 3 | 9 | .log+.clog+.txt | 2.4KB | WARN | 日志缺失 | 仅有OneApp前端日志，无CCC配对关键日志（D级），无法定位 |
| VCTCEM-35791 | 2 | 12 | .log | 2.8KB | OK | 手机端 | 手机端 - ICS SDK permission check失败，后台权限不足 |
| VCTCEM-13300 | 10 | 1 | .vw | 3.8KB | OK | 车企后台 | 后台 - 90000008 人车关系不存在（配对过程中被其他设备解绑） |
| VCTCEM-14346 | 12 | 1 | .vw | 1.3KB | 日志缺失 | 日志缺失 | 日志为二进制.vw，无可读文本，无法定位 |
| VCTCEM-15923 | 9 | 1 | .ubin | 0.9KB | 日志缺失 | 日志缺失 | 日志为二进制.ubin，无可读文本，无法定位 |

---

## 遗留问题（按优先级）

| 优先级 | 事项 | 状态 |
|--------|------|------|
| P0 | ASC 时间戳搜索：按问题时间点定位 CAN 日志片段 | ✅ 已优化（时间过滤 L2 自适应窗口） |
| P1 | AI 报告仍输出内部推理（ response） | ✅ 已优化（正则过滤 `` + 开篇废话） |
| P1 | 同一证据分类多处文件重复 | ⬜ 待优化 |
| P1 | AI 超时不稳定 | ✅ 已优化（按需注入知识库+DBC，预期减少 50% prompt） |
| P1 | JIRA 超时后跳过继续分析（根因缺失） | ✅ 已修复（v4.11：JIRA 获取失败直接退出） |
| P2 | `classify_fault()` 从 `knowledge/*.md` 动态加载故障模式 | ⬜ 待优化 |
| P2 | Polarion 对接 | ⬜ 待处理 |
| P2 | 批量重跑 52 个历史 ticket 验证分析质量 | 🔄 进行中（钥匙分享9个✓，配对26个已验证3个，NFC/UWB待深入） |
| P2 | 案例库 + 故障模式库积累 | ⬜ 长期 |

---

*更新日期：2026-05-21*
