#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA - 添加 Ticket 到 Sprint
"""
import requests
import sys
import io
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.config import JIRA_URL, JIRA_TOKEN

def add_to_sprint(ticket_keys, sprint_id):
    """添加 ticket 到 sprint"""
    if not JIRA_TOKEN:
        print("Error: JIRA_TOKEN not configured")
        return False
    
    session = requests.Session()
    session.get(f"{JIRA_URL}/login.jsp", timeout=60)
    
    headers = {
        'Authorization': f'Bearer {JIRA_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    if isinstance(ticket_keys, str):
        ticket_keys = [ticket_keys]
    
    resp = session.post(
        f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue",
        headers=headers,
        json={'issues': ticket_keys},
        timeout=60
    )
    
    if resp.status_code in [200, 204, 201]:
        return True
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)
        return False

def main():
    parser = argparse.ArgumentParser(description='Add ticket to sprint')
    parser.add_argument('--ticket', '-t', required=True, nargs='+', help='Ticket key(s) (e.g., EP-184)')
    parser.add_argument('--sprint', '-s', required=True, type=int, help='Sprint ID (e.g., 8837 for Sprint 2606)')
    
    args = parser.parse_args()
    
    result = add_to_sprint(args.ticket, args.sprint)
    
    if result:
        tickets = ', '.join(args.ticket)
        print(f"Added {tickets} to Sprint {args.sprint}")

if __name__ == '__main__':
    main()
