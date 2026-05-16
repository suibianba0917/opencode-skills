#!/usr/bin/env python3
"""Export all workitems from a Polarion document/module."""

import sys
import os
import json
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

# Set default config
POLARION_URL = "https://polarion.intranet.vwg-cea.cn/polarion"
POLARION_TOKEN = "eyJraWQiOiI4ZDBjNzBmZC1hYzFhYzJiMC0zZmQ4ZTExYy04MzBhZGVkYSIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJXUDZLQ0YyIiwiaWQiOiJhZjZkYjhlZC1hYzFhYzJiMC00MGQ0NmM0MC01ODc3MzVhNCIsImV4cCI6MTc4MzYxMjgwMCwiaWF0IjoxNzc2NzY0Njk2fQ.NvE8anDAlmeyjyulv1wiyISRCZkbTl9YJxzETMfYYnJdrlesp9VXZGTVVIbAusC9aI8nngBevYsJRiRsklfY61pQrAOe6TkT0Uno2Qm6XSB5Sf7X3XgGBz34TI6UjHwy5BtFLuduRC7drQ_fKRERnUbgS8Lulau7HsfWVCbSQyn9vyLj_zIvzkfnmQlvriUCfppTOTnzahZYxjYGXwrYG11DUHTTjywKa5J6wQHSWe0at_dHIY1lYiu-khndDyBwin9z30HamBNa031fqtd_ebh6Exu-BsvcWK1AfPV8wCS1C7XiafdfHUgJG7xhZ2jSLgqWKfU6KtU8uQj5fTN16g"


def make_request(endpoint, method="GET", data=None, params=None):
    """Make HTTP request to Polarion API."""
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


def export_document(project_id, module_path, output_file=None, page_size=100):
    """Export all workitems from a document module.

    Args:
        project_id: Project ID (e.g., VEEA)
        module_path: Document module path (e.g., VEEA/2-FRS_VC/文档名)
        output_file: Output JSON file path
        page_size: Number of items per page (max 100)
    """
    if not POLARION_URL or not POLARION_TOKEN:
        print("Error: POLARION_URL and POLARION_TOKEN must be set")
        return None

    if output_file is None:
        output_file = f"document_{project_id}_{module_path.split('/')[-1]}.json"

    query = f"module:{module_path}"
    all_items = []
    page = 1

    print(f"Exporting document: {module_path}")
    print(f"Project: {project_id}")
    print(f"Page size: {page_size}")
    print("-" * 50)

    while True:
        params = {
            "query": query,
            "page[size]": page_size,
            "page[number]": page,
            "fields[workitems]": "id,title,type,description,status"
        }

        result = make_request(f"/projects/{project_id}/workitems", params=params)

        if result is None:
            print(f"Error fetching page {page}")
            break

        items = result.get("data", [])
        meta = result.get("meta", {})
        total = meta.get("totalCount", 0)

        if not items:
            break

        all_items.extend(items)
        print(f"Page {page}: fetched {len(items)} items (total: {len(all_items)}/{total})")

        if len(all_items) >= total:
            break

        page += 1

    print("-" * 50)
    print(f"Total items: {len(all_items)}")

    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "project": project_id,
            "module": module_path,
            "total_count": len(all_items),
            "items": all_items
        }, f, indent=2, ensure_ascii=False)

    print(f"Saved to: {output_file}")
    return all_items


def main():
    parser = argparse.ArgumentParser(description="Export Polarion document")
    parser.add_argument("--project", "-p", required=True, help="Project ID")
    parser.add_argument("--module", "-m", required=True, help="Document module path")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--size", "-s", type=int, default=100, help="Page size (max 100)")

    args = parser.parse_args()
    export_document(args.project, args.module, args.output, args.size)


if __name__ == "__main__":
    main()
