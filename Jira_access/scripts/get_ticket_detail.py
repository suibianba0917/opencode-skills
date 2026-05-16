#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

# Ensure parent directory is in path for config imports
_script_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_script_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

import requests
import json
import io

# Check if color should be disabled
NO_COLOR = os.environ.get('NO_COLOR') or not sys.stdout.isatty()

if not NO_COLOR:
    try:
        from colorama import init, Fore, Style, just_fix_windows_console
        just_fix_windows_console()
        init(autoreset=True)
        HAS_COLOR = True
    except:
        HAS_COLOR = False
else:
    class Fore:
        RED = YELLOW = GREEN = CYAN = MAGENTA = WHITE = ''
    class Style:
        BRIGHT = ''
    HAS_COLOR = False

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.config import JIRA_URL, JIRA_TOKEN

def get_ticket_detail(key):
    if not JIRA_TOKEN:
        print("Error: JIRA_TOKEN not configured")
        return None
    
    session = requests.Session()
    session.get(f"{JIRA_URL}/login.jsp", timeout=30)
    
    headers = {
        'Authorization': f'Bearer {JIRA_TOKEN}',
        'Accept': 'application/json'
    }
    
    url = f"{JIRA_URL}/rest/api/2/issue/{key}"  # Get all fields including custom fields
    resp = session.get(url, headers=headers, timeout=30)
    
    if resp.status_code != 200:
        print(f"Error: {resp.status_code} - {resp.text[:500]}")
        return None
    
    data = resp.json()
    
    comments_url = f"{JIRA_URL}/rest/api/2/issue/{key}/comment?fields=created,updated,author,body"
    comments_resp = session.get(comments_url, headers=headers, timeout=30)
    
    comments = []
    if comments_resp.status_code == 200:
        comments = comments_resp.json().get('comments', [])
    
    return {'detail': data, 'comments': comments}

def format_description(desc):
    if not desc:
        return "(No description)"
    
    if isinstance(desc, dict):
        lines = []
        for block in desc.get('content', []):
            for item in block.get('content', []):
                lines.append(item.get('text', ''))
        return '\n'.join(lines)
    return desc

def status_color(status):
    if not HAS_COLOR:
        return ''
    status = status.lower() if status else ''
    if 'close' in status or 'done' in status:
        return Fore.GREEN
    if 'progress' in status or 'review' in status:
        return Fore.YELLOW
    if 'open' in status or 'todo' in status:
        return Fore.CYAN
    if 'verification' in status:
        return Fore.MAGENTA
    return Fore.WHITE

def priority_color(priority):
    if not HAS_COLOR:
        return ''
    priority = priority.upper() if priority else ''
    if priority in ['A', 'A1', 'BLOCKER', 'HIGHEST']:
        return Fore.RED
    if priority in ['B', 'HIGH']:
        return Fore.YELLOW
    if priority in ['C', 'MEDIUM']:
        return Fore.CYAN
    return Fore.WHITE

def get_attachments(key):
    """Get ticket attachments"""
    from config.config import JIRA_URL, JIRA_TOKEN
    
    session = requests.Session()
    session.get(f"{JIRA_URL}/login.jsp", timeout=30)
    
    headers = {'Authorization': f'Bearer {JIRA_TOKEN}', 'Accept': 'application/json'}
    url = f"{JIRA_URL}/rest/api/2/issue/{key}?fields=attachment"
    resp = session.get(url, headers=headers, timeout=30)
    
    if resp.status_code == 200:
        return resp.json().get('fields', {}).get('attachment', [])
    return []

def create_analysis_folders(output_dir, key, ticket_info):
    """创建标准化的分析过程文件夹"""
    from datetime import datetime
    import json
    
    analysis_dir = os.path.join(output_dir, "分析过程")
    os.makedirs(analysis_dir, exist_ok=True)
    
    f = ticket_info.get('fields', {})
    status = f.get("status", {}).get("name", "")
    priority = f.get("priority", {}).get("name", "")
    summary = f.get("summary", "")
    
    # 获取描述
    desc_text = ""
    desc = f.get('description', {})
    if isinstance(desc, dict):
        for block in desc.get('content', []):
            for item in block.get('content', []):
                text = item.get('text', '')
                if text:
                    desc_text += text + "\n"
    
    content = f"""# {key} 分析过程记录

## 问题基本信息

| 项目 | 内容 |
|------|------|
| **Ticket** | {key} |
| **状态** | {status} |
| **优先级** | {priority} |
| **摘要** | {summary} |
| **创建时间** | {f.get('created', '')[:10]} |
| **更新时间** | {f.get('updated', '')[:10]} |

## 问题描述
{desc_text.strip()}

## 日志来源

### 已下载日志
| 文件名 | 大小 | 上传时间 | 说明 |
|--------|------|----------|------|
| | | | |

## 日志分析过程

### Step 1: 解压日志
```powershell
# 7z解压
& "C:\\Program Files\\7-Zip\\7z.exe" x -o"./extracted" "android_2.7z.001"
& "C:\\Program Files\\7-Zip\\7z.exe" x -o"./extracted" "tbox_2.7z.001"

# 解压zip
Expand-Archive -Path "*.zip" -DestinationPath "extracted"
```

### Step 2: 搜索关键词
```powershell
# 搜索数字钥匙相关
Select-String -Path "main.txt" -Pattern "dk_|carkey|CarKey|DIGITAL_KEY|数字钥匙"

# 搜索T-Box日志
Select-String -Path "dk_service.log" -Pattern "key|delete|注销|HeartBeat"

# 搜索OneApp日志
Select-String -Path "flutter*.log" -Pattern "getKeyList|CarKeyManager|key"
```

## 分析结论

### 故障定位
| 归属端 | 判断 | 依据 |
|--------|------|------|
| | | |

### 日志完整性评级: **级**

## 下一步行动

### 需要补充的日志


### 排查方向

---
*分析时间: {datetime.now().strftime('%Y-%m-%d')}*
*分析人: opencode*
"""
    
    readme_path = os.path.join(analysis_dir, "分析过程说明.md")
    with open(readme_path, 'w', encoding='utf-8') as rf:
        rf.write(content)
    
    print(f"已创建分析过程文件夹: {analysis_dir}")
    return analysis_dir

def download_attachments(key, attachments, output_dir, ticket_info=None):
    """Download ticket attachments"""
    from config.config import JIRA_URL, JIRA_TOKEN
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 先创建分析过程文件夹
    if ticket_info:
        create_analysis_folders(output_dir, key, ticket_info)
    
    session = requests.Session()
    session.get(f"{JIRA_URL}/login.jsp", timeout=30)
    headers = {'Authorization': f'Bearer {JIRA_TOKEN}'}
    
    downloaded = []
    for att in attachments:
        att_id = att.get('id')
        filename = att.get('filename')
        url = f"{JIRA_URL}/secure/attachment/{att_id}/{filename}"
        output_path = os.path.join(output_dir, filename)
        
        print(f'Downloading {filename}...')
        resp = session.get(url, headers=headers, timeout=300, stream=True)
        
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f'  Saved: {size_mb:.1f} MB')
            downloaded.append(output_path)
        else:
            print(f'  Error: {resp.status_code}')
    
    return downloaded

def get_field_value(field):
    """Helper to extract value from field (handles dict/list/string)"""
    if field is None:
        return ""
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        # Handle fields with child (like Platform/Project)
        if field.get('child'):
            child_val = field.get('child', {}).get('value', '')
            parent_val = field.get('value', '')
            if child_val and parent_val:
                return f"{parent_val} - {child_val}"
            return child_val or parent_val or str(field)
        return field.get('name', field.get('value', str(field)))
    if isinstance(field, list):
        if not field:
            return ""
        return ", ".join([get_field_value(v) for v in field])
    return str(field)

def get_custom_field(f, field_ids):
    """Get custom field value by field IDs or names"""
    for field_id in field_ids:
        val = f.get(field_id)
        if val:
            return get_field_value(val)
    return ""

def get_all_important_fields(f):
    """Get all important custom fields with their display names"""
    important = {}
    
    # Map of field IDs to display names (corrected)
    field_map = {
        'customfield_19403': 'frequency',
        'customfield_19482': 'Defect Category',
        'customfield_19484': '问题类型',
        'customfield_19486': '相关模块',
        'customfield_19705': '问题类型2',
        'customfield_19706': '严重等级',
        'customfield_19814': '相关模块2',
        'customfield_20757': 'Issue Objective',
        'customfield_20759': 'Platform & Project',
        'customfield_20760': 'Vehicle info',
        'customfield_20761': 'Tester Domain',
        'customfield_20765': 'Issue Analysis',
        'customfield_20774': 'Solver Domain',
        'customfield_24502': 'E/E Baseline',
        'customfield_24503': 'Affected baseline/s',
        'customfield_15042': 'Interfaces',
        'customfield_15043': 'Verification method',
        'customfield_15372': '测试级别',
        'customfield_15375': '测试类型',
    }
    
    for field_id, display_name in field_map.items():
        val = f.get(field_id)
        if val:
            # Handle list values
            if isinstance(val, list):
                if val:
                    important[display_name] = ', '.join([get_field_value(v) for v in val])
            else:
                important[display_name] = get_field_value(val)
    
    return important

if __name__ == '__main__':
    key = sys.argv[1] if len(sys.argv) > 1 else 'VCTCEM-26376'
    use_json = '--json' in sys.argv
    sys.argv = [a for a in sys.argv if a != '--json']

    result = get_ticket_detail(key)

    if result:
        if use_json:
            output = {
                'key': key,
                'summary': result['detail'].get('fields', {}).get('summary', ''),
                'description': result['detail'].get('fields', {}).get('description', ''),
                'status': result['detail'].get('fields', {}).get('status', {}).get('name', ''),
                'created': result['detail'].get('fields', {}).get('created', ''),
                'updated': result['detail'].get('fields', {}).get('updated', ''),
                'comments': result['comments'],
                'all_fields': result['detail'].get('fields', {}),
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
            sys.exit(0)

        f = result['detail'].get('fields', {})
        f = result['detail'].get('fields', {})
        comments = result['comments']
        
        # Header
        header_color = Fore.CYAN + Style.BRIGHT if HAS_COLOR else ''
        reset = Style.RESET_ALL if HAS_COLOR else ''
        print(f'{header_color}============================================================{reset}')
        print(f'{header_color}  {key}{reset}')
        print(f'{header_color}============================================================{reset}')
        print()
        
        # Basic Info
        bright = Style.BRIGHT if HAS_COLOR else ''
        white = Fore.WHITE if HAS_COLOR else ''
        yellow = Fore.YELLOW if HAS_COLOR else ''
        green = Fore.GREEN if HAS_COLOR else ''
        cyan = Fore.CYAN if HAS_COLOR else ''
        
        print(f'{bright}【基本信息】')
        status = f.get("status", {}).get("name", "")
        priority = f.get("priority", {}).get("name", "")
        resolution = f.get("resolution", {})
        
        print(f'  {bright}Type:       ' + white + f.get("issuetype", {}).get("name", ""))
        print(f'  {bright}Status:     ', end='')
        print(status_color(status) + status)
        
        if resolution:
            res_val = get_field_value(resolution)
            if res_val:
                print(f'  {bright}Resolution: ' + green + res_val)
        
        print(f'  {bright}Priority:   ', end='')
        print(priority_color(priority) + priority)
        
        print(f'  {bright}Assignee:   ' + yellow + f.get("assignee", {}).get("displayName", ""))
        print(f'  {bright}Reporter:   ' + white + f.get("reporter", {}).get("displayName", ""))
        print(f'  {bright}Created:    ' + white + f.get("created", "")[:10])
        print(f'  {bright}Updated:    ' + white + f.get("updated", "")[:10])
        
        # Versions
        fix_versions = f.get("fixVersions", [])
        versions = f.get("versions", [])
        affects_versions = f.get("versions", [])
        
        print(f'  {bright}Fix Version/s:   ' + white + (", ".join([get_field_value(v) for v in fix_versions]) if fix_versions else "None"))
        print(f'  {bright}Affects Version/s: ' + white + (", ".join([get_field_value(v) for v in affects_versions]) if affects_versions else "-"))
        
        # Components
        components = f.get("components", [])
        print(f'  {bright}Component/s:    ' + white + (", ".join([get_field_value(c) for c in components]) if components else "None"))
        
        # Security
        security = f.get("security", {})
        if security:
            print(f'  {bright}Security Level: ' + green + get_field_value(security))
        
        # Labels
        labels = f.get("labels", [])
        print(f'  {bright}Labels:      ' + white + (", ".join(labels) if labels else "None"))
        print()
        
        # Project Info
        print(f'{bright}【项目信息】')
        project = f.get("project", {})
        if project:
            print(f'  {bright}Project:     ' + white + project.get("name", "") + f" ({project.get('key', '')})")
        
        # Platform & Project (custom field)
        platform = get_custom_field(f, ['customfield_20759'])
        if platform:
            print(f'  {bright}Platform:    ' + white + platform)
        
        # Security level
        security = f.get("security", {})
        if security:
            print(f'  {bright}Security:    ' + white + get_field_value(security))
        print()
        
        # Summary
        print(f'{bright}【摘要】')
        print(f'{white}  {f.get("summary")}')
        print()
        
        # Description
        print(f'{bright}【描述】')
        desc = format_description(f.get('description'))
        for line in desc.split('\n'):
            print(f'  {white}{line}')
        print()
        
        # Key Custom Fields
        print(f'{bright}【关键自定义字段】')
        
        important_fields = get_all_important_fields(f)
        
        if important_fields:
            for field_name, field_val in important_fields.items():
                if field_val:
                    print(f'  {bright}{field_name}: ' + white + str(field_val)[:200])
        else:
            print(f'  {white}(No key custom fields)')
        print()
        
        # All Comments
        if comments:
            cyan = Fore.CYAN if HAS_COLOR else ''
            print(f'{bright}【评论】({len(comments)}条)')
            for i, c in enumerate(comments, 1):
                body = c.get('body', {})
                author = c.get('author', {}).get('displayName', 'Unknown')
                created = c.get('created', '')[:16]
                
                print(f'  {cyan}--- Comment {i} [{created}] {author} ---')
                if isinstance(body, dict):
                    for block in body.get('content', []):
                        for item in block.get('content', []):
                            text = item.get('text', '')
                            if text:
                                print(f'  {white}{text}')
                else:
                    print(f'  {white}{body}')
                print()
        
        # Latest Conclusion (at the end)
        if comments:
            conc_color = Fore.CYAN + bright if HAS_COLOR else ''
            print(f'{conc_color}【最新结论】')
            recent_comments = comments[-3:]
            green = Fore.GREEN if HAS_COLOR else ''
            for c in recent_comments:
                body = c.get('body', {})
                author = c.get('author', {}).get('displayName', 'Unknown')
                created = c.get('created', '')[:16]
                
                text_content = []
                if isinstance(body, dict):
                    for block in body.get('content', []):
                        for item in block.get('content', []):
                            text = item.get('text', '')
                            if text:
                                text_content.append(text)
                else:
                    text_content.append(str(body))
                
                valid_text = [t for t in text_content if t and not t.strip().startswith('!')]
                if valid_text:
                    print(f'  {green}[{created}] {author}:')
                    for t in valid_text:
                        print(f'    {white}{t}')
                    print()
        
        # Change history
        changelog = f.get('changelog', {}).get('histories', [])
        if changelog:
            recent_changes = changelog[-10:]
            yellow = Fore.YELLOW if HAS_COLOR else ''
            print(f'{bright}【变更历史】(最近{len(recent_changes)}条)')
            for h in recent_changes:
                created = h.get('created', '')[:16]
                author = h.get('author', {}).get('displayName', 'Unknown')
                print(f'  {yellow}--- {created} by {author} ---')
                for item in h.get('items', []):
                    field = item.get('field', '')
                    from_val = item.get('fromString', '')
                    to_val = item.get('toString', '')
                    if from_val or to_val:
                        print(f'    {field}: {from_val} -> {to_val}')
                print()
        
        # Check if ticket is unresolved and offer to download logs
        status = f.get('status', {}).get('name', '').lower()
        resolved_statuses = ['done', 'closed', 'resolved', 'completed']
        is_unresolved = not any(s in status for s in resolved_statuses)
        
        if is_unresolved:
            print(f'\n{"="*60}')
            yellow = Fore.YELLOW if HAS_COLOR else ''
            print(f'{yellow}该Ticket尚未解决')
            print(f'{yellow}如需下载日志并分析，请回复: log 或 分析')
            print(f'{"="*60}')
            
            # Check if called with --auto flag (non-interactive)
            if '--auto' not in sys.argv:
                try:
                    user_input = input('\n是否下载日志并分析? (y/n): ').strip().lower()
                    if user_input in ['y', 'yes', '是', 'log', '分析']:
                        print('\n获取附件列表...')
                        attachments = get_attachments(key)
                        if attachments:
                            print(f'找到 {len(attachments)} 个附件')
                            output_dir = os.path.join('Y:', 'JIRA_Logs', key)
                            downloaded = download_attachments(key, attachments, output_dir, result['detail'])
                            print(f'\n已下载 {len(downloaded)} 个文件到: {output_dir}')
                            print('已自动创建分析过程文件夹: 分析过程/分析过程说明.md')
                            print('\n可使用 ccc-debug skill 进行分析')
                        else:
                            print('无附件可下载')
                except EOFError:
                    pass  # Non-interactive mode
