#!/usr/bin/env python3
"""List documents in a Polarion project."""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polarion_api import list_documents

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List Polarion documents")
    parser.add_argument("--project", "-p", required=True, help="Project ID")
    parser.add_argument("--space", "-s", help="Space ID")
    
    args = parser.parse_args()
    list_documents(args.project, args.space)
