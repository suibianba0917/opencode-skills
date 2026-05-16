---
name: pdf-read
description: PDF文档读取 - 使用PyMuPDF/pypdf提取PDF文本内容
version: 2.0
author: default
---

# PDF 文档读取 Skill

## 功能说明

使用 Python 的 `PyMuPDF` (推荐) 或 `pypdf` 库读取 PDF 文档并提取文本内容。

### 为什么选 PyMuPDF

- 速度比 pypdf 快 5-10 倍
- 文本提取准确率更高
- 支持图片/表格/链接/注释提取
- 页面操作（旋转/裁剪/水印）更强大

## 使用方法

### 基础读取 (推荐 PyMuPDF)

```python
import fitz  # PyMuPDF

pdf_path = r"你的PDF文件路径"
doc = fitz.open(pdf_path)

print(f"总页数: {len(doc)}")

for i, page in enumerate(doc):
    text = page.get_text()
    print(f"\n=== 第 {i+1} 页 ===")
    print(text)

doc.close()
```

### 指定页码范围

```python
import fitz

doc = fitz.open("file.pdf")

# 读取前3页
for page in doc[:3]:
    print(page.get_text())

# 读取第5-10页
for page in doc[4:10]:
    print(f"Page {page.number + 1}:", page.get_text())

doc.close()
```

### 读取并保存到文件

```python
import fitz

pdf_path = r"你的PDF文件路径"
output_txt = r"输出文本文件路径"

doc = fitz.open(pdf_path)

with open(output_txt, "w", encoding="utf-8") as f:
    for page in doc:
        text = page.get_text()
        f.write(f"\n=== Page {page.number + 1} ===\n")
        f.write(text if text else "No text found")

print(f"已保存到: {output_txt}")
doc.close()
```

### 获取PDF元信息

```python
import fitz

doc = fitz.open("document.pdf")
meta = doc.metadata

print(f"标题: {meta.get('title', 'N/A')}")
print(f"作者: {meta.get('author', 'N/A')}")
print(f"主题: {meta.get('subject', 'N/A')}")
print(f"创建者: {meta.get('creator', 'N/A')}")
print(f"页数: {len(doc)}")

doc.close()
```

### 提取图片

```python
import fitz

doc = fitz.open("file.pdf")
output_dir = "images"

for page_num, page in enumerate(doc):
    for img_index, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]
        image_ext = base_image["ext"]

        img_name = f"page{page_num+1}_img{img_index+1}.{image_ext}"
        with open(f"{output_dir}/{img_name}", "wb") as f:
            f.write(image_bytes)

doc.close()
```

### 提取表格

```python
import fitz

doc = fitz.open("file.pdf")

for i, page in enumerate(doc):
    tables = page.find_tables()
    for table in tables:
        data = table.extract()
        for row in data:
            print(row)

doc.close()
```

## 脚本工具

| 脚本 | 功能 | 命令 |
|------|------|------|
| pdf_read.py | 读取PDF文本(可选是否提取图片) | `python pdf_read.py <pdf> [起始页] [结束页] [--no-images]` |
| pdf_to_txt.py | PDF转文本文件 | `python pdf_to_txt.py <pdf> [输出txt]` |
| pdf_info.py | 获取PDF元信息 | `python pdf_info.py <pdf>` |
| pdf_extract_images.py | 提取PDF图片 | `python pdf_extract_images.py <pdf> [输出目录]` |
| pdf_extract_tables.py | 提取PDF表格 | `python pdf_extract_tables.py <pdf> [起始页] [结束页]` |
| pdf_ocr.py | OCR识别扫描版PDF | `python pdf_ocr.py <pdf> [输出目录] [--dpi 200]` |

### pdf_read.py 参数说明

```
python pdf_read.py <pdf> [起始页] [结束页] [--no-images]

参数:
  <pdf>              PDF文件路径 (必需)
  [起始页]           起始页码，从0开始 (默认: 0)
  [结束页]           结束页码，不包含 (默认: 全部)
  --no-images        不提取图片，避免生成_images文件夹

示例:
  python pdf_read.py document.pdf              # 读取全部，包含图片
  python pdf_read.py document.pdf 0 3          # 读取前3页
  python pdf_read.py document.pdf 0 3 --no-images  # 读取前3页，不提取图片
```

### pdf_ocr.py 参数说明

```
python pdf_ocr.py <pdf> [输出目录] [--dpi 200] [--tesseract PATH]

参数:
  <pdf>              PDF文件路径 (必需)
  [输出目录]          输出目录 (默认: PDF文件名_ocr)
  --dpi 200          图片渲染DPI，越高越清晰但越慢 (默认: 200)
  --tesseract PATH   Tesseract可执行文件路径 (如不在PATH中)

依赖:
  pip install Pillow pytesseract pymupdf
  Windows需安装Tesseract: https://github.com/UB-Mannheim/tesseract/wiki

示例:
  python pdf_ocr.py document.pdf                    # 识别全部页
  python pdf_ocr.py document.pdf result --dpi 300   # 300DPI，输出到result目录
```

### OCR 识别（扫描版 PDF）

扫描版 PDF（如扫描件、影印件）没有可提取的文本层，需要用 OCR 识别。

**依赖安装：**
```bash
# Python 3.14
py -3.14 -m pip install Pillow pytesseract

# 还需要安装 Tesseract OCR 引擎
# Windows: 下载 https://github.com/UB-Mannheim/tesseract/wiki
# 安装后添加 PATH 或指定路径
```

**基本 OCR 流程：**

```python
import fitz
from PIL import Image
import pytesseract

pdf_path = r"你的PDF文件路径"

# 配置 tesseract 路径（如果不在 PATH 中）
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

doc = fitz.open(pdf_path)

for page_num, page in enumerate(doc):
    # 将页面转为图片
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x 缩放提高清晰度
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # OCR 识别
    text = pytesseract.image_to_string(img, lang='chi_sim+eng')

    print(f"\n=== Page {page_num + 1} ===")
    print(text if text.strip() else "[无文字]")

doc.close()
```

**提取图片 + OCR（批量处理）：**

```python
import fitz
import pytesseract
from pathlib import Path

pdf_path = r"你的PDF文件路径"
output_dir = Path(pdf_path).stem + "_ocr"
Path(output_dir).mkdir(exist_ok=True)

doc = fitz.open(pdf_path)

for page_num, page in enumerate(doc):
    for img_index, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        base_image = doc.extract_image(xref)
        img_bytes = base_image["image"]
        img_ext = base_image["ext"]

        # 保存图片
        img_path = f"{output_dir}/page{page_num+1}_img{img_index+1}.{img_ext}"
        with open(img_path, "wb") as f:
            f.write(img_bytes)

        # OCR 识别
        pil_img = Image.open(img_path)
        text = pytesseract.image_to_string(pil_img, lang='chi_sim+eng')

        # 保存识别结果
        txt_path = f"{output_dir}/page{page_num+1}_img{img_index+1}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"Page {page_num+1} Image {img_index+1}: 识别完成")

doc.close()
```

### 常见问题

- **Tesseract 未找到**：设置 `pytesseract.pytesseract.tesseract_cmd` 指向安装路径
- **识别不准**：尝试提高 `pixmap` 的 DPI/缩放倍数，或调整 `lang` 参数
- **语言支持**：`lang='chi_sim'` 简体中文，`lang='chi_tra'` 繁体文，`lang='eng'` 英文，可组合如 `'chi_sim+eng'`

## 限制

- 需要安装 pymupdf: `pip install pymupdf`
- 扫描版PDF（图片）需要OCR处理
- 某些PDF有加密保护，无法直接读取

## 快速使用示例

读取用户的PDF并介绍内容：

```python
import fitz

pdf_path = r"用户提供的路径"
doc = fitz.open(pdf_path)

print(f"总页数: {len(doc)}")

# 读取前几页了解内容
for page in doc[:3]:
    print(f"\n=== Page {page.number + 1} ===")
    print(page.get_text()[:1000])

doc.close()
```
