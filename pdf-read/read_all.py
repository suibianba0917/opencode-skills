import fitz
import os

pdf_path = r'C:\Users\WP6KCF2\.config\opencode\skills\ccc-debug\references\公司内部\手机蓝牙数字钥匙系统FRS.pdf'
out_path = r'C:\Users\WP6KCF2\.config\opencode\skills\ccc-debug\references\公司内部\手机蓝牙数字钥匙系统FRS_content.txt'

doc = fitz.open(pdf_path)

with open(out_path, 'w', encoding='utf-8') as f:
    f.write(f"总页数: {len(doc)}\n")
    f.write("=" * 60 + "\n")
    for i, page in enumerate(doc):
        text = page.get_text()
        f.write(f"\n=== 第{i+1}页 ===\n")
        if text.strip():
            f.write(text)
        else:
            f.write("[无文本]\n")

doc.close()
print(f"已保存到: {out_path}")
