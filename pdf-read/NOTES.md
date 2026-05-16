# PDF-Read Skill 状态追踪

## 当前状态

| 项目 | 状态 |
|------|------|
| **版本** | 2.0 |
| **首选库** | PyMuPDF 1.27.2.2 |
| **备用库** | pypdf 6.8.0 |
| **文本提取** | ✅ 正常工作 |
| **图片提取** | ⚠️ 功能代码就绪，需安装 Build Tools |
| **表格提取** | ✅ 使用 PyMuPDF find_tables() |
| **OCR 扫描件** | ❌ 缺 PyTorch/numpy (Python 3.15 兼容问题) |

## 本地环境

- OS: Windows
- Python: 3.15
- 编译器: 无 MSVC Build Tools
- 临时脚本目录: `C:\Users\WP6KCF2\temp_scripts\`

## 已安装

```
pymupdf==1.27.2.2
pypdf==6.8.0
PyPDF2==3.0.1
fpdf==1.7.2
```

## 待办事项

- [ ] **高优先级** 评估 PDF 表格提取效果（PyMuPDF find_tables），如效果不佳可联系 IT 安装 MSVC 后改用 pdfplumber
- [ ] **中优先级** 联系 IT 推送 MSVC Build Tools，装完后 `pip install pdfplumber` 可补充更精准的表格提取
- [ ] **中优先级** 扫描件 OCR 方案待定（Python 3.15 生态暂无成熟方案）
- [ ] **低优先级** 评估 marker / Docling 等结构化解析工具（需要 Docker/WSL）

## 更新日志

### v2.0 (2026-04-28)
- 文本引擎从 pypdf 切换为 PyMuPDF（更快更准）
- 移除图片自动提取，现在默认不生成 `_images` 文件夹
- 添加 `--no-images` 参数控制图片提取
- 所有脚本添加 PyMuPDF 优先 + pypdf 回退机制
- 更新 SKILL.md 文档

### v1.0 (初始版本)
- 使用 pypdf 作为唯一文本引擎
- 默认自动提取图片到 `{文件名}_images` 文件夹
