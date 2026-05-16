#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA - 查看 Sprint 中的 Issues
"""
import requests
import json
import sys
import io
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.config import JIRA_URL, JIRA_TOKEN

def get_sprint_issues(sprint_id):
    """获取 Sprint 中的 issues"""
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
    
    resp = session.get(
        f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue",
        headers=headers,
        timeout=60
    )
    
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)
        return None

def main():
    parser = argparse.ArgumentParser(description='Get issues in a sprint')
    parser.add_argument('--sprint', '-s', required=True, type=int, help='Sprint ID (e.g., 8837 for Sprint 2606)')
    parser.add_argument('--output', '-o', default=None, help='Output file (JSON)')
    
    args = parser.parse_args()
    
    data = get_sprint_issues(args.sprint)
    
    if data:
        issues = data.get('issues', [])
        print(f"\n=== Sprint {args.sprint} - {len(issues)} issues ===\n")
        
        for issue in issues:
            key = issue['key']
            fields = issue['fields']
            summary = fields.get('summary', '')
            status = fields.get('status', {}).get('name', '')
            priority = fields.get('priority', {}).get('name', '')
            issuetype = fields.get('issuetype', {}).get('name', '')
            assignee = fields.get('assignee', {})
            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
            
            print(f"[{key}] {issuetype} - {priority}")
            print(f"  {summary}")
            print(f"  Status: {status} | Assignee: {assignee_name}")
            print()
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Saved to {args.output}")

if __name__ == '__main__':
    main()
