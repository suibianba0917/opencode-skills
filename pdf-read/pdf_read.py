#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF读取脚本 - 提取PDF文本内容(可选图片提取)
默认使用PyMuPDF，回退到pypdf
"""
import sys
import os
import re

def clean_text(text):
    if not text:
        return text

    text = text.replace('\u200b', '')
    text = text.replace('\u200c', '')
    text = text.replace('\u200d', '')
    text = text.replace('\ufeff', '')
    text = text.replace('\xa0', ' ')
    text = text.replace('\u3000', '    ')

    replacements = {
        'DK2.0': 'DK 2.0',
    }

    for old, new in replacements.items():
        if isinstance(old, str) and len(old) > 1:
            text = text.replace(old, new)

    import unicodedata
    result = []
    for char in text:
        code = ord(char)
        if 0xf900 <= code <= 0xfaff:
            normalized = unicodedata.normalize('NFKC', char)
            if normalized.strip():
                result.append(normalized)
            else:
                result.append(char)
        else:
            result.append(char)
    text = ''.join(result)

    text = re.sub(r'([a-z])(\d)', r'\1 \2', text)
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

    text = re.sub(r'\n\s*\n', '\n', text)

    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            if len(line) > 1:
                line = ' '.join(line.split())
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)

def extract_images(pdf_path, start_page=0, end_page=None):
    try:
        import fitz
    except ImportError:
        print("提示: 需要安装 pymupdf 来提取图片: pip install pymupdf")
        return []

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    if end_page is None or end_page > total_pages:
        end_page = total_pages

    pdf_dir = os.path.dirname(pdf_path)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    img_dir = os.path.join(pdf_dir, f"{pdf_name}_images")
    os.makedirs(img_dir, exist_ok=True)

    extracted = []

    for page_num in range(start_page, end_page):
        page = doc[page_num]
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            image_filename = f"page{page_num+1}_img{img_index+1}.{image_ext}"
            image_path = os.path.join(img_dir, image_filename)

            with open(image_path, "wb") as f:
                f.write(image_bytes)

            extracted.append(image_path)

    doc.close()

    if extracted:
        print(f"Extracted {len(extracted)} images to: {img_dir}")
    else:
        print("No images found")

    return extracted

def read_pdf_pymupdf(pdf_path, start_page=0, end_page=None, extract_images_flag=False):
    import fitz

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    if end_page is None or end_page > total_pages:
        end_page = total_pages

    print(f"=== PDF Info ===")
    print(f"File: {pdf_path}")
    print(f"Pages: {total_pages}")
    print(f"Reading: {start_page+1} - {end_page}")
    print("=" * 50)

    extracted_images = []
    if extract_images_flag:
        extracted_images = extract_images(pdf_path, start_page, end_page)
        if extracted_images:
            print("--- Extracted Images ---")
            for img in extracted_images:
                print(f"  {img}")
            print("=" * 50)

    for i in range(start_page, end_page):
        page = doc[i]
        text = page.get_text()
        text = clean_text(text)

        page_imgs = [img for img in extracted_images if f"page{i+1}_" in os.path.basename(img)]

        print(f"\n--- Page {i+1} ---")

        if page_imgs:
            for img_path in page_imgs:
                img_name = os.path.basename(img_path)
                print(f"\n[Image: {img_name}]")
                print(f"  Path: {img_path}\n")

        print(text if text else "[No text]")

    doc.close()
    return True

def read_pdf_pypdf(pdf_path, start_page=0, end_page=None, extract_images_flag=False):
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    if end_page is None or end_page > total_pages:
        end_page = total_pages

    print(f"=== PDF Info ===")
    print(f"File: {pdf_path}")
    print(f"Pages: {total_pages}")
    print(f"Reading: {start_page+1} - {end_page}")
    print("=" * 50)

    extracted_images = []
    if extract_images_flag:
        extracted_images = extract_images(pdf_path, start_page, end_page)
        if extracted_images:
            print("--- Extracted Images ---")
            for img in extracted_images:
                print(f"  {img}")
            print("=" * 50)

    for i in range(start_page, end_page):
        page = reader.pages[i]
        text = page.extract_text()
        text = clean_text(text)

        page_imgs = [img for img in extracted_images if f"page{i+1}_" in os.path.basename(img)]

        print(f"\n--- Page {i+1} ---")

        if page_imgs:
            for img_path in page_imgs:
                img_name = os.path.basename(img_path)
                print(f"\n[Image: {img_name}]")
                print(f"  Path: {img_path}\n")

        print(text if text else "[No text]")

    return True

def read_pdf(pdf_path, start_page=0, end_page=None, extract_images_flag=False):
    try:
        import fitz
        return read_pdf_pymupdf(pdf_path, start_page, end_page, extract_images_flag)
    except ImportError:
        print("PyMuPDF not found, falling back to pypdf...")
        return read_pdf_pypdf(pdf_path, start_page, end_page, extract_images_flag)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_read.py <PDF> [start_page] [end_page] [--no-images]")
        print("Examples:")
        print("  python pdf_read.py document.pdf                    # Read all, no images")
        print("  python pdf_read.py document.pdf 0 3                # Read first 3 pages")
        print("  python pdf_read.py document.pdf 0 3 --no-images    # No image extraction")
        sys.exit(1)

    pdf_path = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 0
    end = int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
    no_images = '--no-images' in sys.argv

    read_pdf(pdf_path, start, end, extract_images_flag=not no_images)
