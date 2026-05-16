#!/usr/bin/env python3
"""List all Polarion projects."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polarion_api import list_projects

if __name__ == "__main__":
    list_projects()
