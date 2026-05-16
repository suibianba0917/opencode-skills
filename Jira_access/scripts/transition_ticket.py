#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JIRA - Ticket 状态流转
"""
import requests
import json
import sys
import io
import argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.config import JIRA_URL, JIRA_TOKEN

def get_transitions(ticket_key):
    """获取 ticket 可用的状态流转"""
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
        f"{JIRA_URL}/rest/api/2/issue/{ticket_key}/transitions",
        headers=headers,
        timeout=60
    )
    
    if resp.status_code == 200:
        data = resp.json()
        transitions = data.get('transitions', [])
        print(f"\n=== Available transitions for {ticket_key} ===\n")
        for t in transitions:
            print(f"  [{t['id']}] {t['name']}")
        print()
        return data
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)
        return None

def transition_ticket(ticket_key, transition_id=None, transition_name=None):
    """执行状态流转"""
    if not JIRA_TOKEN:
        print("Error: JIRA_TOKEN not configured")
        return False
    
    session = requests.Session()
    session.get(f"{JIRA_URL}/login.jsp", timeout=60)
    
    headers = {
        'Authorization': f'Bearer {JIRA_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # 如果没有提供 transition_id 或 name，显示可用选项
    if not transition_id and not transition_name:
        data = get_transitions(ticket_key)
        if data:
            transitions = data.get('transitions', [])
            print(f"\n=== Available transitions for {ticket_key} ===\n")
            for t in transitions:
                print(f"  [{t['id']}] {t['name']}")
            print()
        return False
    
    # 如果提供了名称，查找对应的 ID
    if transition_name and not transition_id:
        data = get_transitions(ticket_key)
        if data:
            transitions = data.get('transitions', [])
            for t in transitions:
                if t['name'].lower() == transition_name.lower():
                    transition_id = t['id']
                    break
            
            if not transition_id:
                print(f"Error: Transition '{transition_name}' not found")
                return False
    
    # 执行流转
    resp = session.post(
        f"{JIRA_URL}/rest/api/2/issue/{ticket_key}/transitions",
        headers=headers,
        json={'transition': {'id': transition_id}},
        timeout=60
    )
    
    if resp.status_code in [200, 204, 201]:
        return True
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)
        return False

def main():
    parser = argparse.ArgumentParser(description='Transition JIRA ticket status')
    parser.add_argument('--ticket', '-t', required=True, help='Ticket key (e.g., EP-184)')
    parser.add_argument('--transition', '-tr', default=None, help='Transition name (e.g., "In Progress", "Done")')
    parser.add_argument('--id', '-i', default=None, help='Transition ID')
    parser.add_argument('--list', '-l', action='store_true', help='List available transitions')
    
    args = parser.parse_args()
    
    # 如果指定了 --list 或没有指定 transition，显示可用选项
    if args.list or (not args.transition and not args.id):
        get_transitions(args.ticket)
        return
    
    result = transition_ticket(args.ticket, args.id, args.transition)
    
    if result:
        print(f"Transitioned {args.ticket} to '{args.transition or args.id}'")

if __name__ == '__main__':
    main()
