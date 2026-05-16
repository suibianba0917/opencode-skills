#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA - 管理 Sprint
"""
import requests
import json
import sys
import io
import os
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.config import JIRA_URL, JIRA_TOKEN

def get_sprints(board_id):
    """获取 Board 的 Sprints"""
    if not JIRA_TOKEN:
        print("Error: JIRA_TOKEN not configured")
        return None
    
    session = requests.Session()
    session.get(f"{JIRA_URL}/login.jsp", timeout=30)
    
    headers = {
        'Authorization': f'Bearer {JIRA_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    resp = session.get(
        f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint",
        headers=headers,
        timeout=30
    )
    
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Error: {resp.status_code} - {resp.text[:200]}")
        return None

def create_sprint(name, board_id):
    """创建 Sprint"""
    if not JIRA_TOKEN:
        print("Error: JIRA_TOKEN not configured")
        return None
    
    session = requests.Session()
    session.get(f"{JIRA_URL}/login.jsp", timeout=30)
    
    headers = {
        'Authorization': f'Bearer {JIRA_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    sprint_data = {
        "name": name,
        "originBoardId": board_id
    }
    
    resp = session.post(
        f"{JIRA_URL}/rest/agile/1.0/sprint",
        headers=headers,
        json=sprint_data,
        timeout=30
    )
    
    if resp.status_code in [200, 201]:
        return resp.json()
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text[:500])
        return None

def main():
    parser = argparse.ArgumentParser(description='Manage JIRA Sprints')
    parser.add_argument('--board', '-b', type=int, default=4307, help='Board ID (default: 4307 EP)')
    parser.add_argument('--create', '-c', default=None, help='Create new sprint with name')
    parser.add_argument('--list', '-l', action='store_true', help='List sprints')
    
    args = parser.parse_args()
    
    if args.list or (not args.create):
        data = get_sprints(args.board)
        if data:
            print(f"=== Board {args.board} Sprints ===\n")
            for s in data.get('values', []):
                name = s.get('name', '')
                state = s.get('state', '')
                sprint_id = s.get('id', '')
                print(f"  [{state}] {name} (ID: {sprint_id})")
    
    if args.create:
        result = create_sprint(args.create, args.board)
        if result:
            print(f"\n✓ Sprint created: {result.get('name')} (ID: {result.get('id')})")

if __name__ == '__main__':
    main()
