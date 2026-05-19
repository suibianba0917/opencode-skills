# Skill: outlook

# Outlook Skill

## 概述

此技能使 opencode 能够与 Microsoft Outlook 进行交互，完成邮件管理任务，包括读取邮件、搜索、发送消息和处理附件。

## 使用场景

当用户请求以下操作时使用此技能：
- 读取或列出收件箱中的邮件
- 按主题、发件人或内容搜索特定邮件
- 发送带或不带附件的新邮件
- 下载邮件附件
- 查看未读邮件
- 管理 Outlook 文件夹

## 前置条件

本地 Outlook 客户端（仅 Windows）：
- 系统上已安装 Microsoft Outlook
- pywin32 库：`pip install pywin32`

基于 Web 的 Outlook（企业账户）：
- 有效的 Outlook Web 凭据
- 浏览器自动化工具：`pip install playwright`

## 使用方法

### 读取未读邮件

列出收件箱中的未读邮件：

```python
import win32com.client

outlook = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")
inbox = namespace.GetDefaultFolder(6)

emails = inbox.Items
emails.Sort("[ReceivedTime]", True)

for email in emails:
    if email.UnRead:
        print(f"Subject: {email.Subject}")
        print(f"From: {email.SenderName}")
        print(f"Time: {email.ReceivedTime}")
        print("-" * 50)
```

### 获取邮件详情

获取完整邮件内容：

```python
import win32com.client

outlook = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")
inbox = namespace.GetDefaultFolder(6)

email = inbox.Items[0]

print(f"Subject: {email.Subject}")
print(f"From: {email.SenderName}")
print(f"Body: {email.Body}")
print(f"HTML Body: {email.HTMLBody}")
print(f"Attachments: {[a.FileName for a in email.Attachments]}")
```

### 搜索邮件

搜索邮件：

```python
import win32com.client

outlook = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")
inbox = namespace.GetDefaultFolder(6)

emails = inbox.Items

for email in emails:
    if "keyword" in email.Subject.lower():
        print(f"{email.Subject} - {email.SenderName}")
```

### 发送邮件

发送新邮件：

```python
import win32com.client

outlook = win32com.client.Dispatch("Outlook.Application")
mail = outlook.CreateItem(0)

mail.Subject = "邮件主题"
mail.Body = "邮件正文"
mail.HTMLBody = "<html><body><h1>你好</h1></body></html>"
mail.To = "recipient@example.com"
mail.CC = "cc@example.com"

mail.Send()
```

### 下载附件

下载邮件附件：

```python
import win32com.client
import os

outlook = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")
inbox = namespace.GetDefaultFolder(6)

email = inbox.Items[0]

save_dir = "downloads"
os.makedirs(save_dir, exist_ok=True)

for attachment in email.Attachments:
    attachment.SaveAsFile(os.path.join(save_dir, attachment.FileName))
    print(f"Saved: {attachment.FileName}")
```

### 获取所有文件夹

列出所有 Outlook 文件夹：

```python
import win32com.client

outlook = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")

for folder in namespace.Folders:
    print(f"{folder.Name}")
    for subfolder in folder.Folders:
        print(f"  - {subfolder.Name}")
```

## 文件夹常量

常用 Outlook 文件夹常量：
- `6` = olFolderInbox（收件箱）
- `5` = olFolderSentMail（已发送邮件）
- `3` = olFolderContacts（联系人）
- `4` = olFolderCalendar（日历）
- `2` = olFolderDrafts（草稿）
- `1` = olFolderOutbox（发件箱）
- `0` = olFolderDeletedItems（已删除邮件）

## 常用属性

邮件对象属性：
- `Subject` - 邮件主题
- `SenderName` - 发件人显示名称
- `SenderEmailAddress` - 发件人邮箱地址
- `ReceivedTime` - 接收时间
- `Body` - 纯文本正文
- `HTMLBody` - HTML 格式正文
- `To` - 收件人
- `CC` - 抄送
- `BCC` - 密送
- `Attachments` - 附件集合
- `UnRead` - 布尔值，未读时为 True
- `Size` - 大小（字节）
- `Importance` - 重要程度：0=低，1=普通，2=高
- `Categories` - 颜色分类

## 基于 Web 的 Outlook（企业账户）

对于没有本地客户端的企业 Outlook 账户：

1. 使用 Playwright/Selenium 自动化网页界面
2. 导航到 `https://outlook.office.com/mail/` 或组织的企业 Outlook Web URL
3. 处理身份验证（可能需要 MFA）
4. 使用选择器与邮件元素交互

## 错误处理

常见问题及解决方案：

1. **COM 错误**：确保 Outlook 已正确安装并运行
2. **权限被拒绝**：如需要，请以管理员身份运行
3. **编码错误**：对非 ASCII 文本使用 `encode('utf-8', 'ignore').decode()`
4. **项目未找到**：检查特定邮件的 EntryID

### 在 Windows 中处理中文/Unicode 文本输出

在 Windows 中打印包含中文的邮件时，可能会遇到 `UnicodeEncodeError`。使用以下解决方案：

**解决方案 1：使用 io.TextIOWrapper**

```python
# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import win32com.client
```

**解决方案 2：通过 PowerShell 使用 UTF-8 运行**

```powershell
powershell.exe -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; & 'python.exe' your_script.py"
```

**解决方案 3：设置环境变量**

```python
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
```

## 脚本文件说明

本技能包含以下脚本：
- `scripts/outlook_local.py` - 本地 Outlook COM 接口函数
- `scripts/outlook_web.py` - 基于 Web 的 Outlook 自动化
- `scripts/check_inbox.py` - 快速未读邮件检查器
