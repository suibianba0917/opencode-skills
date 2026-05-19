# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import os


def get_outlook():
    return win32com.client.Dispatch("Outlook.Application")


def get_inbox(folder_id=6):
    outlook = get_outlook()
    namespace = outlook.GetNamespace("MAPI")
    return namespace.GetDefaultFolder(folder_id)


def list_unread_emails(limit=10):
    inbox = get_inbox()
    emails = inbox.Items
    emails.Sort("[ReceivedTime]", True)
    count = 0
    results = []
    for email in emails:
        if email.UnRead and count < limit:
            results.append({
                "subject": email.Subject,
                "from": email.SenderName,
                "time": str(email.ReceivedTime),
                "preview": email.Body[:200] if email.Body else ""
            })
            count += 1
    return results


def get_email_detail(index=0):
    inbox = get_inbox()
    emails = inbox.Items
    emails.Sort("[ReceivedTime]", True)
    email = emails[index]
    return {
        "subject": email.Subject,
        "from": email.SenderName,
        "from_address": email.SenderEmailAddress,
        "to": email.To,
        "cc": email.CC,
        "body": email.Body,
        "html_body": email.HTMLBody,
        "time": str(email.ReceivedTime),
        "attachments": [a.FileName for a in email.Attachments],
        "unread": email.UnRead,
        "importance": email.Importance
    }


def search_emails(keyword, folder_id=6):
    inbox = get_inbox(folder_id)
    emails = inbox.Items
    results = []
    for email in emails:
        if keyword.lower() in email.Subject.lower() or (email.Body and keyword.lower() in email.Body.lower()):
            results.append({
                "subject": email.Subject,
                "from": email.SenderName,
                "time": str(email.ReceivedTime)
            })
    return results


def send_email(to, subject, body, cc=None, bcc=None, html_body=None, attachments=None):
    outlook = get_outlook()
    mail = outlook.CreateItem(0)
    mail.Subject = subject
    mail.Body = body
    if html_body:
        mail.HTMLBody = html_body
    mail.To = to
    if cc:
        mail.CC = cc
    if bcc:
        mail.BCC = bcc
    if attachments:
        for path in attachments:
            if os.path.exists(path):
                mail.Attachments.Add(path)
    mail.Send()
    return True


def download_attachments(index=0, save_dir="downloads"):
    inbox = get_inbox()
    emails = inbox.Items
    emails.Sort("[ReceivedTime]", True)
    email = emails[index]
    os.makedirs(save_dir, exist_ok=True)
    saved = []
    for attachment in email.Attachments:
        path = os.path.join(save_dir, attachment.FileName)
        attachment.SaveAsFile(path)
        saved.append(path)
    return saved


def list_folders():
    outlook = get_outlook()
    namespace = outlook.GetNamespace("MAPI")
    results = []
    for folder in namespace.Folders:
        results.append({"name": folder.Name, "folders": [f.Name for f in folder.Folders]})
    return results
