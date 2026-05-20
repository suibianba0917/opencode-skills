# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json
import re
from datetime import datetime

PREFIXES = ["答复: ", "回复: ", "RE: ", "Re: ", "FW: ", "Fw: "]


def get_outlook():
    return win32com.client.Dispatch("Outlook.Application")


def get_folder(folder_id):
    outlook = get_outlook()
    namespace = outlook.GetNamespace("MAPI")
    return namespace.GetDefaultFolder(folder_id)


def strip_prefix(subject):
    for p in PREFIXES:
        if subject.startswith(p):
            return subject[len(p):]
    return subject


def normalize_subject(subject):
    s = strip_prefix(subject.strip())
    return s.strip()


def search_email_chain(keyword, max_results=100):
    outlook = get_outlook()
    namespace = outlook.GetNamespace("MAPI")

    results = []

    folders_to_search = {
        "Inbox": 6,
        "Sent Mail": 5,
        "Drafts": 2,
        "Outbox": 1,
    }

    for folder_name, folder_id in folders_to_search.items():
        try:
            folder = namespace.GetDefaultFolder(folder_id)
            for email in folder.Items:
                try:
                    if email.Subject and keyword.lower() in email.Subject.lower():
                        sent_time = getattr(email, "SentOn", None) or getattr(email, "ReceivedTime", None)
                        from datetime import datetime as dt
                        results.append({
                            "subject": email.Subject,
                            "normalized": normalize_subject(email.Subject),
                            "from_name": getattr(email, "SenderName", ""),
                            "from_email": getattr(email, "SenderEmailAddress", ""),
                            "to": getattr(email, "To", ""),
                            "cc": getattr(email, "CC", ""),
                            "time": str(sent_time) if sent_time else "",
                            "time_dt": sent_time,
                            "body": getattr(email, "Body", "") or "",
                            "html_body": getattr(email, "HTMLBody", "") or "",
                            "attachments": [a.FileName for a in getattr(email, "Attachments", [])],
                            "folder": folder_name,
                            "importance": getattr(email, "Importance", 1),
                            "unread": getattr(email, "UnRead", False),
                            "entry_id": getattr(email, "EntryID", ""),
                        })
                except Exception:
                    continue
        except Exception:
            continue

    results.sort(key=lambda x: x["time_dt"] if x["time_dt"] else datetime.min, reverse=True)
    for r in results:
        r.pop("time_dt", None)

    if not results:
        return {"status": "not_found", "keyword": keyword}

    latest = results[0]
    base_subject = normalize_subject(latest["subject"])

    chain = [r for r in results if normalize_subject(r["subject"]) == base_subject]

    return {
        "status": "found",
        "keyword": keyword,
        "base_subject": base_subject,
        "total_relevant": len(results),
        "chain_length": len(chain),
        "chain": chain,
    }


def extract_context(email):
    body = email.get("body", "")
    return {
        "subject": email["subject"],
        "sender": email["from_name"],
        "sender_email": email["from_email"],
        "to": email["to"],
        "cc": email["cc"],
        "time": email["time"],
        "body_preview": body[:3000] if body else "",
        "body_length": len(body),
        "attachments": email.get("attachments", []),
        "folder": email["folder"],
        "importance": email.get("importance", 1),
    }


def build_email_chain_tree(chain):
    if not chain:
        return []

    chain_sorted = sorted(chain, key=lambda x: x["time"])

    output = []
    for i, email in enumerate(chain_sorted):
        depth = i
        output.append({
            "index": i + 1,
            "subject": email["subject"],
            "sender": email["from_name"],
            "sender_email": email["from_email"],
            "time": email["time"],
            "body_preview": email["body"][:2000] if email["body"] else "",
            "folder": email["folder"],
        })
    return output


def extract_key_discussion_points(chain):
    all_text = " ".join([e.get("body", "") or "" for e in chain])

    patterns = {
        "技术问题": [r"问题", r"issue", r"bug", r"无法", r"失败", r"fail", r"error"],
        "解决方案": [r"方案", r"优化", r"建议", r"solution", r"fix", r"improve"],
        "认证要求": [r"MFI", r"认证", r"certification", r"Apple", r"豁免", r"exception"],
        "测试结果": [r"测试", r"test", r"pass", r"fail", r"通过", r"不满足"],
        "需确认事项": [r"请确认", r"请看下", r"帮忙", r"确认", r"是否能", r"是否可以"],
    }

    findings = {}
    for category, keywords in patterns.items():
        matches = []
        for kw in keywords:
            for match in re.finditer(kw, all_text, re.IGNORECASE):
                start = max(0, match.start() - 50)
                end = min(len(all_text), match.end() + 100)
                snippet = all_text[start:end].replace("\n", " ").strip()
                if snippet and snippet not in [m["snippet"] for m in matches]:
                    matches.append({"keyword": kw, "snippet": snippet})
        if matches:
            findings[category] = matches[:5]

    return findings


def analyze_and_suggest(chain, keyword_hint=""):
    if not chain:
        return {
            "status": "no_chain",
            "summary": "未找到邮件链",
            "reply_suggestion": "",
        }

    tree = build_email_chain_tree(chain)
    discussions = extract_key_discussion_points(chain)

    latest_email = chain[0]

    summary_parts = []
    summary_parts.append(f"邮件链共 {len(chain)} 封，主题：{chain[0]['subject']}")

    senders = {}
    for e in chain:
        s = e.get("from_name", "Unknown")
        senders[s] = senders.get(s, 0) + 1
    main_senders = sorted(senders.items(), key=lambda x: -x[1])
    summary_parts.append(f"主要发件人：{', '.join([f'{n}({c}封)' for n, c in main_senders[:3]])}")

    tech_issues = discussions.get("技术问题", [])
    if tech_issues:
        summary_parts.append(f"技术问题：{tech_issues[0]['snippet'][:100]}")

    tech_solutions = discussions.get("解决方案", [])
    if tech_solutions:
        summary_parts.append(f"解决方案：{tech_solutions[0]['snippet'][:100]}")

    cert_issues = discussions.get("认证要求", [])
    confirm_items = discussions.get("需确认事项", [])

    reply_suggestion = f"""## 回复建议

### 邮件背景
- 主题：{chain[0]['subject']}
- 邮件链共 {len(chain)} 封
- 最新邮件来自：{latest_email['from_name']}（{latest_email['time']}）

### 关键讨论点
"""

    if tech_issues:
        reply_suggestion += f"""
**技术问题**：{tech_issues[0]['snippet'][:200]}
"""
    if cert_issues:
        reply_suggestion += f"""
**认证相关**：{cert_issues[0]['snippet'][:200]}
"""
    if confirm_items:
        reply_suggestion += f"""
**待确认事项**：{confirm_items[0]['snippet'][:200]}
"""

    reply_suggestion += """
### 建议回复方向
请根据您的角色和立场，选择以下合适的回复方式：
1. 确认收到，提供技术分析
2. 提供文档依据，说明处理进展
3. Loop 相关同事跟进
"""

    return {
        "status": "analyzed",
        "summary": "\n".join(summary_parts),
        "chain_length": len(chain),
        "main_senders": dict(main_senders[:5]),
        "key_discussions": discussions,
        "latest_email": extract_context(latest_email),
        "reply_suggestion": reply_suggestion,
        "email_tree": tree,
    }


def run(keyword):
    search_result = search_email_chain(keyword)
    if search_result["status"] == "not_found":
        return search_result

    chain = search_result.get("chain", [])
    analysis = analyze_and_suggest(chain, keyword)

    return {
        "search": search_result,
        "analysis": analysis,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        keyword = sys.argv[1]
    else:
        keyword = sys.argv[1] if len(sys.argv) > 1 else ""

    if not keyword:
        print("Usage: python email_analysis.py <keyword>")
        sys.exit(1)

    result = run(keyword)
    print(json.dumps(result, ensure_ascii=False, indent=2))
