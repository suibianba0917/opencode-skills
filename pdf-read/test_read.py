import fitz
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

pdf_path = r'C:\Users\WP6KCF2\.config\opencode\skills\ccc-debug\references\公司内部\手机蓝牙数字钥匙系统FRS.pdf'
doc = fitz.open(pdf_path)

print(f"总页数: {len(doc)}")

for i, page in enumerate(doc[:3]):
    print(f"\n=== 第{i+1}页 ===")
    text = page.get_text()
    if text.strip():
        print(text[:2000])
    else:
        print("[扫描版/图片页，无可提取文本]")
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        print(f"页面尺寸: {pix.width}x{pix.height} px")

doc.close()
