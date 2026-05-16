#!/usr/bin/env python3
"""Get a single work item details."""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polarion_api import get_workitem

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get Polarion work item")
    parser.add_argument("--project", "-p", required=True, help="Project ID")
    parser.add_argument("--id", "-i", required=True, dest="workitem_id", help="Work item ID")
    parser.add_argument("--fields", "-f", help="Fields to return (comma-separated). Include 'description' to get full content")
    
    args = parser.parse_args()
    
    fields = args.fields.split(",") if args.fields else None
    get_workitem(args.project, args.workitem_id, fields=fields)
