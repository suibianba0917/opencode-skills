# CCC Debug Skill CHANGELOG

> 本文档为开发记录，实际 debug 过程请参考 **SKILL.md**

---

## 当前状态（v4.7）

- **版本**：v4.7（2026-05-16）
- **前版本**：v4.6（2026-05-15）
- **核心脚本**：`scripts/analyze.py` / `scripts/analyze_debug.py`
- **知识库**：`knowledge/` 目录（6 个故障域文档）
- **知识摘要**：`scripts/cache/knowledge_summaries.json`（6 文件 ~5KB 摘要，标注 reliability+source，每次分析自动注入 AI prompt）
- **DBC 缓存**：`scripts/cache/dbc_cache.json`（225 条 CAN 消息）
- **性能**：规则报告生成 ~4-5s，AI 分析 ~12-55s（网络波动），总耗时 ~19-60s

---

## 迭代简史

| 版本 | 日期 | 里程碑 |
|------|------|--------|
| v4.7 | 2026-05-16 | 新增知识库摘要自动注入：6个 knowledge 文件生成 ~4KB 摘要（`cache/knowledge_summaries.json`），每次分析时注入 AI prompt，AI 可自主引用知识域；每个知识域/章节标注 reliability (high/medium/low) + source 来源；AI prompt 新增约束第8条（引用知识库章节）+ 可信度提示；`analyze.py` 新增 `load_knowledge_summaries()` 函数；**BugFix**：`analyze.py` opencode 路径错误修复（`node opencode` → `opencode.exe`），修复后 AI 分析正常返回报告；`analyze_debug.py` debug 输出 `jira_context_str` 参数名修正 |
| v4.6 | 2026-05-15 | 根因分布修正：配对失败26个重跑（车企后台12/车端7/手机端3/苹果后台1/双重2）；修正4个根因（6549/10825/14482/20667）；重跑后7章完整 |
| v4.5 | 2026-05-14 | 修复二进制 VW 文件导致乱码（排除 .vw）；扩展跳章节修复；批量验证钥匙分享失败 9 个（8 OK / 1 WARN）；知识库更新：新增 90000008/99990004 错误码、车端脏数据、LocalPassNotFound、nginx 配置遗漏；细化 Pretrack keyId 未下发/BLE MAC RKE-PEPS/短信延迟；修复 knowledge-platform debug.py 路径（analyze_debug.py 从 Jira_access 改为 ccc-debug/scripts）；增强 AI header 禁止 think 输出；新增后处理过滤 Chinese think 文本（"让我先查看"等）；批量下载配对/创建失败 26 个 tickets |
| v4.4 | 2026-05-14 | 修复 AI 跳过"一、JIRA 信息"章节：检测到 AI 报告以"## 二、分析结论"开头时，自动前置 JIRA 上下文；验证 VCTCEM-22690 + VCTCEM-19212（无日志模式） |
| v4.3 | 2026-05-12 | Ticket 全量分类（66条/13类）；`ccc_pairing.md` 重构为6章结构；新增 ECP cccop/bindkeyid2mac 知识点；新增 `backend.md`（数字钥匙后端服务配置问题）；路径 `原始Attachments` 统一改为 `Attachments`；AI prompt 加格式强制约束（7章节+日志路径必须带原始日志+完整路径）；验证 VCTCEM-6549 + VCTCEM-16673 + VCTCEM-35791；`customfield_20765` Issue Analysis 字段名待确认 |
| v4.2 | 2026-05-12 | 固定 AI 报告7章节模板；归一化后处理（`###` → `##`）；Python 3.15 全角标点替换（全文件 `：` `，` → ASCII） |
| v4.1 | 2026-05-11 | 耗时埋点统计；`analyze_backend_logs` 优化（34s→0.4s）；AI 报告过滤 `` 思考块+开篇废话 |
| v4.0 | 2026-05-11 | 知识库重构 |
| v3.x | 2026-05-10 | analyze.py 多问题支持 + 证据分类 + DBC 缓存 |
| v3.0 | 2026-05-09 | knowledge/ 目录拆分，SKILL.md 精简 |
| v2.6 | 2026-05-09 之前 | 单文件 SKILL.md（737行） |

---

## Ticket 分类（CCC Sync 66条，全量）

> 注：后台/URL配置错误（2条）不建知识库，属于数字钥匙后端服务配置问题，非CCC协议层调试范畴。

| 类型              | 数量 | 占比 | Tickets |
|-------------------|------|------|---------|
| 配对/创建失败       | 26   | 39%  | 6549, 7900, 9461, 10130, 10825, 12144, 14321, 14482, 14519, 17212, 17996, 19504, 20449, 20667, 20677, 21031, 21967, 22135, 27525, 28325, 30734, 22248, 35791, 13300, 14346, 15923 |
| 钥匙分享失败       | 9    | 14%  | 7531, 9314, 9316, 14302, 22233, 22690, 26376, 29194, 11021 |
| NFC刷卡/启动无提醒  | 3    | 5%   | 10551, 12821, 16673 |
| 车控失败           | 2    | 3%   | 14281, 24495 |
| UWB异常            | 5    | 8%   | 13343, 13403, 21405, 11016, 11018 |
| PE/Polling启停异常  | 5    | 8%   | 11017, 11019, 11020, 13342, 19212 |
| 钥匙注销/删除异常   | 2    | 3%   | 28261, 29187 |
| 后台/URL配置错误    | 2    | 3%   | 29351, 36257 |
| BLE入口异常        | 2    | 3%   | 14342, 14381 |
| 物理钥匙FOB        | 1    | 2%   | 13323 |
| 非CCC问题          | 9    | 14%  | 11193, 12620, 15023, 16263, 16265, 29144, 25315, 22234, 24235 |

### 钥匙分享失败（9个）批量验证详情

| Ticket | 附件数 | 解压数 | 日志情况 | 章节 | 大小 | 质量 | 根因 |
|--------|-------:|-------:|----------|:----:|-----:|:----:|------|
| VCTCEM-7531 | 12 | 1 | VW二进制(470MB) | 3/7 | 2.4KB | OK(简化) | 车企后台 Pretrack 服务未将分享钥匙的 keyId 下发到车端，车端无法识别分享钥匙（NFC 解闭锁失败），建议排查 Pretrack 服务日志确认 keyId 下发链路；注：仅有二进制 VW 日志，AI 生成 3 章简化报告 |
| VCTCEM-9314 | 4 | 0 | OneApp.log+HTML+截图 | 7/7 | 2.8KB | OK | 车端存在脏数据（该车之前有数字钥匙数据未清理干净），共享钥匙处理逻辑通过 VIN 找到旧 keyId slot，导致分享钥匙拿到脏数据无法使用 |
| VCTCEM-9316 | 8 | 0 | 8张截图 | 7/7 | 2.8KB | OK | DK 服务端已发出领取通知短信，但短信被运营商拦截/延迟，消息在消息中心长时间未处理完成，导致接收方超时未领取 |
| VCTCEM-14302 | 0 | 0 | 无附件 | 7/7 | 3.2KB | OK | BLE 软件 MAC 地址上报配置有误，导致 CCC 分享钥匙仅有 NFC 功能但缺少 RKE 和 PEPS 功能（与 MiFi 认证流程相关） |
| VCTCEM-22233 | 12 | 0 | 7z分卷(800MB)+视频+zip | 7/7 | 2.5KB | OK | 两台苹果手机使用同一 iCloud 账号登录，AirDrop 接收端未正确响应；手机死机也可能为触发因素，重启后可复测 |
| VCTCEM-22690 | 12 | 31 | VW+OneApp+Flutter+TouchGo | 8/7 | 3.8KB | OK | 用户 uid:7167966776943219 与车辆 VIN:HVWPA3EG6S1300078 的绑定关系已在车企后台解绑，后台返回 ERROR_CODE_VEHICLE_RELATIONSHIP_UNBIND（90000008），钥匙分享被拒绝 |
| VCTCEM-26376 | 5 | 0 | dk_service.log+截图+视频 | 7/7 | 2.7KB | OK | DK 后端 nginx 配置遗漏了部分车型的 CCC 访问路径配置，属于 corner case，导致钥匙分享后接收方领取请求被 404 |
| VCTCEM-29194 | 22 | 6 | OneApp+Flutter+TouchGo | 7/7 | 7.0KB | OK | 用户在 App 内添加了数字钥匙但未完成苹果 CarKey 注册流程（LocalPassNotFound + data:false），CarKey Pass 未成功写入 Apple Wallet，建议联系苹果侧分析；Pretrack 返回 data:false + 99990004 |
| VCTCEM-11021 | 1 | 0 | 1张截图 | 7/7 | 2.5KB | OK | 无日志，仅截图显示无法共享凭证；可能涉及手机端钥匙存储数量限制（最多 16 把）或 iOS 系统版本兼容性问题，需补充系统日志排查 |

> 2026-05-14 批量验证钥匙分享失败9个，8 OK / 1 WARN。7531=二进制VW仅3章；29194=重跑后7章节完整。

### 配对/创建失败（26个）批量下载完成

| Ticket | 附件数 | 日志类型 |
|--------|-------:|----------|
| VCTCEM-6549 | 15 | ubin+OneApp.log+截图 |
| VCTCEM-7900 | 3 | 截图+xlsx |
| VCTCEM-9461 | 3 | csv+html+截图 |
| VCTCEM-10130 | 8 | zip+log+截图 |
| VCTCEM-10825 | 11 | ubin+zip+log+截图+7z分卷 |
| VCTCEM-12144 | 2 | log+视频 |
| VCTCEM-14321 | 6 | 视频+log+截图 |
| VCTCEM-14482 | 2 | log+截图 |
| VCTCEM-14519 | 5 | zip+log+截图 |
| VCTCEM-17212 | 9 | 截图+7z分卷(3) |
| VCTCEM-17996 | 12 | zip+视频(2)+7z+截图 |
| VCTCEM-19504 | 4 | 视频+zip+7z |
| VCTCEM-20449 | 1 | log |
| VCTCEM-20667 | 9 | zip(2)+视频+7z+截图 |
| VCTCEM-20677 | 15 | zip(2)+视频+7z(2) |
| VCTCEM-21031 | 4 | log+zip+视频(2) |
| VCTCEM-21967 | 8 | 视频+截图(4) |
| VCTCEM-22135 | 14 | zip+视频(2)+7z+截图 |
| VCTCEM-27525 | 5 | 视频+tar.gz(2)+zip |
| VCTCEM-28325 | 7 | zip+截图+视频+7z分卷 |
| VCTCEM-30734 | 13 | zip(2)+视频+7z+截图 |
| VCTCEM-22248 | 3 | zip+视频+截图 |
| VCTCEM-35791 | 2 | zip+视频 |
| VCTCEM-13300 | 10 | 截图+7z分卷(3) |
| VCTCEM-14346 | 12 | zip+视频+7z(2)+截图 |
| VCTCEM-15923 | 9 | 视频+7z(2)+截图 |

> 2026-05-14 下载完成，26 个全部有附件或确认无附件。下一步：批量跑分析。

### 配对/创建失败（26个）批量验证详情

| Ticket | 附件数 | 提取数 | 日志类型 | 章节 | 大小 | 质量 | 根因 |
|--------|-------:|-------:|---------|:----:|-----:|:----:|------|
| VCTCEM-6549 | 15 | 4 | .vw+.log+.asc+.ubin | 7 | 4.2KB | OK | 车端 - NFC SE Applet cccop=2 只读模式，sw=0x6400，Phase 2 配对失败 |
| VCTCEM-7900 | 3 | 0 | 截图+xlsx | 7 | 2.8KB | 无日志 | 无日志 - NFC 传感器 MFi 认证不通过 |
| VCTCEM-9461 | 3 | 0 | csv+html | 7 | 2.5KB | 无日志 | 无日志 - NFC 版本旧 |
| VCTCEM-10130 | 8 | 13 | .log+.clog+.txt | 7 | 4.0KB | OK | 车企后台 - getKeyInfoList 返回 data:false 导致 Android SDK JSON 解析崩溃 (99990004) |
| VCTCEM-10825 | 11 | 9 | .vw+.log+.ubin+.asc | 7 | 3.5KB | OK | 车企后台 - 车辆与用户关系已解绑 (90000008) |
| VCTCEM-12144 | 2 | 1 | .log | 7 | 2.3KB | OK | 手机端 - Android 密钥解密失败 (mbedtls_aes -0x6200) |
| VCTCEM-14321 | 6 | 65 | .log+.clog+.txt | 7 | 2.7KB | OK | 车端 - SE Applet 返回 sw=0x6400，Phase 2 Auth1 认证失败 |
| VCTCEM-14482 | 2 | 1 | .log | 7 | 1.5KB | OK | 车端 - SE Applet sw=0x6400，Auth1 验证失败 |
| VCTCEM-14519 | 5 | 114 | .log+.clog+.txt | 7 | 3.3KB | OK | 手机端 - 大屏删除钥匙后 OneApp SDK 缓存未同步，使用旧 KeyID 发起配对 |
| VCTCEM-17212 | 9 | 9 | .log+.clog+.txt+.vw | 7 | 1.4KB | 简化 | 车企后台 - 人车关系已解绑 (90000008) |
| VCTCEM-17996 | 12 | 1 | .ubin | 7 | 2.7KB | OK | 车企后台 - 人车关系已解绑 (90000008) |
| VCTCEM-19504 | 4 | 169 | 多类型 | 7 | 1.5KB | 简化 | 车企后台 - 人车关系已解绑 (90000008) |
| VCTCEM-20449 | 1 | 1 | .log | 7 | 9.1KB | OK | 车端 - TBOX 无法解析后台域名，DNS 解析失败 (curl: Couldn't resolve host name) |
| VCTCEM-20667 | 9 | 14 | .log+.clog+.txt+.vw | 7 | 4.0KB | OK | 车企后台 - 人车关系已解绑 (90000008) |
| VCTCEM-20677 | 15 | 18 | .vw+.log+.clog+.txt+.ubin | 7 | 3.7KB | WARN | 需补充日志 - 缺失 17pm iOS sysdiagnose |
| VCTCEM-21031 | 4 | 2 | .log+.txt | 7 | 3.4KB | OK | 车企后台 - 人车关系已解绑 (90000008) |
| VCTCEM-21967 | 8 | 52 | .log+.clog+.txt | 7 | 4.0KB | OK | 双重 - 车端 SE 未配置 ECP (nfcKeyFunState=-1) + 后台 OAuth 401 (90000011) |
| VCTCEM-22135 | 14 | 5 | .ubin+.log+.txt | 7 | 3.5KB | OK | 双重 - 后台订阅 API 401 (90000011) + 缺少 iOS 日志确认 6A80 |
| VCTCEM-27525 | 5 | 7 | .log+.txt | 7 | 0.8KB | 简化 | 车企后台 - 后台返回 REJECTED_BY_BACKEND |
| VCTCEM-28325 | 7 | 12 | .vw+.log+.clog+.txt | 7 | 3.0KB | OK | 苹果后台 - Profile 签名验证失败（苹果更换测试 Profile） |
| VCTCEM-30734 | 13 | 1 | .vw | 7 | 2.3KB | OK | 车企后台 - CEA Profile 状态异常，KTS 无法完成钥匙下发 |
| VCTCEM-22248 | 3 | 9 | .log+.clog+.txt | 7 | 2.4KB | WARN | 日志时间不匹配 - 需补充 17:46 日志 |
| VCTCEM-35791 | 2 | 12 | .log | 7 | 2.8KB | OK | 车企后台 - Failed to check permission，Profile 未下发 |
| VCTCEM-13300 | 10 | 1 | .vw | 7 | 3.8KB | OK | 车企后台 - 人车关系已解绑 (90000008) |
| VCTCEM-14346 | 12 | 1 | .vw | 7 | 1.3KB | 简化 | 知识库模式 - 无实际日志分析 |
| VCTCEM-15923 | 9 | 1 | .ubin | 7 | 0.9KB | 简化 | 知识库模式 - 无实际日志分析 |

> 2026-05-15 重跑后根因修正：配对/创建失败 26 个
>
> 修正 4 个：6549(后台→车端)、10825(车端→后台)、14482(后台→车端)、20667(未改但根因细化)
>
> 根因分布：车企后台 12 个 | 车端 7 个 | 手机端 3 个 | 苹果后台 1 个 | 双重 2 个 | 待补充 4 个

**根因分类汇总**：

| 故障端 | 数量 | 根因模式 |
|--------|-----:|----------|
| **车企后台** | 12 | 90000008 车辆关系解绑、99990004 API 错误、Profile 未下发、90000011 OAuth 失败 |
| **车端** | 7 | sw=0x6400、cccop=2、keyid blacklist、NFC 未上电、nfcKeyFunState=-1、TBOX DNS、receipt签名 |
| **手机端** | 3 | SDK 缓存未刷新、AES 解密失败、6A80 安全错误 |
| **苹果后台** | 1 | Profile 签名验证失败 |
| **双重** | 2 | 车端 SE + 后台 OAuth 双重问题 |
| 待补充 | 4 | 日志缺失或时间不匹配 |

---

## 遗留问题（按优先级）

| 优先级 | 事项 | 状态 |
|--------|------|------|
| P0 | ASC 时间戳搜索：按问题时间点定位 CAN 日志片段 | ⬜ 待优化 |
| P1 | AI 报告仍输出内部推理（ response） | ✅ 已优化（正则过滤 `` + 开篇废话） |
| P1 | 同一证据分类多处文件重复 | ⬜ 待优化 |
| P1 | AI 超时不稳定 | ✅ 已优化（prompt 300KB截断） |
| P2 | `classify_fault()` 从 `knowledge/*.md` 动态加载故障模式 | ⬜ 待优化 |
| P2 | Polarion 对接 | ⬜ 待处理 |
| P2 | 批量重跑 52 个历史 ticket 验证分析质量 | 🔄 进行中（钥匙分享9个✓，配对26个待分析） |
| P2 | 案例库 + 故障模式库积累 | ⬜ 长期 |

---

*更新日期：2026-05-16*
