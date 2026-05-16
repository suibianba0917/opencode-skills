#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polarion REST API Client
"""

import os
import sys
import json
import argparse
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

DEFAULT_POLARION_URL = "https://polarion.intranet.vwg-cea.cn/polarion"

POLARION_URL = os.environ.get("POLARION_URL", "")
POLARION_TOKEN = os.environ.get("POLARION_TOKEN", "")


def get_config():
    """Get URL and Token, prompt if missing."""
    global POLARION_URL, POLARION_TOKEN
    
    # URL
    if not POLARION_URL:
        print("=" * 50)
        print("Polarion URL 未配置，使用默认或手动输入")
        print(f"默认: {DEFAULT_POLARION_URL}")
        print("-" * 50)
        url_input = input("直接回车使用默认，或输入自定义 URL: ").strip()
        POLARION_URL = url_input if url_input else DEFAULT_POLARION_URL
    
    # Token
    if not POLARION_TOKEN:
        print("\n" + "=" * 50)
        print("Polarion Token 未配置！")
        print("=" * 50)
        print("获取 Token 方法：")
        print("1. 登录 https://polarion.intranet.vwg-cea.cn/polarion/")
        print("2. 点击右上角头像 → Personal Settings")
        print("3. 点击 Personal Access Tokens")
        print("4. Create new token → 复制 JWT token")
        print("-" * 50)
        POLARION_TOKEN = input("请输入 Token: ").strip()
        if not POLARION_TOKEN:
            print("\n错误: Token 不能为空，程序退出")
            return False
    
    return True


def make_request(endpoint, method="GET", data=None, params=None):
    """Make HTTP request to Polarion API."""
    if not get_config():  # 确保配置完整
        return None
        print("Warning: POLARION_TOKEN not configured")
        print("Set environment variable: export POLARION_TOKEN='your_token'")
        return None

    url = f"{POLARION_URL}/rest/v1{endpoint}"
    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"

    headers = {
        "Authorization": f"Bearer {POLARION_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    body = json.dumps(data).encode("utf-8") if data else None

    try:
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"HTTP Error {e.code}: {error_body}")
        return None
    except URLError as e:
        print(f"URL Error: {e.reason}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def list_projects():
    """Get list of all projects."""
    result = make_request("/projects")
    if result and "data" in result:
        projects = result["data"]
        print(f"\nFound {len(projects)} projects:\n")
        for p in projects:
            print(f"  - {p['id']}")
        
        output_file = "projects.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_file}")
        return projects
    return None


def get_project(project_id):
    """Get project details."""
    result = make_request(f"/projects/{project_id}")
    if result and "data" in result:
        data = result["data"]
        attrs = data.get("attributes", {})
        print(f"\nProject: {project_id}")
        print(f"  Name: {attrs.get('name', 'N/A')}")
        print(f"  Description: {attrs.get('description', 'N/A')}")
        print(f"  Location: {attrs.get('location', 'N/A')}")
        
        output_file = f"project_{project_id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_file}")
        return result
    return None


def query_workitems(project_id, query="", fields=None, limit=10):
    """Query work items in a project."""
    params = {"page[size]": limit}
    if query:
        params["query"] = query
    if fields:
        params["fields[workitems]"] = ",".join(fields)
    
    result = make_request(f"/projects/{project_id}/workitems", params=params)
    if result and "data" in result:
        items = result["data"]
        meta = result.get("meta", {})
        total = meta.get("totalCount", len(items))
        
        print(f"\nFound {total} work items (showing {len(items)}):\n")
        for item in items:
            attrs = item.get("attributes", {})
            print(f"  [{item.get('id', 'N/A')}] {attrs.get('title', 'N/A')}")
            print(f"      Type: {attrs.get('type', 'N/A')}, Status: {attrs.get('status', 'N/A')}")
        
        output_file = f"workitems_{project_id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_file}")
        return result
    return None


def get_workitem(project_id, workitem_id, fields=None):
    """Get single work item details.
    
    Args:
        project_id: Project ID
        workitem_id: Work item ID
        fields: List of fields to return (e.g., ['title', 'status', 'description'])
                If None, returns default fields (without description)
                To get description, must explicitly include it in fields
    """
    params = None
    if fields:
        params = {"fields[workitems]": ",".join(fields)}
    
    result = make_request(f"/projects/{project_id}/workitems/{workitem_id}", params=params)
    if result and "data" in result:
        data = result["data"]
        attrs = data.get("attributes", {})
        
        print(f"\nWork Item: {workitem_id}")
        print(f"  Title: {attrs.get('title', 'N/A')}")
        print(f"  Type: {attrs.get('type', 'N/A')}")
        print(f"  Status: {attrs.get('status', 'N/A')}")
        print(f"  Severity: {attrs.get('severity', 'N/A')}")
        print(f"  Created: {attrs.get('created', 'N/A')}")
        print(f"  Updated: {attrs.get('updated', 'N/A')}")
        
        if "description" in attrs:
            desc = attrs["description"]
            if isinstance(desc, dict):
                desc_value = desc.get('value', 'N/A')
                desc_type = desc.get('type', 'N/A')
                print(f"  Description ({desc_type}):")
                if len(desc_value) > 300:
                    print(f"    {desc_value[:300]}...")
                else:
                    print(f"    {desc_value}")
            else:
                print(f"  Description: {str(desc)[:200]}...")
        
        output_file = f"workitem_{project_id}_{workitem_id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_file}")
        return result
    return None


def create_workitem(project_id, item_type, title, description=None, **kwargs):
    """Create a new work item."""
    data = {
        "data": {
            "type": "workitems",
            "attributes": {
                "type": item_type,
                "title": title
            }
        }
    }
    
    if description:
        data["data"]["attributes"]["description"] = {
            "type": "text/html",
            "value": description
        }
    
    for key, value in kwargs.items():
        if value:
            data["data"]["attributes"][key] = value
    
    result = make_request(f"/projects/{project_id}/workitems", method="POST", data=data)
    if result and "data" in result:
        new_id = result["data"].get("id", "N/A")
        print(f"\nCreated work item: {new_id}")
        
        output_file = f"created_workitem_{new_id.replace('/', '_')}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Saved to {output_file}")
        return result
    return None


def list_documents(project_id, space_id=None):
    """List documents in a project."""
    if space_id:
        result = make_request(f"/projects/{project_id}/spaces/{space_id}/documents")
    else:
        result = make_request(f"/projects/{project_id}/spaces")
    
    if result and "data" in result:
        items = result["data"]
        print(f"\nFound {len(items)} items:\n")
        for item in items:
            print(f"  - [{item.get('type', 'N/A')}] {item.get('id', 'N/A')}")
        
        output_file = f"documents_{project_id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_file}")
        return result
    return None


def list_testruns(project_id, limit=20):
    """List test runs in a project."""
    params = {"page[size]": limit}
    result = make_request(f"/projects/{project_id}/testruns", params=params)
    
    if result and "data" in result:
        items = result["data"]
        print(f"\nFound {len(items)} test runs:\n")
        for item in items:
            attrs = item.get("attributes", {})
            print(f"  - [{item.get('id', 'N/A')}] {attrs.get('title', 'N/A')}")
            print(f"      Status: {attrs.get('status', 'N/A')}")
        
        output_file = f"testruns_{project_id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_file}")
        return result
    return None


def main():
    parser = argparse.ArgumentParser(description="Polarion REST API Client")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # list-projects
    subparsers.add_parser("list-projects", help="List all projects")
    
    # get-project
    p_project = subparsers.add_parser("get-project", help="Get project details")
    p_project.add_argument("project_id", help="Project ID")
    
    # query-workitems
    p_query = subparsers.add_parser("query-workitems", help="Query work items")
    p_query.add_argument("project_id", help="Project ID")
    p_query.add_argument("--query", "-q", default="", help="Query string")
    p_query.add_argument("--fields", "-f", help="Fields to return (comma-separated)")
    p_query.add_argument("--limit", "-l", type=int, default=10, help="Limit results")
    
    # get-workitem
    p_wi = subparsers.add_parser("get-workitem", help="Get work item details")
    p_wi.add_argument("project_id", help="Project ID")
    p_wi.add_argument("workitem_id", help="Work item ID")
    
    # create-workitem
    p_create = subparsers.add_parser("create-workitem", help="Create work item")
    p_create.add_argument("project_id", help="Project ID")
    p_create.add_argument("--type", "-t", required=True, help="Item type (requirement/defect/task)")
    p_create.add_argument("--title", required=True, help="Title")
    p_create.add_argument("--description", "-d", help="Description")
    p_create.add_argument("--severity", "-s", help="Severity")
    p_create.add_argument("--assignee", "-a", help="Assignee")
    
    # list-documents
    p_docs = subparsers.add_parser("list-documents", help="List documents")
    p_docs.add_argument("project_id", help="Project ID")
    p_docs.add_argument("--space", help="Space ID")
    
    # list-testruns
    p_tests = subparsers.add_parser("list-testruns", help="List test runs")
    p_tests.add_argument("project_id", help="Project ID")
    p_tests.add_argument("--limit", "-l", type=int, default=20, help="Limit results")
    
    args = parser.parse_args()
    
    if args.command == "list-projects":
        list_projects()
    elif args.command == "get-project":
        get_project(args.project_id)
    elif args.command == "query-workitems":
        fields = args.fields.split(",") if args.fields else None
        query_workitems(args.project_id, args.query, fields, args.limit)
    elif args.command == "get-workitem":
        get_workitem(args.project_id, args.workitem_id)
    elif args.command == "create-workitem":
        create_workitem(
            args.project_id, args.type, args.title,
            description=args.description,
            severity=args.severity,
            assignee=args.assignee
        )
    elif args.command == "list-documents":
        list_documents(args.project_id, args.space)
    elif args.command == "list-testruns":
        list_testruns(args.project_id, args.limit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
