---
name: feishu
description: 飞书消息发送 - 通过Webhook发送消息到飞书群
version: 1.0
author: default
---

# 飞书消息 Skill

## 功能

通过飞书Webhook发送消息到指定群聊。

## 配置

Webhook地址已配置：
```
https://open.feishu.cn/open-apis/bot/v2/hook/113f3db8-5da9-4efc-b95c-a197820ccd86
```

## 使用方式

直接说"发消息到飞书"或"发送飞书消息"，然后提供消息内容。

## 示例

- "发消息到飞书：测试一下"
- "发送飞书消息：今天的CCC测试结果已出"

## 消息类型

支持：
- 纯文本 (text)
- 富文本 (post)

## 限制

- 仅支持发送消息，不支持读取
- 机器人名称为"自动化助手"
