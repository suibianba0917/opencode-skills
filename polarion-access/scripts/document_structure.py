#!/usr/bin/env python3
"""Extract document structure with chapters, intros, functions and cases."""

import sys
import os
import json
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

POLARION_URL = "https://polarion.intranet.vwg-cea.cn/polarion"
POLARION_TOKEN = "eyJraWQiOiI4ZDBjNzBmZC1hYzFhYzJiMC0zZmQ4ZTExYy04MzBhZGVkYSIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJXUDZLQ0YyIiwiaWQiOiJhZjZkYjhlZC1hYzFhYzJiMC00MGQ0NmM0MC01ODc3MzVhNCIsImV4cCI6MTc4MzYxMjgwMCwiaWF0IjoxNzc2NzY0Njk2fQ.NvE8anDAlmeyjyulv1wiyISRCZkbTl9YJxzETMfYYnJdrlesp9VXZGTVVIbAusC9aI8nngBevYsJRiRsklfY61pQrAOe6TkT0Uno2Qm6XSB5Sf7X3XgGBz34TI6UjHwy5BtFLuduRC7drQ_fKRERnUbgS8Lulau7HsfWVCbSQyn9vyLj_zIvzkfnmQlvriUCfppTOTnzahZYxjYGXwrYG11DUHTTjywKa5J6wQHSWe0at_dHIY1lYiu-khndDyBwin9z30HamBNa031fqtd_ebh6Exu-BsvcWK1AfPV8wCS1C7XiafdfHUgJG7xhZ2jSLgqWKfU6KtU8uQj5fTN16g"


def make_request(endpoint, method="GET", data=None, params=None):
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
        print(f"HTTP Error {e.code}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def extract_document_structure(project_id, module_path, max_pages=300):
    """Extract document structure."""
    query = f"module:{module_path}"
    all_items = []
    page = 1

    print(f"Fetching document: {module_path}")
    print(f"Project: {project_id}")

    while page <= max_pages:
        params = {
            "query": query,
            "page[size]": 100,
            "page[number]": page,
            "fields[workitems]": "id,title,type,description"
        }
        result = make_request(f"/projects/{project_id}/workitems", params=params)
        if result is None or not result.get("data"):
            break
        items = result.get("data", [])
        all_items.extend(items)
        meta = result.get("meta", {})
        total = meta.get("totalCount", 0)
        print(f"Page {page}: {len(items)} items (total: {len(all_items)}/{total})")
        if len(all_items) >= total:
            break
        page += 1

    # Group items by chapter
    chapters = []
    current_chapter = None

    for item in all_items:
        attrs = item.get("attributes", {})
        item_type = attrs.get("type", "")
        item_id = attrs.get("id", "")
        title = attrs.get("title", "")
        desc = attrs.get("description", {})

        # Get plain description
        desc_text = ""
        if isinstance(desc, dict):
            desc_text = desc.get("value", "")
            # Strip HTML tags for display
            import re
            desc_text = re.sub(r'<[^>]+>', ' ', desc_text)
            desc_text = re.sub(r'\s+', ' ', desc_text).strip()

        if item_type == "heading":
            if current_chapter:
                chapters.append(current_chapter)
            current_chapter = {
                "id": item_id,
                "title": title,
                "description": desc_text,
                "functions": [],
                "usecases": [],
                "others": []
            }
        elif current_chapter:
            if "functionRequirement" in item_id.lower() or item_type == "functionRequirement":
                current_chapter["functions"].append({"id": item_id, "title": title, "desc": desc_text[:200]})
            elif "userCase" in item_id.lower() or "uc-" in item_id.lower() or item_type == "userCase":
                current_chapter["usecases"].append({"id": item_id, "title": title, "desc": desc_text[:200]})
            else:
                if title:
                    current_chapter["others"].append({"id": item_id, "type": item_type, "title": title, "desc": desc_text[:200]})

    if current_chapter:
        chapters.append(current_chapter)

    return chapters


def print_structure(chapters):
    """Print document structure."""
    print("\n" + "=" * 100)
    print("DOCUMENT STRUCTURE")
    print("=" * 100)

    for i, chapter in enumerate(chapters, 1):
        print(f"\n{'='*80}")
        print(f"CHAPTER {i}: [{chapter['id']}] {chapter['title']}")
        print(f"{'='*80}")

        if chapter["description"]:
            desc = chapter["description"][:500]
            if len(chapter["description"]) > 500:
                desc += "..."
            print(f"\n【介绍】: {desc}")

        if chapter["functions"]:
            print(f"\n【功能需求】 ({len(chapter['functions'])} items):")
            for func in chapter["functions"][:20]:
                print(f"  • [{func['id']}] {func['title']}")
            if len(chapter["functions"]) > 20:
                print(f"  ... and {len(chapter['functions']) - 20} more")

        if chapter["usecases"]:
            print(f"\n【用户场景】 ({len(chapter['usecases'])} items):")
            for uc in chapter["usecases"][:20]:
                print(f"  • [{uc['id']}] {uc['title']}")
            if len(chapter["usecases"]) > 20:
                print(f"  ... and {len(chapter['usecases']) - 20} more")

        if chapter["others"]:
            print(f"\n【其他内容】 ({len(chapter['others'])} items):")
            for other in chapter["others"][:10]:
                print(f"  • [{other['id']}] ({other['type']}) {other['title']}")
            if len(chapter["others"]) > 10:
                print(f"  ... and {len(chapter['others']) - 10} more")


def save_to_file(chapters, output_file):
    """Save structure to JSON file."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chapters, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Extract document structure")
    parser.add_argument("--project", "-p", default="VEEA", help="Project ID")
    parser.add_argument("--module", "-m", default="VEEA/2-FRS_VC/Gong Neng Shi Xian Fang An Shu _Shu Zi Yao Chi", help="Module path")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--max-pages", type=int, default=300, help="Max pages to fetch")
    args = parser.parse_args()

    chapters = extract_document_structure(args.project, args.module, args.max_pages)

    print_structure(chapters)

    if args.output:
        save_to_file(chapters, args.output)


if __name__ == "__main__":
    main()
