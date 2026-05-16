#!/usr/bin/env python3
import os
import sys

# Set env
os.environ["POLARION_URL"] = "https://polarion.intranet.vwg-cea.cn/polarion"
os.environ["POLARION_TOKEN"] = "eyJraWQiOiI4ZDBjNzBmZC1hYzFhYzJiMC0zZmQ4ZTExYy04MzBhZGVkYSIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJXUDZLQ0YyIiwiaWQiOiJhZjZkYjhlZC1hYzFhYzJiMC00MGQ0NmM0MC01ODc3MzVhNCIsImV4cCI6MTc4MzYxMjgwMCwiaWF0IjoxNzc2NzY0Njk2fQ.NvE8anDAlmeyjyulv1wiyISRCZkbTl9YJxzETMfYYnJdrlesp9VXZGTVVIbAusC9aI8nngBevYsJRiRsklfY61pQrAOe6TkT0Uno2Qm6XSB5Sf7X3XgGBz34TI6UjHwy5BtFLuduRC7drQ_fKRERnUbgS8Lulau7HsfWVCbSQyn9vyLj_zIvzkfnmQlvriUCfppTOTnzahZYxjYGXwrYG11DUHTTjywKa5J6wQHSWe0at_dHIY1lYiu-khndDyBwin9z30HamBNa031fqtd_ebh6Exu-BsvcWK1AfPV8wCS1C7XiafdfHUgJG7xhZ2jSLgqWKfU6KtU8uQj5fTN16g"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polarion_api import make_request
import json

print("Testing API...")
result = make_request('/projects/VEEA/workitems', params={
    'query': 'module:VEEA/2-FRS_VC/Gong Neng Shi Xian Fang An Shu _Shu Zi Yao Chi',
    'page[size]': 5,
    'page[number]': 1,
    'fields[workitems]': 'id,title,type'
})

if result:
    print(f"Success! Got {len(result.get('data', []))} items")
    for item in result['data'][:3]:
        attrs = item.get('attributes', {})
        print(f"  - {item['id']}: {attrs.get('title', 'N/A')} ({attrs.get('type', 'N/A')})")
    print(f"Total in document: {result.get('meta', {}).get('totalCount', 'unknown')}")
else:
    print("Failed!")
