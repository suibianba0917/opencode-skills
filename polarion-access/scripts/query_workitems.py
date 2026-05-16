#!/usr/bin/env python3
"""Query work items in a Polarion project."""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polarion_api import query_workitems

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query Polarion work items")
    parser.add_argument("--project", "-p", required=True, help="Project ID")
    parser.add_argument("--query", "-q", default="", help="Query string")
    parser.add_argument("--fields", "-f", help="Fields to return (comma-separated)")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Limit results")
    
    args = parser.parse_args()
    fields = args.fields.split(",") if args.fields else None
    query_workitems(args.project, args.query, fields, args.limit)
