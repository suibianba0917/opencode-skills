#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF图片提取脚本
支持两种方式:
1. PyMuPDF (推荐) - pip install pymupdf
2. pdfimages (命令行) - 需要安装 poppler-utils
"""
import sys
import os
import subprocess

def extract_images_pymupdf(pdf_path, output_dir=None):
    """使用PyMuPDF提取图片"""
    try:
        import fitz
    except ImportError:
        print("PyMuPDF未安装，请运行: pip install pymupdf")
        return False
    
    doc = fitz.open(pdf_path)
    
    if output_dir is None:
        output_dir = os.path.splitext(pdf_path)[0] + "_images"
    
    os.makedirs(output_dir, exist_ok=True)
    
    img_count = 0
    for page_num, page in enumerate(doc):
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            img_name = f"page{page_num+1}_img{img_index+1}.{image_ext}"
            with open(os.path.join(output_dir, img_name), "wb") as f:
                f.write(image_bytes)
            img_count += 1
    
    doc.close()
    print(f"✓ 提取 {img_count} 张图片到: {output_dir}")
    return True

def extract_images_cli(pdf_path, output_dir=None):
    """使用pdfimages命令行提取"""
    if output_dir is None:
        output_dir = os.path.splitext(pdf_path)[0] + "_images"
    
    os.makedirs(output_dir, exist_ok=True)
    original_dir = os.getcwd()
    
    try:
        os.chdir(output_dir)
        result = subprocess.run(
            ["pdfimages", "-j", pdf_path, "img"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            files = [f for f in os.listdir(".") if f.startswith("img-")]
            print(f"✓ 提取 {len(files)} 张图片到: {output_dir}")
            return True
    except FileNotFoundError:
        print("pdfimages未安装")
    finally:
        os.chdir(original_dir)
    
    return False

def extract_images(pdf_path, output_dir=None, method="auto"):
    """提取图片主函数"""
    if method == "pymupdf":
        return extract_images_pymupdf(pdf_path, output_dir)
    elif method == "cli":
        return extract_images_cli(pdf_path, output_dir)
    else:
        # 自动选择: 优先pymupdf
        if extract_images_pymupdf(pdf_path, output_dir):
            return True
        return extract_images_cli(pdf_path, output_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python pdf_extract_images.py <PDF文件> [输出目录]")
        print("依赖: pip install pymupdf")
        print("或安装 poppler-utils: https://github.com/oschwartz10612/poppler-windows")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    extract_images(pdf_path, output_dir)
