#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA - 更新 Ticket 信息
"""
import requests
import json
import sys
import io
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.config import JIRA_URL, JIRA_TOKEN

def update_ticket(ticket_key, summary=None, description=None, priority=None, assignee=None, status=None):
    """更新 ticket 信息"""
    if not JIRA_TOKEN:
        print("Error: JIRA_TOKEN not configured")
        return None
    
    session = requests.Session()
    session.get(f"{JIRA_URL}/login.jsp", timeout=60)
    
    headers = {
        'Authorization': f'Bearer {JIRA_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    fields = {}
    if summary:
        fields['summary'] = summary
    if description:
        fields['description'] = description
    if priority:
        fields['priority'] = {'name': priority}
    if assignee:
        fields['assignee'] = {'name': assignee}
    
    update_data = {'fields': fields}
    
    resp = session.put(
        f"{JIRA_URL}/rest/api/2/issue/{ticket_key}",
        headers=headers,
        json=update_data,
        timeout=60
    )
    
    if resp.status_code in [200, 204, 201]:
        return True
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)
        return False

def main():
    parser = argparse.ArgumentParser(description='Update JIRA ticket')
    parser.add_argument('--ticket', '-t', required=True, help='Ticket key (e.g., EP-184)')
    parser.add_argument('--summary', '-s', default=None, help='New summary')
    parser.add_argument('--description', '-d', default=None, help='New description')
    parser.add_argument('--priority', '-p', default=None, help='Priority (e.g., A1, Highest, High)')
    parser.add_argument('--assignee', '-a', default=None, help='Assignee username')
    
    args = parser.parse_args()
    
    if not any([args.summary, args.description, args.priority, args.assignee]):
        print("Error: At least one field to update is required")
        return
    
    result = update_ticket(
        args.ticket,
        args.summary,
        args.description,
        args.priority,
        args.assignee
    )
    
    if result:
        print(f"Updated {args.ticket}")

if __name__ == '__main__':
    main()
