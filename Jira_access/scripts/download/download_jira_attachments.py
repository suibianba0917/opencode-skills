#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import os
import sys
import argparse
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config.config import get_config, JIRA_URL, JIRA_TOKEN

def find_7z():
    possible_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def merge_split_archives(base_dir):
    seven_zip = find_7z()

    if not seven_zip:
        print("  [警告] 未找到 7-Zip，跳过分卷合并")
        print("  [提示] 建议安装 7-Zip: https://www.7-zip.org/")
        return []

    merged_files = []

    for filename in os.listdir(base_dir):
        filepath = os.path.join(base_dir, filename)

        if filename.endswith('.001'):
            base_name = filename[:-4]
            first_part = os.path.join(base_dir, filename)

            print(f"  [合并] 发现分卷压缩包: {filename}")

            output_dir = os.path.join(os.path.dirname(base_dir), 'extracted')
            os.makedirs(output_dir, exist_ok=True)

            try:
                cmd = [seven_zip, 'x', first_part, f'-o{output_dir}', '-y']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                if result.returncode == 0:
                    print(f"  [成功] 解压到: {output_dir}")
                    merged_files.append(base_name)
                else:
                    print(f"  [失败] 7-Zip 返回: {result.returncode}")
                    print(f"  [错误] {result.stderr[:200] if result.stderr else 'Unknown error'}")
            except subprocess.TimeoutExpired:
                print("  [失败] 解压超时")
            except Exception as e:
                print(f"  [失败] {str(e)}")

    return merged_files

def extract_with_python_zip(filepath, output_dir):
    """使用 Python zipfile 解压（处理中文文件名）"""
    import zipfile
    extracted_count = 0
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            for name in zf.namelist():
                try:
                    zf.extract(name, output_dir)
                    extracted_count += 1
                except Exception as e:
                    pass
        return extracted_count
    except Exception as e:
        print(f"    [Python解压失败] {e}")
        return 0


def extract_single_archives(base_dir):
    seven_zip = find_7z()
    extracted_count = 0

    zip_files = []
    for filename in os.listdir(base_dir):
        if filename.endswith('.zip') or filename.endswith('.tar.gz'):
            if not any(filename.endswith(f'.{str(i).zfill(3)}') for i in range(1, 100)):
                zip_files.append(filename)

    if not zip_files:
        return 0

    output_dir = os.path.join(os.path.dirname(base_dir), 'extracted')
    os.makedirs(output_dir, exist_ok=True)

    for filename in zip_files:
        filepath = os.path.join(base_dir, filename)
        print(f"  [解压] {filename}")

        if seven_zip:
            try:
                cmd = [seven_zip, 'x', filepath, f'-o{output_dir}', '-y']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

                if result.returncode == 0:
                    print(f"    [成功] 7-Zip")
                    extracted_count += 1
                else:
                    print(f"    [7-Zip失败，尝试Python...]")
                    if extract_with_python_zip(filepath, output_dir) > 0:
                        print(f"    [成功] Python zipfile")
                        extracted_count += 1
            except Exception as e:
                print(f"    [7-Zip异常: {str(e)[:50]}，尝试Python...]")
                if extract_with_python_zip(filepath, output_dir) > 0:
                    print(f"    [成功] Python zipfile")
                    extracted_count += 1
        else:
            if extract_with_python_zip(filepath, output_dir) > 0:
                print(f"    [成功] Python zipfile")
                extracted_count += 1
            else:
                print(f"    [失败] 无解压工具")

    return extracted_count

def generate_readme(extracted_dir, jira_key):
    """生成日志索引文件 README.txt"""
    readme_path = os.path.join(extracted_dir, 'README.txt')

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"=== {jira_key} 日志索引 ===\n\n")
        f.write(f"生成时间: {os.popen('date').read().strip()}\n\n")
        f.write("--- 日志文件列表 ---\n\n")

        for root, dirs, files in os.walk(extracted_dir):
            # 跳过 README 自身所在目录的计算
            rel_root = os.path.relpath(root, extracted_dir)
            if rel_root == '.':
                continue

            level = rel_root.count(os.sep)
            indent = '  ' * level
            folder_name = os.path.basename(root) or 'extracted'
            f.write(f"{indent}{folder_name}/\n")

            sub_indent = '  ' * (level + 1)
            for file in sorted(files):
                if file == 'README.txt':
                    continue
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                if size > 1024 * 1024:
                    size_str = f"{size / 1024 / 1024:.1f} MB"
                else:
                    size_str = f"{size / 1024:.1f} KB"
                f.write(f"{sub_indent}{file} ({size_str})\n")

        f.write("\n--- 日志类型识别 ---\n")
        f.write("| 文件 | 类型 | 来源 |\n")
        f.write("|------|------|------|\n")

        for root, dirs, files in os.walk(extracted_dir):
            for file in files:
                if file == 'README.txt':
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, extracted_dir)

                log_type = ""
                source = ""

                if 'security-sysdiagnose' in file:
                    log_type = "KTS/证书日志"
                    source = "手机端"
                elif 'system_logs' in file or 'logarchive' in file:
                    log_type = "系统日志"
                    source = "手机端"
                elif 'errors' in file:
                    log_type = "错误汇总"
                    source = "手机端"
                elif 'logs' in file and 'logarchive' not in file:
                    log_type = "应用日志"
                    source = "手机端"
                elif file.endswith('.ASC'):
                    log_type = "CAN日志"
                    source = "车端"
                elif file.endswith('.blf'):
                    log_type = "BLF日志"
                    source = "车端"
                elif file.endswith('.log'):
                    log_type = "后台日志"
                    source = "后台"
                elif 'trace' in file.lower():
                    log_type = "跟踪日志"
                    source = "后台"

                if log_type:
                    f.write(f"| {rel_path} | {log_type} | {source} |\n")

        f.write("\n--- 使用说明 ---\n")
        f.write("1. 使用 ccc-debug skill 分析日志\n")
        f.write("2. 分析报告保存在 '分析过程/' 目录\n")
        f.write("3. 分析报告命名: 分析过程说明.md\n")

    print(f"  [生成] 日志索引: {readme_path}")
    return readme_path


def download_jira_attachments(jira_key, output_dir=None, auto=False, analyze=False):
    jira_url = JIRA_URL
    jira_token = JIRA_TOKEN
    if not jira_url or not jira_token:
        print("Error: JIRA_URL or JIRA_TOKEN not configured")
        sys.exit(1)

    if output_dir is None:
        output_dir = rf'Y:\JIRA_Logs\{jira_key}'

    attachments_dir = os.path.join(output_dir, 'Attachments')
    extracted_dir = os.path.join(output_dir, 'extracted')
    process_dir = os.path.join(output_dir, '分析过程')

    os.makedirs(attachments_dir, exist_ok=True)
    print(f"目录结构已创建:")
    print(f"  {output_dir}")
    print(f"  ├── Attachments/")
    print(f"  ├── extracted/")
    print(f"  └── 分析过程/")

    session = requests.Session()
    session.get(f'{jira_url}/login.jsp', timeout=30)

    headers = {'Authorization': f'Bearer {jira_token}'}

    url = f'{jira_url}/rest/api/2/issue/{jira_key}?fields=attachment'
    resp = session.get(url, headers=headers, timeout=30)

    if resp.status_code != 200:
        print(f'Error getting attachments: {resp.status_code} - {resp.text[:200]}')
        return

    data = resp.json()
    attachments = data.get('fields', {}).get('attachment', [])

    if not attachments:
        print(f'No attachments found for {jira_key}')
        return

    print(f'\n发现 {len(attachments)} 个附件，下载到: Attachments/')

    for att in attachments:
        att_id = att.get('id')
        filename = att.get('filename')
        download_url = f'{jira_url}/secure/attachment/{att_id}/{filename}'
        output_path = os.path.join(attachments_dir, filename)

        if os.path.exists(output_path):
            print(f'  [跳过] {filename} (已存在)')
            continue

        print(f'  [下载] {filename}...')
        resp = session.get(download_url, headers=headers, timeout=300, stream=True)

        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            size_mb = os.path.getsize(output_path) / 1024 / 1024
            print(f'    [成功] {size_mb:.1f} MB')
        else:
            print(f'    [失败] HTTP {resp.status_code}')

    print(f'\n所有文件已下载到: {attachments_dir}')

    print(f'\n--- 下载完成 ---')
    print(f'  附件目录: {attachments_dir}')
    print(f'  下一步: 点击"Start Analysis"进行解压和 AI 深度分析')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='下载JIRA附件并准备日志文件')
    parser.add_argument('jira_key', help='JIRA issue key (例如: VCTCEM-35292)')
    parser.add_argument('--output', help='输出目录 (默认: Y:\\JIRA_Logs\\{jira_key})')
    parser.add_argument('--auto', action='store_true', help='自动处理日志（无需确认）')
    parser.add_argument('--analyze', action='store_true', help='处理后提示启动分析')
    args = parser.parse_args()

    download_jira_attachments(args.jira_key, output_dir=args.output, auto=args.auto, analyze=args.analyze)
