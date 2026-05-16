#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA - 创建子任务
"""
import requests
import json
import sys
import io
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.config import JIRA_URL, JIRA_TOKEN

def create_subtask(parent_key, summary, description='', assignee=None, priority=None):
    """创建子任务"""
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
    
    # 获取父任务的 project 信息
    resp = session.get(
        f"{JIRA_URL}/rest/api/2/issue/{parent_key}?fields=project",
        headers=headers,
        timeout=60
    )
    
    if resp.status_code != 200:
        print(f"Error: Cannot find parent issue {parent_key}")
        return None
    
    project_key = resp.json()['fields']['project']['key']
    
    # 创建子任务
    issue_data = {
        "fields": {
            "project": {"key": project_key},
            "parent": {"key": parent_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Sub-task"}
        }
    }
    
    if assignee:
        issue_data["fields"]["assignee"] = {"name": assignee}
    
    if priority:
        issue_data["fields"]["priority"] = {"name": priority}
    
    resp = session.post(
        f"{JIRA_URL}/rest/api/2/issue",
        headers=headers,
        json=issue_data,
        timeout=60
    )
    
    if resp.status_code == 201:
        return resp.json()
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)
        return None

def main():
    parser = argparse.ArgumentParser(description='Create JIRA sub-task')
    parser.add_argument('--parent', '-p', required=True, help='Parent ticket key (e.g., EP-184)')
    parser.add_argument('--summary', '-s', required=True, help='Sub-task summary')
    parser.add_argument('--description', '-d', default='', help='Sub-task description')
    parser.add_argument('--assignee', '-a', default=None, help='Assignee username')
    parser.add_argument('--priority', default=None, help='Priority (e.g., A1, Highest, High)')
    
    args = parser.parse_args()
    
    result = create_subtask(
        args.parent,
        args.summary,
        args.description,
        args.assignee,
        args.priority
    )
    
    if result:
        key = result.get('key')
        print(f"\n✓ Sub-task created: {key}")
        print(f"  Parent: {args.parent}")
        print(f"  URL: {JIRA_URL}/browse/{key}")

if __name__ == '__main__':
    main()
