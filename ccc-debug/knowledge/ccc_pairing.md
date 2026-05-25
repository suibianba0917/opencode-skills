# CCC 配对流程 / 钥匙分享

> **官方规范**：Apple Spec R4 — Ch3.2 Owner Pairing (p34) / Ch4.6 Owner Pairing (p65) / Ch5 Key Sharing (p69) / Ch7.1~7.2 OP Initiation (p96) / Ch6.1 First Friend Approach
> 📎 `references/Apple规范/Car Keys Specification R4.pdf`

---

## 1. 基础知识

### Owner Pairing 流程 5 阶段

详见 Apple Spec R4 **3.2 Owner Pairing via BLE** (p34) + **4.6 Owner Pairing** (p65)：

| Phase | 环节 | 涉及端 | 关键检查点 | 对应 NFC 交易 |
|-------|------|--------|-----------|--------------|
| Phase 1 | 初始化 / 检测 | 手机 + 车 | 蓝牙 / NFC 连接建立 | — |
| Phase 2 | 设备认证 | 手机 + 车 | SPAKE2+ 密钥交换 | SELECT → Auth0 → Exchange |
| Phase 3 | 证书交换 | 手机 + 车 + 后台 | 证书链校验 | Auth1 → Control Flow |
| Phase 4 | KTS 注册 | 手机 + 苹果后台 + 车企后台 | KTS 请求发起（Phase 3 证书交换期间）→ ABR 路由 → 响应写入 SE；ABR 配置 | Standard Transaction |
| Phase 5 | 钥匙写入 | 手机 + 车 | SE 写入、密钥存储 | — |

> **Phase ↔ Pairstatus 对照**：Pairstatus=0~4 对应 Phase 1~5，见第 2 章「配对阶段状态机」。

### Owner Pairing 初始化方式

详见 Apple Spec R4 **7.1 Owner Pairing Initiation: NFC** (p96) + **7.2 Owner Pairing Initiation (BLE and UWB)** (p99)：

- **方式1**：Apple Wallet URL 邮件链接
- **方式2**：车企 APP 内输入密码
- **方式3**：车企 APP 直接发起（无需密码）

### Key Sharing 完整流程

详见 Apple Spec R4 **Chapter 5 Key Sharing** (p69) + **7.4 Key Sharing Experience**：

| Stage | 环节 | 涉及端 | 关键检查点 |
|-------|------|--------|-----------|
| Stage 1 | 发起分享 | 手机端 | 钥匙选择、可分享数量检查 |
| Stage 2 | 邀请发送 | 手机端 + 车企后台 | iMessage/AirDrop 发送 |
| Stage 3 | 接收端处理 | 手机端 | 钥匙下载、KTS 注册准备 |
| Stage 4 | KTS 注册 | 手机端 + 苹果后台 + 车企后台 | Pretrack 响应、Key Tracking |
| Stage 5 | 首次车辆交易 | 手机端 + 车端 | First Friend Transaction、attestation 验证 |

### First Friend Approach（分享钥匙首次交易）

详见 Apple Spec R4 **6.1 First Friend Approach**：

Friend Device 和车建立蓝牙连接后，需完成一次 Standard Transaction 才算有效——这个过程称为 **First Friend Approach**。

流程：BLE Owner Pairing GATT Flow → First Friend Approach → Standard Transaction

### 密钥生命周期

详见 Apple Spec R4 **6.6 Key Life Cycle** (p87)：
- KeyID 使用规则（6.6.1）
- Digital Key Status（6.6.2）
- Key Termination and Suspend（6.6.3）

---

## 2. 车端日志标记

### NFC ECP cccop 只读模式

**日志关键词**：`NFC_iN ecp[4] = X,conf->cccop = 2`（ecp[4] 值平台相关，多数平台为 8，VW MEB 平台为 1）

`cccop` 决定 NFC ECP 读写模式：
- `cccop=1` = 读写模式（正常）
- `cccop=2` = 只读模式（异常）

**两种表现**：

| 表现 | cccop 何时异常 | 症状 | 参考 |
|------|---------------|------|------|
| Phase 2 配对中断 | 配对开始时 cccop=2 | sw=0x6400 写入失败，无法完成配对 | VCTCEM-6549 |
| NFC 刷卡无弹窗 | 配对时 cccop=1 成功，刷卡时变成 2 | ECP 配置配对后丢失，sw=0x6400 读取失败 | VCTCEM-16673 |

ECP 配置丢失说明配置未持久化（NVCM 未保存），需要在 NFC 初始化阶段增加 ECP 参数加载日志确认。

### 配对阶段状态机（Pairstatus）

> 注：Pairstatus 与 Phase 编号对应关系需参考车端 nfc.cpp 代码，以下为推测。

| Pairstatus | 对应 Phase | 含义 | 卡住时的根因 |
|------------|-----------|------|-------------|
| 0 | Phase 1 | 初始化 | NFC/BLE 连接未建立 |
| 1 | Phase 2 | 设备认证（SPAKE2+ 写入阶段）| SE/NFC 配置异常 |
| 2 | Phase 2~3 | 设备认证（读取阶段）→ 证书交换 | cccop/ECP 配置异常 |
| 3 | Phase 3~4 | 证书交换 → KTS 注册 | KTS/ABR 异常 |
| 4 | Phase 4~5 | 配对成功 | — |

---

## 3. dk_service.log 日志速查

### 3.1 ccc-- 日志前缀速查

> 来源：8 个 Ticket（6549/10130/10825/14321/14482/20449/21031/26376）交叉验证

| ccc-- 前缀 | 含义 | 阶段 |
|-----------|------|------|
| `ccc--nfc pair` | NFC 配对 transaction 开始 | Phase 2 启动 |
| `ccc--nfc pair--behind PAIRING22` | 开始 NFC 配对流程 | Phase 2 |
| `ccc--nfc pair--pair.status != PAIRED` | 检测到未配对，启动配对 | Phase 2 |
| `ccc--NFC` | NFC 模块操作/轮询 | Phase 1~3 |
| `ccc--write` | 写入证书/数据到 SE | Phase 2~5 |
| `ccc--read` | 读取 SE 数据 | Phase 2~3 |
| `ccc--statemachine` | 配对状态机运行 | Phase 2~4 |
| `ccc--statemachine--in ranging` | **开始 UWB 定位** | Phase 2→3 |
| `ccc--PubCb` | 定位 callback（locked/power 状态） | Phase 2→3 |
| `ccc--setuwb` | 设置 UWB 参数 | Phase 2→3 |
| `ccc--build_ragingsessionreq` | 构建 ranging session | Phase 2→3 |
| `ccc--finduwbsession` | 查找 UWB session | Phase 2→3 |
| `ccc--standard_transaction_step1to6` | NFC 标准交易步骤（1-6） | Phase 2~4 |
| `ccc--CCCKeydata` | 钥匙数据交换/持久化 | Phase 3~5 |
| `ccc--sync_capbilityrsp` | 交换能力信息 | Phase 2~3 |
| `ccc--del_statemachine` | 配对结束，清理状态机 | Phase 5 结束 |
| `ccc--BLE_DISCONNECTED` | BLE 连接断开 | 任意阶段 |
| `ccc--BLEBUSSEvent` | BLE 总线事件 | 任意阶段 |
| `ccc--ble` | BLE 操作（read/write/connect）| 任意阶段 |
| `ccc--bleSTDTRANSAC` | BLE 标准交易 | 任意阶段 |
| `ccc--app_set` | APP 配置下发/操作 | 任意阶段 |
| `ccc--busywait` | 等待忙 | 任意阶段 |
| `ccc--checktime` | 时间校验 | 任意阶段 |
| `ccc--setCCCUwbRangingParamSupported` | UWB 参数协商 | 任意阶段 |
| `ccc--ranging_noact` | UWB 无活动 | 任意阶段 |
| `recv_cb error:it's not in transaction or pairing` | 交易正常结束回调 | **无害，正常** |
| `recv_cb error: recv len=0` | **BLE 连接断开** | Phase 1 阻断 |

### 3.2 803C 状态码格式

`803Cxyzz` = 控制流状态码，格式为：
- **xy** = 配对阶段编号
- **zz** = 该阶段步骤编号

### 3.3 各阶段 803C 状态码序列

| 状态码 | 含义 | 对应 Phase | 验证 Ticket |
|--------|------|-----------|------------|
| `803C1001` | Phase 2 第一次 Transaction 完成（SELECT + Auth0）| Phase 2 | 6549/10825/14321/14482 |
| `803C1002` | Phase 2 第二次 Transaction 完成（Exchange 1） | Phase 2 | 6549/10825/14321 |
| `803C1111` | **Phase 2 结束，KeyID 已生成** | Phase 2→3 | 6549/10825/14321/14482 |
| `803C0181` | **Phase 3 车端完成，证书链校验通过** | Phase 3 | 10825/14321/14482 |
| `803C4088` | Phase 4 开始（KTS 注册请求） | Phase 4 | 10825/14482 |
| `803C4081` | Phase 4 步骤 2 | Phase 4 | 14482 |
| `803C4082` | Phase 4 步骤 3 | Phase 4 | 14482 |
| `803C0190` | **Phase 4 结束，KTS 注册成功** | Phase 4 | 10825/14482 |
| `803C01B0` | 钥匙写入 SE | Phase 5 | 14321 |
| `803C0100` | **配对完全成功，进入 Polling 状态** | Phase 5 | 10825/14321 |
| `803C0000` | 配对失败 | - | 14482/20449 |

### 3.4 完整配对成功序列

```
配对开始
  ├─ ccc--nfc pair
  └─ 803C1001 → 803C1002 → 803C1111  (Phase 2 结束)
      ├─ ccc--statemachine--in ranging  (手机进入车内)
      └─ 803C0181  (Phase 3 结束)
          └─ 803C4088 → 803C4081 → 803C4082 → 803C0190  (Phase 4 结束)
              └─ 803C01B0 → 803C0100  (Phase 5 结束，配对成功)
```

### 3.5 常见故障序列速查

| 日志序列特征 | 停在 | 根因 |
|-------------|------|------|
| **无** `ccc--nfc pair` + `bindkeyid2mac error` + `recv_cb error` | Phase 1 之前 | keyid 与 MAC 绑定丢失，BLE 断开 |
| 只有 `803C1001`，无 1002/1111 + `6A80`/`6A8C` 大量 | Phase 2 第1次交易 | Profile/证书环境不对齐 |
| `803C1001→1002→1111` 后无 `803C0181` + `6A82` 大量(100+次) | Phase 2→3 | 证书交换失败（AID 不匹配）|
| `803C1111→0181` 后无 `803C4088` + `sw=0x6400`(4次) | Phase 3→4 | SE Applet 处于只读/锁定状态 |
| `803C4088` 反复出现，无 `803C0190` | Phase 4 | KTS 注册失败（后台 500 / 99990004）|
| `803C4088→0190` 完整，但无 `803C0100` | Phase 4→5 | 钥匙写入 SE 失败 |
| 有 `ccc--statemachine--in ranging`（持续每2秒）无 NFC 交易 | Phase 2→3 | UWB 定位失败（手机位置不对）|
| 大量 `report2cloud XPNFC_ACTIVE fail code:500` | Phase 4 | 后台 XPNFC_ACTIVE 服务异常 |
| `curl_easy_perform() failed: Couldn't resolve host name` | 任意 | TBOX DNS 解析失败 |

### 3.6 ISO 7816 错误码（6Axx）

> 来源：NFC 交易中 SE 返回的 APDU 响应状态码

| 状态码 | 含义 | 阶段 | 根因 |
|--------|------|------|------|
| `6A82` | **文件/应用未找到（AID 不匹配）** | Phase 2~3 | 证书或 AID 配置问题，Profile 环境不对齐 |
| `6A80` | **数据域参数不正确** | Phase 2~3 | Profile/证书环境不对齐（CCC联调Knowhow Page 1）|
| `6A81` | 功能不支持 | Phase 2~3 | SE Applet 版本问题 |
| `6A83` | 认证失败（Record not found） | Phase 2~3 | 证书校验失败 |
| `6A84` | 引用数据已失效 | Phase 3 | 证书过期或被吊销 |
| `6A88` | 引用数据未找到（KeyID 黑名单）| Phase 2~3 | KeyID 在车端黑名单 |
| `6A89` | 用户认证失败 | Phase 3 | SPAKE2+ 认证失败 |
| `6A8A` | 超出使用次数限制 | Phase 3 | KTS 试用次数耗尽 |
| `6A8B` | GPO 失败（BLE 断开导致）| Phase 2~3 | BLE 连接丢失 |
| `6A8C` | P1P2 参数错误（BLE 数据接收异常）| Phase 1~2 | BLE 连接丢失或数据不完整 |
| `6A8E` | 允许的剩余次数为 0 | Phase 3 | 钥匙试用次数耗尽 |

### 3.7 各故障类型的完整日志特征

| 故障类型 | dk_service.log 特征 | 对应 Ticket |
|---------|---------------------|------------|
| **Phase 1 阻断** | 无 `ccc--nfc pair`，`bindkeyid2mac error`，`recv_cb error`，`803C1001` 后卡住 | 45795, 21031 |
| **Phase 2 证书问题** | `6A82`(100+次) 反复出现，`803C1001` 后无 1002/1111 | 6549, 10825 |
| **Phase 3 SE 只读** | `sw=0x6400`(4次)，`803C0181` 后无 4088，`ccc--CCCKeydata`(634次) | 14482 |
| **Phase 4 后台 500** | `report2cloud XPNFC_ACTIVE fail code:500` 反复，`803C4088` 无 0190 | 21031 |
| **Phase 4 TBOX DNS** | `curl_easy_perform: Couldn't resolve host name`，`ccc--BLE_DISCONNECTED` | 20449 |
| **分享 Ranging 卡住** | `ccc--statemachine--in ranging`（持续60+秒每2秒一次），`ccc--PubCb--still not change` | 26376 |

---

## 4. 配对故障模式

### 车端故障

| 错误特征 | 可能原因 | 修复方向 |
|----------|----------|----------|
| cccop=2 + sw=0x6400（配对时） | NFC ECP 只读模式，SE 写入失败 | 检查 ACOSe ECP 参数是否正确写入 NFC 固件，确认 cccop 默认值为 1 |
| cccop=2 + sw=0x6400（刷卡时） | ECP 配置配对后丢失，SE 读取失败 | 检查 ECP 参数是否持久化到 NVCM |
| sw=0x6400（无 cccop=2） | SE Applet 未初始化/只读模式，可发生在 Phase 2 或 Phase 3 的 Auth1 流程 | 检查 SE 生命周期管理，SE 是否被锁定或未正确初始化 |
| keyid in blacklist | 钥匙 KeyID 被车端列入黑名单 | 检查车端 KeyID 黑名单机制，确认 KeyID 清理逻辑 |
| NFC_SysSt=全0 | NFC 控制器未完成初始化，chip status error active | 检查 NFC 固件配置，确认电源/时钟/初始化时序 |
| nfcKeyFunState=-1 | SE 未配置 ECP，NFC 发现阶段阻断 | 检查 SE ECP 参数配置是否正确下发并持久化 |
| SELECT 失败 | Applet 未安装 / 损坏 | 重烧 NFC 固件 |
| APDU 响应错误 | 协议版本不匹配 | 核对车端/手机端协议版本 |
| SPAKE2+ 验证失败 | 密钥计算错误 | 车端证书检查 |
| 6A80 | 环境/证书不对齐 | 检查车端证书/iCloud账号/profile环境是否一致 |
| PairPhase2_1 / PairPhase2_2 failed | Phase 2 写入阶段失败 | 结合 cccop 值判断是车端 ECP 问题还是手机端问题 |

### 手机端 / 苹果后台故障

| 错误特征 | 可能原因 |
|----------|----------|
| CheckIDSRegistration 失败(-365) | Apple 身份服务注册失败 |
| PinningEvent 失败(TrustResult 4/5) | Apple Pay 证书验证失败 |
| TransparencyErrorEligibility | 透明性检查失败 |
| ktEnvironment: 0 | KTS 环境配置异常 |
| Profile签名验证失败 | 苹果更换测试 Profile 导致签名校验失败，startPairing 返回业务错误（605）|
| SDK缓存未刷新 | 大屏/IVI 删除钥匙后 OneApp SDK 未收到通知，仍保留旧 KeyID，发起配对时使用已删除钥匙 |

### 后台故障

| 错误特征 | 可能原因 |
|----------|----------|
| KTS 请求无响应 | ABR 配置错误 / 网络不通 |
| 后端未收到 KTS 请求 | 需区分：(1) ABR 路由配置错误，KTS 请求被阻断（独立根因）；(2) Phase 2/3 已失败，流程未到达 KTS 阶段（结果，非原因）| 
| KTS 超时 | ABR 配置错误 |
| 90000011 (OAuth鉴权失败) | 用户与车辆订阅关系缺失，touchgo 接口返回 401 |

### 日志关键词

**iOS 日志关键词**：
- `KTS` / `KTSEligibility` / `KTSMManager`
- `CheckIDSRegistration`
- `PinningEvent` / `TrustResult`
- `passd` / `Passbook`
- `CarKey` / `digitalcarkey`
- `Owner Pairing` / `OP`
- `SEID` — 设备安全元件 ID
- `TransparencyError` / `Octagon`
- `attestation`
- `opcontrol_cmd: 000B0004803C` — OP Control Flow 状态码

**Android 日志关键词**：
- `ccc--NFC--` — CCC NFC 协议层
- `ccc--bleERROR` — BLE 协议层异常
- `PairPhase2_1` / `PairPhase2_2` — Phase 2 失败
- `frist_ownerparing_stdtransaction` — BLE fallback 失败
- `bindkeyid2mac error` — KeyID-MAC 绑定丢失（Phase 1 阻断触发点）
- `recv_cb error` — BLE 接收回调异常（Phase 1 阻断常见表现）

**车企后台日志关键词**：
- `ABR` — Apple Backend Routing 配置
- `KTS request` / `KTS response`
- `certificate` / `provisioning`
- `auth` / `token` / `session`
- HTTP 状态码：`400` / `401` / `403` / `404` / `500` / `502` / `503`

---

## 5. 钥匙分享故障模式

### Pretrack 检查要点（关键！）

遇到 Key Sharing 失败时，**必须首先检查**：
1. **Pretrack 服务状态**：车企后台 Pretrack 服务是否可访问
2. **Pretrack 响应数据**：UIBundle 数据格式是否正确
3. **HTTP 状态码**：返回 404/500 等错误表明配置问题
4. **时间戳**：与失败时间对齐的 Pretrack 请求

**常见 Pretrack 错误**：
- HTTP 404 → Pretrack URL 配置错误或服务未部署，nginx 路径遗漏（特定车型 corner case）
- HTTP 500 → 后端服务内部错误
- 超时 → 网络不通或服务无响应
- errorCode=99990004 (DEFAULT_ERROR) → Pretrack 验证失败，data:false 返回
- **keyId 未下发** → Pretrack 服务通过验证，但未将分享钥匙的 keyId 下发到车端，车端无分享钥匙绑定关系，导致 NFC 解闭锁失败

### 分享故障模式

| 错误特征 | 可能原因 | 归属端 |
|----------|----------|--------|
| Pretrack 404 Not Found | Pretrack URL 配置错误 / 服务未部署 / nginx 路径遗漏 | 后台 |
| Pretrack 验证失败 | Pretrack 服务返回 data:false + errorCode=99990004（DEFAULT_ERROR）| 后台 |
| 车辆关系解绑 | 用户与车辆绑定关系已解除，errorCode=90000008 | 后台 |
| Pretrack keyId 未下发 | 车企后台未将分享钥匙的 keyId 下发到车端 | 后台 |
| 车端 keyId slot 脏数据 | VIN 对应 keyId slot 有旧数据未清理，新分享钥匙拿到旧数据 | 车端 |
| LocalPassNotFound | 用户添加数字钥匙但未完成 CarKey 注册流程，Pass 未写入 Apple Wallet | 手机端 |
| 短信通知延迟/被拦截 | DK 服务端发出领取短信，但被运营商拦截或消息中心处理超时 | 后台 |
| 钥匙无法添加到 Wallet | KTS 注册未完成 | 手机端 / 后台 |
| 分享邀请发送失败 | 网络问题或 Apple 服务异常 | 手机端 / 苹果后台 |
| AirDrop 接收失败（同账号）| 两台 iPhone 使用同一 iCloud 账号，AirDrop 接收端未正确响应 | 手机端 |

### 日志关键词

- `Pretrack` / `trackKey`
- `Friend` / `Sharing` / `share`
- `ktIDSPV2` / `KTPrimaryAccount`
- `CloudKit` / `CKError`
- `eventType` / `SHARED_KEY_ADDED`

---

## 5. 调试工具

### LDCU 诊断命令

> Phase2→Phase3 定位手机在车外时使用，通常是 LDCU 配置字问题。

通过 CANoe 连接 DCAN，加载 LDCU 的 cdd/dll 后执行：

```
10 03
27 01
27 02
22 CF 05
2E CF 05 01 01 00 01 01 01 01 01 01 01 01 00 00 00 00 00 01 00 00 01 01 00 00 00 00 01 00 00 02 00 00 02
```

### 配对码查看

在 APP 日志中（Notepad 打开，**Notepad++ 会乱码**）：
- 搜索关键字：`startPairing` 或 `password`
- 后台响应的请求体中包含配对码
- JSON 格式特征：`biz_type=63, scene=63001, event=START_PAIRING, salt, w0` 字段

### BLE Static Random Address bug

车端重启后 `payload3` 填了 **public MAC address** 而非 Resolvable Private Address（RPA）：
- 全流程走了，但 Friend Device 开卡失败
- 正确状态：payload3 应填写 RPA（由 IRK 生成）
- **属于车端证书/配置问题**

### BLE MAC 地址配置导致 RKE/PEPS 功能缺失

车端 BLE 软件 MAC 地址上报配置有误（与 MiFi 认证流程相关）：
- 现象：CCC 分享钥匙仅有 NFC 功能，但缺少 RKE 和 PEPS 功能
- 根因：BLE 上报配置中 MiFi 认证相关参数错误，导致车端未使能远程解闭锁功能
- **属于车端 BLE 软件配置问题**

---

## 6. 已知故障模式汇总

| 故障类型 | 错误特征 | 归属端 | 参考 Ticket |
|----------|----------|--------|------------|
| 车辆关系解绑 | errorCode=90000008 人车关系已解除 | 后台 | VCTCEM-22690, VCTCEM-24495 |
| Pretrack keyId 未下发 | 分享钥匙 keyId 未下发到车端 | 后台 | VCTCEM-7531 |
| Pretrack DEFAULT_ERROR | errorCode=99990004 Pretrack 验证失败 data:false | 后台 | VCTCEM-29194 |
| 车端 keyId slot 脏数据 | VIN 对应 keyId slot 有旧数据未清理 | 车端 | VCTCEM-9314 |
| LocalPassNotFound | 用户未完成 CarKey 注册，Pass 未写入 Wallet | 手机端 | VCTCEM-29194 |
| NFC ECP 配对中断 | cccop=2 + sw=0x6400（配对阶段失败）| 车端 | VCTCEM-6549 |
| NFC ECP 刷卡无弹窗 | cccop=2 + sw=0x6400（配对后配置丢失）| 车端 | VCTCEM-16673 |
| BLE MAC 配置错误 | MAC 上报配置有误导致 RKE/PEPS 功能缺失 | 车端 | VCTCEM-14302 |
| SE Applet 未初始化 | sw=0x6400（无 cccop=2），SE 只读/锁定 | 车端 | VCTCEM-14321 |
| KeyID 黑名单 | keyid in blacklist，Auth1 验证失败 | 车端 | VCTCEM-14482 |
| NFC 控制器未初始化 | NFC_SysSt=全0，chip status error active | 车端 | VCTCEM-10825 |
| SE 未配置 ECP | nfcKeyFunState=-1，NFC 发现阶段阻断 | 车端 | VCTCEM-21967 |
| TBOX DNS 解析失败 | curl_easy_perform: Couldn't resolve host name | 车端 | VCTCEM-20449 |
| Profile 签名验证失败 | startPairing 返回 605，苹果 Profile 签名校验失败 | 苹果后台 | VCTCEM-28325 |
| OAuth 鉴权失败 | 90000011，用户与车辆订阅关系缺失 | 后台 | VCTCEM-21967, VCTCEM-22135 |
| SDK 缓存未刷新 | 大屏删除钥匙后 OneApp SDK 未通知，使用旧 KeyID | 手机端 | VCTCEM-14519 |
| 配对创建失败 | 创建钥匙过程异常 | 多端 | VCTCEM-25315 |
| receipt 未对应 | KTS receipt 不匹配 | 后台 | VCTCEM-36257 |
| KTS 超时 | ABR 配置错误 | 后台 | — |
| 证书验证失败 | -365 / TrustResult | 手机/苹果 | — |
| UWB PE 不解锁 | LDCU 未发解锁命令 | 车端 | VCTCEM-23462 |

### 参考 Ticket

**配对/创建失败**：6549, 10130, 10825, 12144, 14321, 14482, 14519, 17212, 17996, 19504, 20449, 20667, 20677, 21031, 21967, 22135, 22248, 27525, 28325, 30734, 35791, 25315, 36257
**钥匙分享失败**：22690, 29194, 26376, 9314, 7531, 9316, 14302, 22233, 11021

---

*最后更新：2026-05-25*（v4.9 新增 803C 状态码完整格式说明 + 24 种 ccc-- 前缀速查 + 6Axx ISO 错误码体系 + 6 个故障类型的完整日志特征 + 8 个 Ticket 交叉验证；修复 Pairstatus 表格 + 章节重复问题）
