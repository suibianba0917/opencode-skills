#!/usr/bin/env python3
"""Get items by searching keywords in each chapter."""

import json
import re
from urllib.request import Request, urlopen
from urllib.parse import urlencode

POLARION_TOKEN = "eyJraWQiOiI4ZDBjNzBmZC1hYzFhYzJiMC0zZmQ4ZTExYy04MzBhZGVkYSIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJXUDZLQ0YyIiwiaWQiOiJhZjZkYjhlZC1hYzFhYzJiMC00MGQ0NmM0MC01ODc3MzVhNCIsImV4cCI6MTc4MzYxMjgwMCwiaWF0IjoxNzc2NzY0Njk2fQ.NvE8anDAlmeyjyulv1wiyISRCZkbTl9YJxzETMfYYnJdrlesp9VXZGTVVIbAusC9aI8nngBevYsJRiRsklfY61pQrAOe6TkT0Uno2Qm6XSB5Sf7X3XgGBz34TI6UjHwy5BtFLuduRC7drQ_fKRERnUbgS8Lulau7HsfWVCbSQyn9vyLj_zIvzkfnmQlvriUCfppTOTnzahZYxjYGXwrYG11DUHTTjywKa5J6wQHSWe0at_dHIY1lYiu-khndDyBwin9z30HamBNa031fqtd_ebh6Exu-BsvcWK1AfPV8wCS1C7XiafdfHUgJG7xhZ2jSLgqWKfU6KtU8uQj5fTN16g"

def make_request(url):
    headers = {"Authorization": f"Bearer {POLARION_TOKEN}", "Accept": "application/json"}
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def strip_html(text):
    if not text: return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

chapters = [
    ("VEEA-12210", "功能定义", "type:requirement"),
    ("VEEA-12211", "功能实现方案", "type:requirement"),
    ("VEEA-12231", "To 蓝牙数字钥匙子系统BLE", "BLE"),
    ("VEEA-12237", "To 蓝牙数字钥匙子系统TBOX", "TBOX"),
    ("CEA-104505", "To 手机APP SDK", "APP SDK"),
    ("CEA-104591", "功能实现方案书_数字钥匙", "数字钥匙"),
    ("CEA-111519", "To 大屏", "大屏"),
    ("CEA-106560", "To TBOX", "TBOX"),
    ("CEA-114675", "功能定义规范_数字钥匙", "数字钥匙"),
]

for chapter_id, chapter_title, keyword in chapters:
    print(f"\n{'='*80}")
    print(f"【{chapter_id}】{chapter_title}")
    print(f"{'='*80}")

    url = f"https://polarion.intranet.vwg-cea.cn/polarion/rest/v1/projects/VEEA/workitems?query={keyword}&page[size]=20"
    result = make_request(url)

    if result and result.get("data"):
        items = result["data"]
        print(f"  找到 {len(items)} 个相关项目:\n")
        for item in items[:15]:
            attrs = item.get("attributes", {})
            item_id = attrs.get("id", "")
            title = attrs.get("title", "")
            item_type = attrs.get("type", "")
            print(f"  • [{item_id}] {title}")
            print(f"    类型: {item_type}")
    else:
        print("  (无相关项目)")
