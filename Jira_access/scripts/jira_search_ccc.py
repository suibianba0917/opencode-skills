# -*- coding: utf-8 -*-
import requests
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, '.')
from config.config import JIRA_URL, JIRA_TOKEN

jql = sys.argv[1] if len(sys.argv) > 1 else "Project=VCTCEM AND status != Open AND text ~ CCC AND (\"Solver Domain\" in (VCTC-AVC, VCTC-AV, AVC, AV) or \"Tester Domain\" in (VCTC-AVC, VCTC-AV, AVC, AV) OR assignee in (FI431KO, S66G6UH, DM7XTC4, TRFFX5C, UCBUK3Z, EM3O5WE, W0U9CN8, A1DV1HF, FGSK6DQ, FUZ368S, FDXQIUO, T04HQTX, VBJM1WT, VW7YXG4, UUC06RH, FSCQACG, E5WG6V1, FL4MZ9K, SRLKYUA, VRBQN6F, F2WNDNA, DH3KAAY, UVTLMTP, F2VI5SH, WP6KCF2, TCYWF6J, URJUNQ7, GUO2QH7, A3V41EH, TERKIWJ, FZEDXAY, G42WM3R, DRFI6K0, WRO2GH0, GE358GO) OR reporter in (FI431KO, S66G6UH, DM7XTC4, TRFFX5C, UCBUK3Z, EM3O5WE, W0U9CN8, A1DV1HF, FGSK6DQ, FUZ368S, FDXQIUO, T04HQTX, VBJM1WT, VW7YXG4, UUC06RH, FSCQACG, E5WG6V1, FL4MZ9K, SRLKYUA, VRBQN6F, F2WNDNA, DH3KAAY, UVTLMTP, F2VI5SH, WP6KCF2, TCYWF6J, URJUNQ7, GUO2QH7, A3V41EH, TERKIWJ, FZEDXAY, G42WM3R, DRFI6K0, WRO2GH0, GE358GO))"

session = requests.Session()
session.get(f'{JIRA_URL}/login.jsp', timeout=30)

headers = {
    'Authorization': f'Bearer {JIRA_TOKEN}',
    'Accept': 'application/json'
}

url = f'{JIRA_URL}/rest/api/2/search?jql={requests.utils.quote(jql)}&maxResults=100&fields=summary,status,project,issuetype,assignee,reporter'
resp = session.get(url, headers=headers, timeout=30)
data = resp.json()
issues = data.get('issues', [])
total = len(issues)

status_count = {}
for issue in issues:
    status = issue['fields']['status']['name']
    status_count[status] = status_count.get(status, 0) + 1

print(f'查询成功！共找到 {total} 条结果')
print()

sep = '=' * 80
print(sep)
header = f'{"状态":^15} | {"数量":^8}'
print(f'| {header} |')
print(sep)
for s, c in sorted(status_count.items(), key=lambda x: -x[1]):
    print(f'| {s:^15} | {c:^8} |')
print(sep)
print()

active = [i for i in issues if i['fields']['status']['name'] not in ('Closed', 'Resolved')]
if active:
    print(f'【活跃 Tickets ({len(active)} 条)】')
    print()
    for issue in active:
        key = issue['key']
        fields = issue['fields']
        status = fields['status']['name']
        summary = fields['summary'][:70]
        assignee = fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'
        print(f'{key} | {status} | {assignee} | {summary}')
    print()

print(f'【全部列表】')
print()
for issue in issues:
    key = issue['key']
    fields = issue['fields']
    status = fields['status']['name']
    summary = fields['summary'][:70]
    assignee = fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'
    print(f'{key} | {status} | {assignee} | {summary}')
