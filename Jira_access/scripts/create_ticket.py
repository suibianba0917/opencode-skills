#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA - 创建新 ticket
"""
import requests
import json
import sys
import io
import os
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.config import JIRA_URL, JIRA_TOKEN

def find_sprint_id(session, headers, sprint_name, project_key):
    """根据 sprint 名称查找 sprint ID"""
    # 常用 board ID 映射
    board_map = {
        'EP': 4307,
        'OBAS': 4307,
        'CEA': 4307,
    }
    
    board_id = board_map.get(project_key, 4307)
    
    resp = session.get(
        f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint",
        headers=headers,
        timeout=30
    )
    
    if resp.status_code == 200:
        sprints = resp.json().get('values', [])
        for s in sprints:
            if sprint_name.lower() in s.get('name', '').lower():
                return s['id']
    
    return None

def add_to_sprint(session, headers, ticket_key, sprint_id):
    """将 ticket 添加到 sprint"""
    resp = session.post(
        f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue",
        headers=headers,
        json={'issues': [ticket_key]},
        timeout=30
    )
    return resp.status_code in [200, 204, 201]

def create_ticket(project, summary, description, issue_type='Task', assignee=None, sprint=None, priority=None, parent=None):
    """创建 JIRA ticket"""
    if not JIRA_TOKEN:
        print("Error: JIRA_TOKEN not configured")
        return None
    
    session = requests.Session()
    session.get(f"{JIRA_URL}/login.jsp", timeout=30)
    
    headers = {
        'Authorization': f'Bearer {JIRA_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # 如果指定了 parent，自动获取 project
    if parent:
        resp = session.get(
            f"{JIRA_URL}/rest/api/2/issue/{parent}?fields=project",
            headers=headers,
            timeout=30
        )
        if resp.status_code == 200:
            project = resp.json()['fields']['project']['key']
        if issue_type == 'Task':
            issue_type = 'Sub-task'
    
    issue_data = {
        "fields": {
            "project": {"key": project},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type}
        }
    }
    
    if parent:
        issue_data["fields"]["parent"] = {"key": parent}
    
    if assignee:
        issue_data["fields"]["assignee"] = {"name": assignee}
    
    if priority:
        issue_data["fields"]["priority"] = {"name": priority}
    
    resp = session.post(
        f"{JIRA_URL}/rest/api/2/issue",
        headers=headers,
        json=issue_data,
        timeout=30
    )
    
    if resp.status_code == 201:
        result = resp.json()
        
        # 如果指定了 sprint，添加到 sprint
        if sprint:
            ticket_key = result.get('key')
            sprint_id = None
            
            # 判断 sprint 是 ID 还是名称
            if isinstance(sprint, int):
                sprint_id = sprint
            elif sprint.isdigit():
                sprint_id = int(sprint)
            else:
                # 根据 sprint 名称查找 ID
                sprint_id = find_sprint_id(session, headers, sprint, project)
            
            if sprint_id:
                add_to_sprint(session, headers, ticket_key, sprint_id)
        
        return result
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)
        return None

def main():
    parser = argparse.ArgumentParser(description='Create JIRA ticket')
    parser.add_argument('--project', '-p', default='OBAS', help='Project key')
    parser.add_argument('--summary', '-s', required=True, help='Ticket summary')
    parser.add_argument('--description', '-d', default='', help='Ticket description')
    parser.add_argument('--type', '-t', default='Task', help='Issue type (Task/Story/Bug/Epic/Sub-task)')
    parser.add_argument('--assignee', '-a', default=None, help='Assignee username')
    parser.add_argument('--sprint', default=None, help='Sprint name (e.g., "EP Sprint 2606") or ID')
    parser.add_argument('--priority', default=None, help='Priority (e.g., A1, Highest, High)')
    parser.add_argument('--parent', default=None, help='Parent ticket key (for creating sub-task)')
    
    args = parser.parse_args()
    
    result = create_ticket(
        args.project,
        args.summary,
        args.description,
        args.type,
        args.assignee,
        args.sprint,
        args.priority,
        args.parent
    )
    
    if result:
        key = result.get('key')
        print(f"\n✓ Ticket created: {key}")
        if args.parent:
            print(f"  Parent: {args.parent}")
        print(f"  URL: {JIRA_URL}/browse/{key}")

if __name__ == '__main__':
    main()
