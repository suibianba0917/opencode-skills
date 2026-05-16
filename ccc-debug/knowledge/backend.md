# 数字钥匙后端服务配置问题

> 注：本章覆盖非 CCC 协议层、但影响配对/分享流程的车企后台配置问题。属于 CCC 调试的边界问题。

---

## 常见后台故障模式

### Profile 相关

| 错误特征 | 可能原因 | 归属端 |
|----------|----------|--------|
| `startPairing` 返回 HTTP 605 / 业务错误码 | VIN 对应数字钥匙 Profile 未在 CEA 后台创建/下发 | 后台 |
| `connect` → "Failed to check permission" | Profile 未下发到 SVW MDK FO，用户无权限创建钥匙 | 后台 |
| Profile 签名验证失败 | 苹果更换测试 Profile 导致签名校验失败，startPairing 返回业务错误 605 | 苹果后台 |
| 一键注销后 Profile 未重建 | Profile 残留但被删除重建流程缺失 | 后台 |

**排查方向**：
1. 确认 VIN 是否在 CEA 后台有数字钥匙 Profile
2. 检查 MDK FO 下发状态
3. 确认用户账号/VIN 绑定关系是否正确

**日志关键词**：
- `startPairing` — 配对初始化 API
- `Failed to check permission` — ICS SDK 权限校验失败
- `profile` / `Profile` — Profile 相关
- 业务层错误码（如 HTTP 605）

### Pretrack / KTS 相关

详见 `ccc_pairing.md` 第 4 章「钥匙分享故障模式 - Pretrack 检查要点」。

| 错误特征 | 可能原因 | 归属端 |
|----------|----------|--------|
| Pretrack 404 | Pretrack URL 配置错误 / 服务未部署 / nginx 路径遗漏 | 后台 |
| Pretrack DEFAULT_ERROR | Pretrack 验证失败，errorCode=99990004，data:false | 后台 |
| Pretrack keyId 未下发 | Pretrack 通过验证但 keyId 未下发到车端 | 后台 |
| KTS receipt 不匹配 | receipt 未正确存储或下发 | 后台 |
| ABR 路由配置错误 | 后端未收到 KTS 请求 | 后台 |
| 车辆关系解绑 | 用户与车辆绑定关系已解绑，errorCode=90000008 | 后台 |

### 短信 / 激活链接相关

| 错误特征 | 可能原因 | 归属端 |
|----------|----------|--------|
| 开卡短信 URL 不对 | 后台短信模板配置错误 | 后台 |
| 短信被运营商拦截/延迟 | DK 服务端发出领取通知短信，但被运营商拦截或消息中心长时间未处理，导致接收方超时未领取 | 后台（运营商/短信平台）|
| nginx 路径配置遗漏 | DK 后端 nginx 配置遗漏部分车型的 CCC 访问路径（corner case），导致钥匙分享后领取请求被 404 | 后台 |

### nginx 配置遗漏导致 404

- **场景**：钥匙分享后，接收方领取请求返回 HTTP 404
- **根因**：nginx 配置中缺少特定车型的 CCC 访问路径（/api/ccc/xxx 相关路径未配置）
- **排查**：
  1. 检查 nginx error.log 确认 404 请求路径
  2. 确认 VIN 对应的车型是否在 nginx 配置覆盖范围内
  3. 联系后台运维添加缺失路径

---

## 后台日志关键词

- `startPairing` / `start_pairing` — 配对初始化
- `profile` / `Profile` / `digital key profile`
- `MDK FO` / `MDK_FO` — MDK 前置条件
- `createDigitalKey` / `create_endpoint` — 钥匙创建
- `KTS receipt` / `receipt` — KTS 凭证
- `ABR` — Apple Backend Routing
- `Pretrack` / `trackKey` — 钥匙分享
- 业务层错误码：`605` / `606` / `90000008` / `99990004` 等非标准 HTTP 码
- `permission` / `unauthorized` — 权限校验
- `VEHICLE_RELATIONSHIP_UNBIND` — 车辆关系解绑
- `DEFAULT_ERROR` — 系统通用错误

---

## 参考 Ticket

**后台配置问题**：36257（receipt 未对应）, 29351（短信 URL 不对）, 26376（nginx 路径遗漏）
**Profile 问题**：35791（startPairing 605 + Profile 未下发）
**Profile 签名验证失败**：28325（苹果更换测试 Profile）
**车辆关系问题**：22690（ERROR_CODE_VEHICLE_RELATIONSHIP_UNBIND 90000008）
**OAuth 鉴权失败**：21967, 22135（90000011 用户订阅关系缺失）
**Pretrack 验证失败**：29194（DEFAULT_ERROR 99990004）
**keyId 未下发**：7531（Pretrack keyId 未下发到车端）

---

*最后更新：2026-05-14*
