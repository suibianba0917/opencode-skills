# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def send_email(to, subject, body, cc=None, bcc=None, html_body=None, attachments=None):
    outlook = win32com.client.Dispatch("Outlook.Application")
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
            mail.Attachments.Add(path)
    mail.Send()
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: send_email.py <to> <subject> <body> [cc]")
        sys.exit(1)

    to = sys.argv[1]
    subject = sys.argv[2]
    body = sys.argv[3]
    cc = sys.argv[4] if len(sys.argv) > 4 else None

    result = send_email(to, subject, body, cc=cc)
    print(json.dumps({"status": "sent" if result else "failed", "to": to, "subject": subject}))
