#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import argparse
from pathlib import Path

def ocr_pdf(pdf_path, output_dir=None, dpi=200, tesseract_cmd=None):
    try:
        import fitz
    except ImportError:
        print("PyMuPDF未安装，请运行: pip install pymupdf")
        return False

    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        print("Pillow或pytesseract未安装，请运行: pip install Pillow pytesseract")
        return False

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    doc = fitz.open(pdf_path)

    if output_dir is None:
        output_dir = Path(pdf_path).stem + "_ocr"

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"总页数: {len(doc)}")
    print(f"输出目录: {out_path}")

    for page_num, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        img_path = out_path / f"page{page_num+1}.png"
        img.save(img_path)

        text = pytesseract.image_to_string(img, lang='chi_sim+eng')

        txt_path = out_path / f"page{page_num+1}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        preview = text[:100].replace('\n', ' ').strip()
        print(f"  Page {page_num+1}: {'识别到文字' if text.strip() else '[无文字]'} - {preview[:50]}...")

    doc.close()

    combined_txt = out_path / "combined.txt"
    with open(combined_txt, "w", encoding="utf-8") as out:
        for txt_file in sorted(out_path.glob("page*.txt")):
            page_num = int(txt_file.stem.replace("page", ""))
            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()
            out.write(f"\n{'='*60}\n")
            out.write(f"Page {page_num}\n")
            out.write(f"{'='*60}\n")
            out.write(content)

    print(f"\n完成! 文字识别结果: {combined_txt}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR识别扫描版PDF")
    parser.add_argument("pdf", help="PDF文件路径")
    parser.add_argument("output_dir", nargs="?", default=None, help="输出目录 (默认: PDF名_ocr)")
    parser.add_argument("--dpi", type=int, default=200, help="图片渲染DPI (默认: 200)")
    parser.add_argument("--tesseract", default=None, help="Tesseract可执行文件路径")

    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"文件不存在: {args.pdf}")
        sys.exit(1)

    ocr_pdf(args.pdf, args.output_dir, args.dpi, args.tesseract)
