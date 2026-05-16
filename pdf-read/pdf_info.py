#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF信息脚本 - 获取PDF元信息和页面统计
优先使用PyMuPDF，回退到pypdf
"""
import sys
import os

def get_pdf_info_pymupdf(pdf_path):
    import fitz

    doc = fitz.open(pdf_path)

    print(f"=== PDF Info ===")
    print(f"Path: {pdf_path}")
    print(f"Pages: {len(doc)}")

    meta = doc.metadata
    if meta:
        print("\n--- Metadata ---")
        print(f"Title: {meta.get('title', 'N/A')}")
        print(f"Author: {meta.get('author', 'N/A')}")
        print(f"Subject: {meta.get('subject', 'N/A')}")
        print(f"Creator: {meta.get('creator', 'N/A')}")
        print(f"Producer: {meta.get('producer', 'N/A')}")
        print(f"CreationDate: {meta.get('creationDate', 'N/A')}")

    print("\n--- Page Sizes (first 3) ---")
    for i, page in enumerate(doc[:3]):
        rect = page.rect
        print(f"Page {i+1}: {rect.width} x {rect.height}")

    doc.close()
    return True

def get_pdf_info_pypdf(pdf_path):
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)

    print(f"=== PDF Info ===")
    print(f"Path: {pdf_path}")
    print(f"Pages: {len(reader.pages)}")

    if reader.metadata:
        meta = reader.metadata
        print("\n--- Metadata ---")
        print(f"Title: {meta.get('/Title', 'N/A')}")
        print(f"Author: {meta.get('/Author', 'N/A')}")
        print(f"Subject: {meta.get('/Subject', 'N/A')}")
        print(f"Creator: {meta.get('/Creator', 'N/A')}")
        print(f"Producer: {meta.get('/Producer', 'N/A')}")
        print(f"CreationDate: {meta.get('/CreationDate', 'N/A')}")

    print("\n--- Page Sizes (first 3) ---")
    for i, page in enumerate(reader.pages[:3]):
        rect = page.mediabox
        print(f"Page {i+1}: {rect.width} x {rect.height}")

    return True

def get_pdf_info(pdf_path):
    try:
        import fitz
        return get_pdf_info_pymupdf(pdf_path)
    except ImportError:
        print("PyMuPDF not found, falling back to pypdf...")
        return get_pdf_info_pypdf(pdf_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_info.py <PDF>")
        sys.exit(1)

    get_pdf_info(sys.argv[1])
