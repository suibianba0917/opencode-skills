#!/usr/bin/env python3
import json
import sys

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

with open("VEEA_digital_key.json", "r", encoding="utf-8") as f:
    data = json.load(f)

items = data["items"]
print(f"Total items: {data['total_count']}")
print("=" * 80)

headings = [item for item in items if item.get("attributes", {}).get("type") == "heading"]
func_reqs = [item for item in items if item.get("attributes", {}).get("type") == "functionRequirement"]
user_cases = [item for item in items if item.get("attributes", {}).get("type") == "userCase"]

print(f"\nHeadings: {len(headings)}")
print(f"Function Requirements: {len(func_reqs)}")
print(f"User Cases: {len(user_cases)}")

print("\n" + "=" * 80)
print("HEADINGS (Document Structure):")
print("=" * 80)
for item in headings:
    attrs = item.get("attributes", {})
    print(f"  [{attrs.get('id', 'N/A')}] {attrs.get('title', 'N/A')}")

print("\n" + "=" * 80)
print("USER CASES:")
print("=" * 80)
for item in user_cases[:20]:
    attrs = item.get("attributes", {})
    title = attrs.get('title', 'N/A')
    if len(title) > 60:
        title = title[:60] + "..."
    print(f"  [{attrs.get('id', 'N/A')}] {title}")

if len(user_cases) > 20:
    print(f"  ... and {len(user_cases) - 20} more")

print("\n" + "=" * 80)
print("FUNCTION REQUIREMENTS (first 30):")
print("=" * 80)
for item in func_reqs[:30]:
    attrs = item.get("attributes", {})
    title = attrs.get('title', 'N/A')
    if len(title) > 50:
        title = title[:50] + "..."
    print(f"  [{attrs.get('id', 'N/A')}] {title}")

if len(func_reqs) > 30:
    print(f"  ... and {len(func_reqs) - 30} more")
