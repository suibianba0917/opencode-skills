# Skill: outlook

# Outlook Skill

## 概述

此技能使 opencode 能够与 Microsoft Outlook 进行交互，完成邮件管理任务，包括读取邮件、搜索、发送消息和处理附件。核心功能：**邮件上下文分析与回复建议生成**。

## 使用场景

当用户请求以下操作时使用此技能：
- **邮件上下文分析与回复建议**（新增）
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

---

## 核心功能：邮件上下文分析与回复建议

### 功能说明

给定邮件标题或关键词，自动：
1. 搜索并收集所有相关邮件历史（同一邮件链的所有往来）
2. 解析邮件链结构（发件人、收件人、时间线、嵌套层级）
3. 识别关键讨论点、技术问题、结论
4. 生成回复建议（包含立场、理由、文档依据）

### 使用方法

用户只需说：
- "分析邮件：CMP21_50W CWCD-NFC 手机NFC扫卡问题exchange"
- "给我这封邮件的回复建议"
- "回复建议：xxx邮件主题"

### 实现逻辑

脚本 `scripts/email_analysis.py` 负责：
1. **邮件搜索** — 按标题关键词搜索收件箱 + 已发送邮件
2. **邮件链构建** — 从 `Subject: 回复: xxx` 中提取完整邮件链
3. **上下文提取** — 识别发件人、讨论点、技术结论、待确认事项
4. **回复建议生成** — 结合分析结果和参考文档（如有）生成回复建议

### 工作流程

```
用户输入邮件标题/关键词
    │
    ▼
email_analysis.search_email_chain(keyword)
    │
    ├── 搜索收件箱匹配邮件
    ├── 搜索已发送邮件匹配邮件
    ├── 提取完整邮件链（包含内嵌历史正文）
    │
    ▼
email_analysis.extract_context(email)
    │
    ├── 解析发件人列表
    ├── 提取关键讨论点
    ├── 识别技术问题/结论
    ├── 标记待确认事项
    │
    ▼
生成回复建议 + 文档依据（如有）
```

---

## 基础方法

### 邮件上下文分析与回复建议（核心功能）

```python
# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client

def search_email_chain(keyword, max_results=50):
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")
    
    results = []
    
    # 搜索收件箱
    inbox = namespace.GetDefaultFolder(6)
    for email in inbox.Items:
        if keyword.lower() in email.Subject.lower():
            results.append({
                "subject": email.Subject,
                "from": email.SenderName,
                "from_email": email.SenderEmailAddress,
                "to": email.To,
                "cc": email.CC,
                "time": str(email.ReceivedTime),
                "body": email.Body,
                "folder": "Inbox",
                "unread": email.UnRead
            })
    
    # 搜索已发送邮件
    sent = namespace.GetDefaultFolder(5)
    for email in sent.Items:
        if keyword.lower() in email.Subject.lower():
            results.append({
                "subject": email.Subject,
                "from": email.SenderName,
                "from_email": email.SenderEmailAddress,
                "to": email.To,
                "cc": email.CC,
                "time": str(email.SentOn),
                "body": email.Body,
                "folder": "Sent Mail",
                "unread": False
            })
    
    # 按时间排序
    results.sort(key=lambda x: x["time"], reverse=True)
    return results[:max_results]


def extract_context(email):
    return {
        "subject": email["subject"],
        "sender": email["from"],
        "sender_email": email["from_email"],
        "recipients": email["to"],
        "cc": email["cc"],
        "time": email["time"],
        "body": email["body"][:5000] if email["body"] else "",
        "folder": email["folder"]
    }


def analyze_email_chain(keyword):
    emails = search_email_chain(keyword)
    if not emails:
        return {"status": "not_found", "keyword": keyword}
    
    # 提取上下文
    context = [extract_context(e) for e in emails]
    
    # 识别邮件链头（最早的一封）
    # 通常Subject去掉"答复: "和"回复: "前缀的就是原始主题
    base_subject = emails[0]["subject"]
    for prefix in ["答复: ", "回复: ", "RE: ", "Re: ", "FW: ", "Fw: "]:
        if base_subject.startswith(prefix):
            base_subject = base_subject[len(prefix):]
    
    # 分析关键讨论点
    all_bodies = " ".join([e.get("body", "") or "" for e in emails])
    
    return {
        "status": "found",
        "keyword": keyword,
        "total_emails": len(emails),
        "base_subject": base_subject,
        "emails": context,
        "analysis": {
            "summary": f"找到 {len(emails)} 封相关邮件",
            "sample_text": all_bodies[:2000]
        }
    }


if __name__ == "__main__":
    import json
    keyword = sys.argv[1] if len(sys.argv) > 1 else input("请输入邮件标题关键词: ")
    result = analyze_email_chain(keyword)
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

### 读取未读邮件

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
- `scripts/email_analysis.py` - 邮件上下文分析与回复建议生成
