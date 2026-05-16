# NFC 刷卡 / ECP 配置问题

> **官方规范**：Apple Spec R4 — Chapter 2 NFC（含 2.2 ECP / 2.1 Polling / 2.6 Transaction）
> 📎 `references/Apple规范/Car Keys Specification R4.pdf`

---

## 官方定义（Apple Spec R4）

### NFC Polling Sequence

详见 Apple Spec R4 **2.1 Reader Polling for Transactions** (p16) + **Figure 2-1 Polling Sequence**：

```
REQA → VASUPA → Reset
```

- **REQA→REQA 间隔**：必须 <30ms
- **REQA→VASUP 间隔**：必须 5~10ms
- 超时表示轮询失败，可能原因：设备未靠近/NFC 硬件异常

### Enhanced Contactless Polling (ECP)

详见 Apple Spec R4 **2.2 Enhanced Contactless Polling (ECP)** (p18)。

ECP 由 Apple 定制，读卡器发出用于轮询，允许设备在通信开始前判断是否与读卡器交互。

### ECP TCI 值（设备位置决定）

详见 Apple Spec R4 **6.5.5.1 TCI Value** (p87)：

| 位置 | TCI 值 | 备注 |
|------|--------|------|
| B 柱（MM AR） | `010676` | - |
| 门把手（其余车型） | `010671` | - |
| WLC（无线充电） | `010673` | - |

### NFC 读卡器工作范围

详见 Apple Spec R4 **2.3 Reader Operating Volume** + **2.4 Door Handle Reader Management**：

- 门把手：iPhone 可达区域详见 Figure 2-2
- Apple Watch 另有独立工作范围（Figure 2-3）

### 交易结构

详见 Apple Spec R4 **2.6 NFC Transaction Structure** (p26) + **3.1 Transactions** (p34)：

```
SELECT + SELECT Response
  ↓
Auth0（首次启动认证）
  ↓
Exchange（数据交换）
  ↓
Control Flow（车端表明最终交易是否成功）
```

Auth0 → Exchange 对应 OP Phase 2，Control Flow 对应 OP Phase 3。详见 `ccc_pairing.md`「配对阶段状态机」章节。

### 标准交易解锁条件

详见 Apple Spec R4 **4.4 Transaction Management**：

- 读卡器读到卡 → 交易成功 → **车端响应 `9000`（ISO 7816 成功状态码）才解锁**
- 未收到 `9000` 则不解锁

### AID 轮询

详见 Apple Spec R4 **2.7 AID Selection** (p30)：

- 读卡器通过 SELECT 轮询，直到轮询到正确的 AID 才开始交易
- 不合适的 AID 返回 `6A82`（"File not found"）— **这是正常行为，非故障**

---

## 内部补充

### ECP TCI 值实际配置

> 内部调试发现，以下 TCI 值为当前量产车型实际配置：

| 位置 | TCI 值 | 内部备注 |
|------|--------|----------|
| B 柱 MM AR | `010676` | - |
| 门把手 | `010671` | - |
| WLC | `010673` | - |

**错误格式**：`TCI` 后带 `Vehicle ID`（如 `0151108D0000A0A7`），导致 NFC 刷卡时无法直接选卡。

**正确格式**：TCI 后不带 Vehicle ID。

### Polling 时间约束（实测）

- REQA→REQA 间隔实测 **必须 <30ms**，超过则轮询失败
- REQA→VASUP 间隔实测 **必须 5~10ms**

---

## 已知故障模式

### 1. NFC ECP 配置问题（cccop 模式）⭐ 重点

**根因**：NFC 固件 `cccop=2`（读卡模式），无法写入 ECP 安全区域 → SE Applet 返回 `sw=0x6400` → CCC Phase 2-3 认证失败

**故障链条**：

```
cccop=2（读卡模式）
  ↓ NFC 无法写入 ECP 安全区域
SE Applet 返回 sw=0x6400（执行失败，无详情）
  ↓ CCC 协议层认证失败
手机端收到 category=1 / ccc--bleERROR
  ↓ 最终表现
NFC刷卡无弹窗 / 配对失败
```

### 2. 其他 NFC 配对失败模式

| 错误特征 | 可能原因 | 归属端 |
|----------|----------|--------|
| APDU 响应错误 | 协议版本不匹配 / 命令格式错误 | 车端 / 手机端 |
| SELECT 失败 | Applet 未安装 / 损坏 | 车端 |
| SPAKE2+ 验证失败 | 密钥计算错误 | 车端 / 手机端 |
| sw=0x6400 + cccop=2 | **NFC ECP 未配置（cccop 读卡模式无法写入 SE）** | **车端 - NFC 固件** |
| sw=0x6400（无 cccop=2） | **车端环境正常时，可能是手机端问题** | **手机端**（重新登录 iCloud 或重启手机） |
| 6A82（SELECT 阶段） | AID 不匹配，正常轮询行为 | ❌ 非故障 |

---

## cccop 工作模式值含义

| cccop 值 | 模式 | 对 NFC 刷卡的影响 |
|----------|------|------------------|
| 1 | 读写模式（正常） | 可以写入 ECP，刷卡成功 |
| 2 | 读卡模式（只读） | 只能读 ECP，**不能写入** → sw=0x6400 |
| 3 | 安全模式 | 仅安全通道通信 |

---

## 日志证据链（必须同时出现）

1. `NFC_iN ecp[4] = 1,conf->cccop = 2` — NFC 处于只读模式
2. `getdata_rsp sw=0x6400 error` — SE 访问失败（ISO 7816）
3. `ccc--bleERROR` 或 `ccc--bleparse_Notify_Sup->category = 1` — 手机端收到错误通知
4. 后续 `cccop` 恢复为 1，但 SE 错误仍持续（说明 ECP 参数未写入）

---

## 排查方向

1. 检查 NFC 固件版本（SW 版本号）
2. 核对 ACOSe 提供的 ECP 参数是否已写入 NFC
3. 确认 TBOX 是否配置了正确的 ECP 值（可通过 TBOX 配置写入）
4. 检查 NFC 初始化时 cccop 的默认值设置

---

## 车端日志搜索词

- `cccop` — NFC 工作模式
- `NFC_iN ecp` — ECP 配置状态
- `sw=0x6400` — SE 访问失败
- `getdata_rsp` — SE 响应
- `ccc--bleERROR` — CCC 协议层错误
- `ccc--bleparse_Notify` — BLE 通知解析
- `Pairstatus` — NFC 配对阶段（0=init → 4=paired），详见 `ccc_pairing.md`「配对阶段状态机」章节

### dk_service.log 文件来源模块

| 模块 | 说明 |
|------|------|
| `pair.cpp` | Owner Pairing 配对阶段 |
| `transaction.cpp` | 每次刷卡认证交易 |
| `NFC_iN` | NFC 输入（手机→车） |
| `NFC_oN` | NFC 输出（车→手机） |

---

## 相关 Ticket

- VCTCEM-16673 — CCC钥匙NFC门外刷卡无提醒（`cccop=2` 根因确认）

---

*最后更新：2026-05-12*
