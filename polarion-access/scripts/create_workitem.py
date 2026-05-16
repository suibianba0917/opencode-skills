#!/usr/bin/env python3
"""Create a new work item in Polarion."""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polarion_api import create_workitem

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Polarion work item")
    parser.add_argument("--project", "-p", required=True, help="Project ID")
    parser.add_argument("--type", "-t", required=True, help="Item type (requirement/defect/task)")
    parser.add_argument("--title", required=True, help="Title")
    parser.add_argument("--description", "-d", help="Description")
    parser.add_argument("--severity", "-s", help="Severity")
    parser.add_argument("--assignee", "-a", help="Assignee")
    
    args = parser.parse_args()
    create_workitem(
        args.project, args.type, args.title,
        description=args.description,
        severity=args.severity,
        assignee=args.assignee
    )
