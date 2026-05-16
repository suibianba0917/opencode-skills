#!/usr/bin/env python3
"""List test runs in a Polarion project."""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polarion_api import list_testruns

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List Polarion test runs")
    parser.add_argument("--project", "-p", required=True, help="Project ID")
    parser.add_argument("--limit", "-l", type=int, default=20, help="Limit results")
    
    args = parser.parse_args()
    list_testruns(args.project, args.limit)
