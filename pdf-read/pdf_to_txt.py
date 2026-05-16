#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转文本脚本 - 将PDF内容保存为文本文件
优先使用PyMuPDF，回退到pypdf
"""
import sys
import os

def pdf_to_txt_pymupdf(pdf_path, output_path=None):
    import fitz

    if output_path is None:
        output_path = os.path.splitext(pdf_path)[0] + '.txt'

    doc = fitz.open(pdf_path)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"PDF: {pdf_path}\n")
        f.write(f"Pages: {len(doc)}\n")
        f.write("=" * 50 + "\n\n")

        for page in doc:
            text = page.get_text()
            f.write(f"\n=== Page {page.number + 1} ===\n")
            f.write(text if text else "[No text]\n")

    doc.close()
    print(f"Saved to: {output_path}")
    return True

def pdf_to_txt_pypdf(pdf_path, output_path=None):
    from pypdf import PdfReader

    if output_path is None:
        output_path = os.path.splitext(pdf_path)[0] + '.txt'

    reader = PdfReader(pdf_path)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"PDF: {pdf_path}\n")
        f.write(f"Pages: {len(reader.pages)}\n")
        f.write("=" * 50 + "\n\n")

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            f.write(f"\n=== Page {i+1} ===\n")
            f.write(text if text else "[No text]\n")

    print(f"Saved to: {output_path}")
    return True

def pdf_to_txt(pdf_path, output_path=None):
    try:
        import fitz
        return pdf_to_txt_pymupdf(pdf_path, output_path)
    except ImportError:
        print("PyMuPDF not found, falling back to pypdf...")
        return pdf_to_txt_pypdf(pdf_path, output_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_txt.py <PDF> [output_txt]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    pdf_to_txt(pdf_path, output_path)
