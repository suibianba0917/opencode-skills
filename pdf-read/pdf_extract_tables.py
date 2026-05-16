#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF表格提取脚本 - 使用PyMuPDF
"""
import sys
import os

def extract_tables_pymupdf(pdf_path, page_nums=None):
    import fitz

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    if page_nums is None:
        page_nums = list(range(total_pages))

    results = []

    for i in page_nums:
        if i >= total_pages:
            continue
        page = doc[i]
        tables = page.find_tables()

        print(f"\n--- Page {i+1} ---")

        if not tables:
            print("  No tables found")
            continue

        for table_idx, table in enumerate(tables):
            data = table.extract()
            if not data:
                continue

            print(f"\n  Table {table_idx + 1}:")

            for row_idx, row in enumerate(data[:10]):
                print(f"    Row {row_idx}: {row}")

            if len(data) > 10:
                print(f"    ... ({len(data) - 10} more rows)")

            results.append({
                'page': i + 1,
                'table_idx': table_idx + 1,
                'data': data
            })

    doc.close()
    return results

def extract_tables(pdf_path, start_page=0, end_page=None):
    try:
        import fitz
    except ImportError:
        print("Error: PyMuPDF not installed. Run: pip install pymupdf")
        return []

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    if end_page is None or end_page > total_pages:
        end_page = total_pages

    page_nums = list(range(start_page, end_page))

    print(f"Extracting tables from pages {start_page+1} to {end_page}")
    print(f"File: {pdf_path}")

    return extract_tables_pymupdf(pdf_path, page_nums)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_extract_tables.py <PDF> [start_page] [end_page]")
        print("Example:")
        print("  python pdf_extract_tables.py document.pdf       # All pages")
        print("  python pdf_extract_tables.py document.pdf 0 3   # Pages 1-3")
        sys.exit(1)

    pdf_path = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    end = int(sys.argv[3]) if len(sys.argv) > 3 else None

    extract_tables(pdf_path, start, end)
