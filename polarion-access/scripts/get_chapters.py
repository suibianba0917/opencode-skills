#!/usr/bin/env python3
"""Get detailed content for specific chapters."""

import sys
import os
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
import re

POLARION_URL = "https://polarion.intranet.vwg-cea.cn/polarion"
POLARION_TOKEN = "eyJraWQiOiI4ZDBjNzBmZC1hYzFhYzJiMC0zZmQ4ZTExYy04MzBhZGVkYSIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJXUDZLQ0YyIiwiaWQiOiJhZjZkYjhlZC1hYzFhYzJiMC00MGQ0NmM0MC01ODc3MzVhNCIsImV4cCI6MTc4MzYxMjgwMCwiaWF0IjoxNzc2NzY0Njk2fQ.NvE8anDAlmeyjyulv1wiyISRCZkbTl9YJxzETMfYYnJdrlesp9VXZGTVVIbAusC9aI8nngBevYsJRiRsklfY61pQrAOe6TkT0Uno2Qm6XSB5Sf7X3XgGBz34TI6UjHwy5BtFLuduRC7drQ_fKRERnUbgS8Lulau7HsfWVCbSQyn9vyLj_zIvzkfnmQlvriUCfppTOTnzahZYxjYGXwrYG11DUHTTjywKa5J6wQHSWe0at_dHIY1lYiu-khndDyBwin9z30HamBNa031fqtd_ebh6Exu-BsvcWK1AfPV8wCS1C7XiafdfHUgJG7xhZ2jSLgqWKfU6KtU8uQj5fTN16g"


def make_request(endpoint, params=None):
    url = f"{POLARION_URL}/rest/v1{endpoint}"
    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"
    headers = {"Authorization": f"Bearer {POLARION_TOKEN}", "Accept": "application/json"}
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Error: {e}")
        return None


def get_workitem_with_desc(workitem_id):
    """Get workitem with full description."""
    result = make_request(f"/projects/VEEA/workitems/{workitem_id}", {
        "fields[workitems]": "id,title,type,description,status"
    })
    if result:
        return result.get("data", {}).get("attributes", {})
    return None


def strip_html(text):
    """Remove HTML tags."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_chapter_items(chapter_heading_id, module_path, max_items=50):
    """Get items under a specific chapter heading."""
    # Get all items in document and find items after this heading
    query = f"module:{module_path}"
    all_items = []
    page = 1

    while page <= 3:  # Just get first few pages
        result = make_request(f"/projects/VEEA/workitems", {
            "query": query,
            "page[size]": 100,
            "page[number]": page,
            "fields[workitems]": "id,title,type"
        })
        if not result or not result.get("data"):
            break
        all_items.extend(result.get("data", []))
        if len(all_items) >= result.get("meta", {}).get("totalCount", 0):
            break
        page += 1

    # Find the index of the chapter heading
    chapter_index = -1
    for i, item in enumerate(all_items):
        item_id = item.get("id", "").split("/")[-1]
        if item_id == chapter_heading_id:
            chapter_index = i
            break

    if chapter_index == -1:
        return []

    # Get items after this heading (until next heading)
    chapter_items = []
    for item in all_items[chapter_index+1:]:
        item_id = item.get("id", "").split("/")[-1]
        item_type = item.get("type", "")
        # Stop if we hit another heading
        if item_type == "workitems":
            attrs = item.get("attributes", {})
            if attrs.get("type") == "heading":
                break
            chapter_items.append({
                "id": item_id,
                "title": attrs.get("title", ""),
                "type": attrs.get("type", "")
            })
            if len(chapter_items) >= max_items:
                break

    return chapter_items


def get_chapter_details(chapter_id, module_path):
    """Get full details for items in a chapter."""
    items = get_chapter_items(chapter_id, module_path)
    results = []

    for item in items[:30]:  # Limit to 30 items for performance
        details = get_workitem_with_desc(item["id"])
        if details:
            desc = details.get("description", {})
            desc_text = strip_html(desc.get("value", "")) if isinstance(desc, dict) else ""
            results.append({
                "id": details.get("id"),
                "title": details.get("title"),
                "type": details.get("type"),
                "status": details.get("status"),
                "description": desc_text[:500] if desc_text else "(无描述)"
            })

    return results


def main():
    chapters = [
        ("VEEA-12210", "功能定义"),
        ("VEEA-12211", "功能实现方案"),
        ("VEEA-12231", "To 蓝牙数字钥匙子系统BLE"),
        ("VEEA-12237", "To 蓝牙数字钥匙子系统TBOX"),
        ("CEA-104505", "To 手机APP SDK"),
        ("CEA-104591", "功能实现方案书_数字钥匙"),
        ("CEA-111519", "To 大屏"),
        ("CEA-106560", "To TBOX"),
        ("CEA-114675", "功能定义规范_数字钥匙"),
    ]

    module_path = "VEEA/2-FRS_VC/Gong Neng Shi Xian Fang An Shu _Shu Zi Yao Chi"

    for chapter_id, chapter_title in chapters:
        print(f"\n{'='*80}")
        print(f"【{chapter_id}】{chapter_title}")
        print(f"{'='*80}")

        details = get_chapter_details(chapter_id, module_path)

        if not details:
            print("  (无子项目)")
        else:
            print(f"  共 {len(details)} 个项目:\n")
            for i, item in enumerate(details, 1):
                print(f"  {i}. [{item['id']}] {item['title']}")
                print(f"     类型: {item['type']} | 状态: {item['status']}")
                if item['description'] and item['description'] != "(无描述)":
                    desc = item['description'][:200] + "..." if len(item['description']) > 200 else item['description']
                    print(f"     描述: {desc}")
                print()


if __name__ == "__main__":
    main()
