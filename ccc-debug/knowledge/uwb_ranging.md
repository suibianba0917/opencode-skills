# UWB 测距 / PE 被动进入不解锁

> **官方规范**：Apple Spec R4 — Chapter 3.6 Location Based Features (p39) / 3.9 UWB Requirements (p54) / 3.5.5 Device Ranging Intent (p37)
> 📎 `references/Apple规范/Car Keys Specification R4.pdf`

---

## 官方定义（Apple Spec R4）

### 定位原理

详见 Apple Spec R4 **3.6 Location Based Features** (p39) + **Figure 3-7~3-10**：

- 多边测距法（Classic Multilateration）：使用 2~3 个锚点测距交叉定位
- iPhone 指向方向影响测距精度（Portrait/Landscape 模式，图 Figure 3-5/3-6）
- L1~L4 轨迹定义用于测试验收

### UWB 系统级要求

详见 Apple Spec R4 **3.9 UWB Sensor-Level RF Requirements** (p54)：

- RMS-Average Packet EIRP 限制
- Rx Effective Isotropic Sensitivity (EIS)
- Time-of-Flight (ToF) 3D 精度要求
- 频段支持（Chapter 3.9.7.4）
- XO Static PPM 要求

### Device Intent（设备意图）

详见 Apple Spec R4 **3.5.5 Device Ranging Intent SubEvent** (p37)：

设备在靠近车辆时发出 Device Intent，告知车辆车主正在靠近，请求车辆发起定位：

| Intent 级别 | 日志标记 | 含义 |
|------------|----------|------|
| Low | `031100020300` | 远距离接近 |
| Medium | `031100020301` | 中距离接近 |
| High | `031100020302` | 近距离接近 |

发出 Device Intent 后，车端随即开启 UWB 定位。

### 用户接近任务流程

详见 Apple Spec R4 **Figure 3-4 User Approach Tasks** (p42)：
- 设备检测 → Device Intent → Ranging 开始 → 位置判断 → 解锁/闭锁

---

## 内部补充

### UWB 定位值（uwbkey1）

dk_service.log 中 `uwbkey1 = X` 表示钥匙所在区域：

| 值 | 区域 | 说明 |
|----|------|------|
| 1-8 | 车内（具体锚点位置） | 钥匙在车内 |
| 9 | 10m外 / 定位失败 | 超出范围或 UWB 测距异常 |
| 10 | 4m内 | **解锁圈** — 走近此距离才会触发解锁 |
| 11 | 4~8m | 闭锁圈 — 超出此范围触发闭锁 |
| 12 | 8~10m | 迎宾圈 — 走近时可能触发迎宾灯效 |

### 锚点编号顺序

| 锚点 | 位置 |
|------|------|
| 1 | 主锚点 |
| 2 | 左前锚点 |
| 3 | 右前锚点 |
| 6 | 左后锚点 |
| 7 | 右后锚点 |

---

## CAN 日志文件格式

- **ASC文件**: Vector CANalyzer/Canoe 格式，如 `CAN_ETH.ASC`
- **DBC文件**: CAN 数据库定义
- **BLF文件**: Binary Log Format（二进制）

### ASC 日志格式解析

```
0.363067 CANFD  15 Rx        249             1 0 f 64 7d 00 00 00 fa 7d 00 00 00 00 00 00 00 00 1d
   ^时间(s)   ^协议 ^Channel ^CANID    ^DLC ^数据字节...
```

### DBC 数据库文件

**DBC目录**: `config.ini` 中 `[DBC] paths` 配置。

使用 DBC 文件可解析 ASC 日志中的 CAN ID 对应的信号含义。

---

## UWB 相关 CAN ID（DWM 芯片）

| CAN ID (Hex) | 来源 | 说明 |
|--------------|------|------|
| 0x12DD5401 | LDCU | UWB 锚点1 测距数据（8个锚点，ID 01-08）|
| 0x12DD5402 | LDCU | UWB 锚点2 测距数据 |
| 0x12DD5403 | LDCU | UWB 锚点3 测距数据 |
| 0x12DD5404 | LDCU | UWB 锚点4 测距数据 |
| 0x12DD5405 | LDCU | UWB 锚点5 测距数据 |
| 0x12DD5406 | LDCU | UWB 锚点6 测距数据 |
| 0x12DD5407 | LDCU | UWB 锚点7 测距数据 |
| 0x12DD5408 | LDCU | UWB 锚点8 测距数据 |

### 核心信号（需结合 DBC 解析）

| CAN ID | 信号 | 说明 |
|--------|------|------|
| 0x226 | LDCU | `UWBKey1-4IncarPosition` 钥匙在车内位置 |
| 0x224 | LDCU | `UWBKey1-4RawLocationX/Y` 钥匙原始坐标 |
| 0x226 | LDCU | `LDCU_DoorUnlockSource` 解锁来源（含 UWB PE unlock=19）|
| 0x226 | LDCU | `LDCU_DoorLockSource` 闭锁来源（含 UWB PE lock=17）|
| 0x316 | CDCU | `UWBPollingDoorLockreq` Polling 门锁请求 |
| 0x629 | CDCU | `UWBKey1-4RawPosition` 钥匙原始位置区域 |
| 0x30E | NGX | `UWBKeyValidSt` UWB 钥匙有效性 |
| 0x30E | NGX | `UWBKeySearchResult` 钥匙搜索结果 |
| 0x228 | RDCU | `BLE_UWBDMSt` UWB 活体检测状态 |
| 0x228 | RDCU | `UWBDMDetected_Result` 活体检测结果 |

### 网络管理报文

| CAN ID | 节点 | 信号 |
|--------|------|------|
| 0x420 | RDCU | `RDCU_NMReq_BLE_UWB` |
| 0x421 | CDCU | `CDCU_NMReq_BLE_UWB` |
| 0x4E0 | LDCU | `LDCU_NMReq_BLE_UWB` |

---

## PE 故障分析方法

### 步骤1: 定位测试时间

ASC 日志开头包含日期时间：

```
date Fri Jan 30 02:03:44 pm 2026
测试14:09发生, 相对时间 = (14:09 - 14:03:44)*60 = 316秒
```

### 步骤2: 提取 UWB 锚点消息

```powershell
grep "12DD5401" CAN_ETH.ASC
grep "12DD5402" CAN_ETH.ASC
# ...
```

### 步骤3: 分析消息间隔

```
正常间隔: ~100ms (10Hz)
异常: 间隔突然增大 >500ms 或停止
```

### 步骤4: 验证结论模式

| 预期现象 | 证据查找 |
|----------|----------|
| UWB 锚点测距打开 | 多个 CAN ID (12DD5401-08) 有持续消息 |
| 测距突然停止 | 消息间隔出现 >500ms 大间隙 |
| CAN 上无手机数据 | 检查手机相关 CAN 消息是否减少/消失 |

---

## PE 故障常见根因

| 现象 | 可能原因 | 归属 |
|------|----------|------|
| UWB 消息正常，解锁失败 | 车端 NFC/BLE 响应异常 | 车端 |
| UWB 消息停止 | 手机端未发起测距 | 手机端 |
| UWB 间隔增大 | 手机与车距离过远 / 信号干扰 | 手机端 / 环境 |
| 无手机相关 CAN | 手机未与车辆建立通信 | 手机端 |
| LDCU 收到测距但未发解锁命令 | 车端软件逻辑问题 | 车端 |

---

## 问题类型 → CAN 组合

| 问题类型 | 重点查看 |
|----------|----------|
| UWB Polling 不解锁 | **0x316**(`UWBPolling*`) + **0x226**(`UWB polling unlock`) |
| 钥匙位置判断错误 | **0x226**(`UWBKey*RawLocation*`) + **0x30E**(`UWBKeySearchResult`) |
| UWB PE 不解锁 | **0x226**(`LDCU_DoorUnlockSource`=19) + **0x629**(`UWBKey*RawPosition`) |
| 活体检测异常 | **0x228**(`BLE_UWBDMSt`, `UWBDMDetected_Result`) |
| 整体通信状态 | **0x420/0x421/0x4E0** (`NMReq_BLE_UWB`) |

---

## 日志时间对齐

- 日志时间通常是本地时间
- 北京时间 (CST) = UTC + 8
- 例: 14:09 北京 = 06:09 UTC

---

## CCC 钥匙乒乓问题（正常行为，非 bug）

### 现象描述

闭锁后 2 分钟自动落锁 → UWB 重新测距 → 又解锁

### 原因（设计逻辑，非 bug）

```
1. 用户 RKE 解闭锁，车辆解锁
2. 用户未拉开车门，2分钟后自动闭锁（防盗设计）
3. UWB 重新唤醒新一轮测距
4. UWB 发现手机仍在解锁圈内（10=4m内），触发 Polling 解锁
5. 用户感知：刚锁好又自动解锁了
```

### 测试场景

放在 3m 保持静止状态，验证乒乓现象：
- 第一次：RKE 解锁 → 2min 后自动落锁
- 第二次：UWB 测距唤醒 → 检测到解锁圈内 → 再次解锁

### ⚠️ 误判风险

**不要将乒乓问题判断为故障！** 这是 CCC UWB 启停策略的正常行为。

### 排查方向（如用户抱怨）

1. 确认是否在 2min 内拉开车门（2min 后才自动落锁）
2. 确认手机是否在解锁圈内（4m 内）
3. 如需避免乒乓，可增加手机与车距离 >8m 再返回

---

## CCC UWB 启停策略

UWB 测距的启动和停止由以下条件控制：

| 条件 | 动作 | 说明 |
|------|------|------|
| 当前处于运动状态 | **stop** | 车辆移动时停止测距 |
| 锁车 + UWB未启动 + RSSI ≤ 迎宾圈 | **start ranging** | 静止锁车后进入迎宾圈时启动 |
| 发动机启动 | **start ranging** | 车辆启动时激活 UWB |
| 没有处于测距状态 | **start ranging** | 兜底策略 |

### ⚠️ 关键注意

- **运动状态优先**：车辆移动时 UWB **不工作**，走近不解锁是正常的
- 静止锁车后，RSSI 检测到钥匙进入迎宾圈才启动 UWB 测距

### 搜索词

- `start ranging` / `stop ranging`
- `uwbkey1`
- `UWB polling`
- `031100020300` / `031100020301` / `031100020302` — Device Intent 级别

---

## 解闭锁源分析方法

通过分析解闭锁来源，可快速定位异常解闭锁（乒乓等）的触发源头。

| 搜索词 | 含义 |
|--------|------|
| `lock src` | 闭锁来源 |
| `unlock src` | 解锁来源 |

### 典型解闭锁来源值

| 值 | 来源 | 说明 |
|----|------|------|
| RKE | 遥控钥匙 | 用户按遥控器 |
| BLE Polling | 蓝牙轮询 | 手机在解锁圈内触发 |
| UWB PE | UWB 被动进入 | UWB 测距定位后触发 |
| CCC | CCC 协议 | 刷卡触发 |

### 应用场景

- **异常乒乓问题**：搜索 `lock src` 和 `unlock src`，确认闭锁来源是 RKE 还是 Polling，解锁来源是 UWB PE 还是其他
- **解闭锁不触发**：确认来源值是否为空，排除来源端硬件/配置问题

---

## 已知正常行为（避免误判）

| 现象 | 是否正常 | 说明 |
|------|----------|------|
| 车辆移动时走近不解锁 | ✅ 正常 | 运动状态下 UWB 不工作 |
| 锁车后 2min 内走近解锁 | ✅ 正常 | 2min 内不会自动落锁 |
| 闭锁后 UWB 重新解锁（乒乓） | ✅ 正常 | 设计行为，2min 落锁 + UWB 检测解锁圈 |
| UWB 锚点 1-8 均无数据 | ⚠️ 需确认 | 手机不支持 UWB 或 UWB 未开启 |

---

## 相关 Ticket

- VCTCEM-23462 — 苹果数字钥匙 PE 解闭锁失败（LDCU 软件未发解锁命令）
- VCTCEM-11016 — 两部 iOS 手机同时进入 UWB 锚点模式
- VCTCEM-11018 — 解闭锁循环异常
- VCTCEM-11019 — 车辆休眠后 PE 不解锁
- VCTCEM-13342 — UWB 钱包钥匙走到闭锁圈不闭锁
- VCTCEM-13343 — CCC 钱包钥匙无法触发 UWB 定位
- VCTCEM-21405 — UWB 技术禁止使用

---

*最后更新：2026-05-12*
