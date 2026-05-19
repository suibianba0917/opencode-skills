# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client

outlook = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")
inbox = namespace.GetDefaultFolder(6)

emails = inbox.Items
emails.Sort("[ReceivedTime]", True)

count = 0
for email in emails:
    if email.UnRead:
        count += 1

print(f"Unread emails: {count}")
