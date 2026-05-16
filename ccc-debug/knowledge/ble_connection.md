# BLE 连接问题 / Polling 策略 / 车控链路

本文涵盖 BLE 数字钥匙配对阶段的蓝牙连接问题（Section A）和 BLE 车控功能（Section B），两者是不同的链路，请按场景查阅。

> **官方规范**：Apple Spec R4 — Ch3.2 BLE Owner Pairing / Ch3.5 DKEvent Notifications
> 📎 `references/Apple规范/Car Keys Specification R4.pdf`

---

## A. 数字钥匙配对 BLE 连接

此部分适用于 OP 配对阶段、Key Sharing、First Friend Approach 场景的蓝牙连接问题。

### 典型症状

- 蓝牙配对失败
- 蓝牙反复断连
- 删除钥匙后无法重连

---

### 1. iOS UUID 缓存失效（重连失败）

**根因**：iOS 为保护隐私，不获取外设 BLE 真实 MAC 地址，而是通过设备广播中的 Service UUID 等标识信息判断扫描到目标设备。当 iOS 扫描到某个 BLE 外设时，系统为该设备分配唯一 UUID，与当前 iOS 设备的连接记录绑定并缓存。

**缓存失效原因**（以下任一情况导致 UUID 缓存失效）：
- 用户在 iOS 系统设置中还原网络设置
- 用户通过设置→蓝牙→开关，关闭或重新开启蓝牙总开关（概率性）
- iOS 系统升级
- APP 被系统强制清除缓存（极少）
- 外设恢复出厂设置（几乎不会）
- APP 被用户删除并重新安装

**日志表现**：

```
扫描广播 → 发现缓存 → 开始连接 → 连接失败
清除缓存
重新扫描广播（通过 Local Name + UUID 筛选）
蓝牙连接成功
开始鉴权
Auth0成功
Auth1成功
```

**修复方案**：
- SDK 需添加缓存失效兜底逻辑：重连失败时自动触发重新扫描，更新并保存新的 UUID
- OneApp 在蓝牙检查界面增加清除缓存入口

---

### 2. Peer removed pairing information（CBError Code=14）

**根因**：删除 CCC 钱包钥匙时，TBOX 和手机端都删除了钥匙，但 **iOS 系统缓存了旧的配对信息**，导致 iOS 携带旧配对信息请求配对失败。

**日志表现**：

```
❌[VehicleSDK] [FT-main蓝牙连接] [M-handleConnect()] 蓝牙连接流程失败
error: Error Domain=CBErrorDomain Code=14 "Peer removed pairing information"
UserInfo={NSLocalizedDescription=Peer removed pairing information}
```

**修复方案**：
1. SDK 抛出故障码
2. OneApp 引导用户手动忽略蓝牙设备
3. 用户在设置→蓝牙→我的设备中找到对应车辆的广播名称，选择「忽略设备」，再尝试重新连接

---

### 3. 安全报文 counter 不匹配（Auth1 失败）

**根因**：One Backend 生成安全报文下发给手机，手机缓存一定数量（>50条）。安全报文中安全信息字段有防重放 counter。每次蓝牙交互使用一条，车端校验 counter 必须 > TBOX 端。

多设备切换场景下，旧设备的安全报文 counter < TBOX 端当前值 → **Auth1 失败**。

**日志表现**：
- TBOX DKS 日志：`Auth1失败`
- APP 日志：`Auth鉴权超时`

**修复方案**：
- APP 在用户退出登录的同时删除数据库 `.db`、`.db-wal`、`.db-shm` 文件
- 登录创表时检查 `.db-wal`、`.db-shm` 文件是否存在

---

### 4. carKeySession 占用 BLE 通道

**根因**：一键注销后，苹果未清理完 CarKey 信息，**carKeySession 仍占用了私有 BLE 通道**，导致新连接请求失败。

**日志表现**：

```
[CarKeySessionAccesser] : startCarKeySession(_:):217 Info: start session error occurred:
未能完成操作。（CarKey.CarKeyErrorCode错误0。）
钱包中有停用的卡片
```

**恢复措施**：
- 手动在钱包中移除钥匙
- 或等待 carKeySession 超时释放

**修复方案**：
- SDK 修复多 carKeySession 内存泄露导致的状态混乱问题

---

### 5. 蓝牙断连原因码（disconnected, reason=X）

车端 dk_service.log 中出现 `disconnected,reason=X`，X 值含义：

| reason | 含义 | 归属 | 排查方向 |
|--------|------|------|----------|
| 19 | 手机主动断开连接 | 手机端 | 用户行为，无需排查 |
| 8 | 远离断开（RSSI 过低） | 环境 | 正常现象，信号衰减 |
| 22 | 信号差主动断连 | 环境/手机 | 检查干扰、重启手机 |
| **62** | **连接未能建立/同步超时** | **手机端** | **通常为手机问题，尝试重启手机** |

**reason=62 详解**：
```
Disconnected, reason=62
含义：LL启动了连接或启动了对定期广播的同步，但连接未能建立，
      或链接层未能与第一次尝试的6个周期广播事件内的定期广播同步。
根因：一般手机问题
修复：让用户重启手机
```

**⚠️ 重要**：reason=62 不应被判断为车端故障，**不要生成车端修复建议**。

---

### 6. BLE 日志关键词（配对场景）

- `disconnected,reason=` — 断连原因码
- `connected` — 连接成功
- `recv_cb error` — 蓝牙接收回调异常（与 reason=62 可能同时出现）
- `Auth1失败` / `Auth鉴权超时` — 安全报文 counter 不匹配
- `CarKeyErrorCode` / `CarKeySessionAccesser` — carKeySession 问题

---

### 7. TBOX DNS 解析失败（车端网络问题）

**根因**：TBOX 在测试时间段内无法解析后台域名，导致无法与车企后台建立连接。

**日志表现**：
```
curl_easy_perform() failed: Couldn't resolve host name
```

**常见场景**：
- TBOX 网络环境配置错误（如配置到了生产环境但测试环境无网络）
- DNS 服务器不可达
- 域名解析超时

**修复方向**：
1. 检查 TBOX 环境配置（`TBOX_ACCOUT_REQ_URL_PATH`）
2. 确认测试环境网络可达性
3. 检查 DNS 服务器配置

**参考 Ticket**：VCTCEM-20449

---
- `CBErrorDomain Code=14` — Peer removed pairing information

---

## B. BLE 车控功能 / Polling

此部分适用于已配对的数字钥匙进行车控操作（解闭锁/尾门/车窗等）以及 Polling 解闭锁功能。

### 典型症状

- 走近不解锁 / 离开不闭锁
- 蓝牙车控指令失败
- 异常乒乓（反复解闭锁）

---

### 1. ⚠️ Polling 功能默认关闭（常见误判根因！）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Polling 解锁 | **关闭** | 用户需手动在 APP 中开启 |
| Polling 闭锁 | **关闭** | 用户需手动在 APP 中开启 |
| Polling 解锁距离 | **3m** | 可调范围 0~6m，调节颗粒度为整数 |
| Polling 闭锁距离 | **6m** | — |
| Polling 自标定参数 | **不启用** | — |

**⚠️ 误判场景**：用户说"走近不解锁"，首先确认 Polling 解锁功能是否已开启！默认是关闭的。

---

### 2. Polling 策略

#### 一次蓝牙连接只触发一次 Polling 解锁

```
手机蓝牙连接车辆
    ↓
触发一次 Polling 解锁（蓝牙连接即可触发，不依赖 UWB）
    ↓
解闭锁后必须断开蓝牙，等待 7s，重新连接才能再次触发 Polling
```

#### 调试要点

- Polling 触发**不依赖 UWB**，蓝牙连接即可触发第一次 Polling
- 第一次 Polling 后即使手机在解锁圈内**也不会再次触发**，必须等断连 7s
- 误判场景：测试中发现走近不解锁 → 检查是否之前已经触发过 Polling 且未断连等待

#### 解闭锁源分析

通过 dk_service.log 搜索 `lock src` / `unlock src`，确认解闭锁来源：

| 来源值 | 含义 |
|--------|------|
| RKE | 遥控钥匙 |
| BLE Polling | 蓝牙轮询触发 |
| UWB PE | UWB 被动进入 |
| CCC | NFC 刷卡 |

**应用场景**：异常乒乓 → 搜索 `lock src` / `unlock src`，确认闭锁来源是 RKE 还是 Polling，解锁来源是 UWB PE 还是其他。

---

### 3. CAN 信号路由（车控指令链路追踪）

车控指令从 APP 到执行结果返回的完整链路：

```
手机APP → BLE（蓝牙协议）
    ↓ CANID:1C/1D/1E/1F（BLE_BLEControl_Sig1~Sig4）
TMCU
    ↓ 串口协议
T4G_SDK（判断前置条件/合法性）
    ↓
执行动作（如 TBOX_LDCU_DoorLockReq=BLE Door Lock）
    ↓ CAN
各ECU（门锁/LDCU/RDCU等）执行动作
    ↓ CAN（返回状态，如 LDCU_LockLogicSt）
TMCU → CANID:3C/3D/3E/3F（TBOX_BLEControl_Sig1~Sig4）
    ↓
BLE（蓝牙协议）
    ↓
APP（更新按键状态）
```

#### Debug 应用

当用户报"蓝牙车控失败"时，按链路逐级排查：
1. 检查 BLE 是否收到 APP 指令（dk_service.log 有无 BLE 接收记录）
2. 检查 CANID:1C~1F 信号是否上 BLCAN
3. 检查 TMCU→SDK 串口是否有响应
4. 检查 SDK 返回的超时原因（如"车门未关"/"非P档"等）
5. 检查 CANID:3C~3F 信号是否返回到 BLE

#### 关键 CAN 信号

| 方向 | CAN ID | 信号 | 说明 |
|------|--------|------|------|
| APP→车 | 1C/1D/1E/1F | BLE_BLEControl_Sig1~4 | APP 车控指令下发 |
| 车→APP | 3C/3D/3E/3F | TBOX_BLEControl_Sig1~4 | SDK 执行结果反馈 |
| TBOX→门锁 | — | TBOX_LDCU_DoorLockReq | 解闭锁请求（值：BLE Door UnLock/Lock/Tmpy lock） |
| 门锁→TBOX | — | LDCU_LockLogicSt | 门锁状态（0x0=unlock/0x1=lock） |
| 门锁→TBOX | — | LDCU_DoorLockSource | 解闭锁指令来源 |
| 门锁→TBOX | — | LDCU_TemporaryLockFB | 临停锁状态（0x1=Active） |

---

### 4. BLE 日志关键词（车控场景）

- `Polling` / `polling`
- `UWBPollingDoorLockreq` — CAN ID 0x316
- `lock src` / `unlock src` — 解闭锁来源
- `LDCU_DoorUnlockSource` / `LDCU_DoorLockSource`

---

## 已知正常行为（避免误判）

| 现象 | 是否正常 | 说明 |
|------|----------|------|
| reason=19 | ✅ 正常 | 手机主动断开，测试行为 |
| reason=8 | ✅ 正常 | 远离车辆，信号衰减 |
| reason=62 | ⚠️ 手机端问题 | 让用户重启手机，不要误判车端 |
| 第一次 Polling 后不解锁 | ✅ 需等待7s | 必须断连重连才触发第二次 |
| Polling 默认关闭 | ✅ 设计如此 | 用户需手动开启 |

---

*最后更新：2026-05-12*