#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量 Debug 分析脚本
遍历历史 Closed JIRA，下载日志并分析，验证 ccc-debug skill。
断点续传：已完成的不重复分析。
"""
import os
import sys
import glob
import json
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_SCRIPT = os.path.join(SCRIPT_DIR, 'download_jira_attachments.py')
ANALYZE_SCRIPT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'ccc-debug', 'scripts', 'analyze_debug.py'))  # ccc-debug 分析入口

LOG_BASE = r'Y:\JIRA_Logs'
PROGRESS_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', 'data', 'batch_progress.json'))


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_progress(data):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_download(ticket_key):
    ticket_dir = os.path.join(LOG_BASE, ticket_key)
    attachments_dir = os.path.join(ticket_dir, 'Attachments')
    already_has_files = os.path.exists(attachments_dir) and len(os.listdir(attachments_dir)) > 0

    if already_has_files:
        print(f"  [跳过下载] {ticket_key} (已有 {len(os.listdir(attachments_dir))} 个附件)")
        return True

    print(f"  [下载] {ticket_key}...")
    result = subprocess.run(
        ['python', DOWNLOAD_SCRIPT, ticket_key, '--auto'],
        capture_output=True, text=True, timeout=600,
        cwd=SCRIPT_DIR
    )
    if result.returncode == 0:
        print(f"  [下载成功]")
        return True
    else:
        print(f"  [下载失败] {result.stderr[:200] if result.stderr else 'unknown error'}")
        return False


def run_analyze(ticket_key):
    ticket_dir = os.path.join(LOG_BASE, ticket_key)
    attachments_dir = os.path.join(ticket_dir, 'Attachments')
    extracted_dir = os.path.join(ticket_dir, 'extracted')
    analysis_dir = os.path.join(ticket_dir, '分析过程')

    has_result = os.path.exists(analysis_dir) and len(glob.glob(os.path.join(analysis_dir, '完整分析报告.md'))) > 0

    if has_result:
        print(f"  [跳过分析] {ticket_key} (已有分析结果)")
        return True

    if not os.path.exists(attachments_dir) or len(os.listdir(attachments_dir)) == 0:
        print(f"  [警告] {ticket_key} 无附件，跳过")
        return False

    print(f"  [分析] {ticket_key}...")
    result = subprocess.run(
        ['python', ANALYZE_SCRIPT, ticket_key, '--extracted-dir', extracted_dir, '--output-dir', analysis_dir],
        capture_output=True, text=True, timeout=900,
        cwd=SCRIPT_DIR
    )
    if result.returncode == 0:
        print(f"  [分析成功]")
        if result.stdout:
            for line in result.stdout.split('\n'):
                if '[完成]' in line or '[成功]' in line:
                    print(f"    {line.strip()}")
        return True
    else:
        print(f"  [分析失败] {result.stderr[:200] if result.stderr else 'unknown error'}")
        return False


def main():
    if len(sys.argv) < 2:
        print("用法: python batch_debug.py <tickets.txt")
        print("  tickets.txt 每行一个 JIRA 号，如 VCTCEM-23462")
        sys.exit(1)

    ticket_file = sys.argv[1]
    if not os.path.exists(ticket_file):
        print(f"[错误] 文件不存在: {ticket_file}")
        sys.exit(1)

    with open(ticket_file, 'r', encoding='utf-8') as f:
        tickets = [line.strip() for line in f if line.strip()]

    progress = load_progress()
    total = len(tickets)
    done = sum(1 for t in tickets if progress.get(t, {}).get('analyzed'))
    print(f"=" * 60)
    print(f"批量 Debug 分析")
    print(f"总任务: {total} 个")
    print(f"已完成: {done} 个")
    print(f"待处理: {total - done} 个")
    print(f"=" * 60)

    for i, ticket_key in enumerate(tickets, 1):
        if ticket_key in progress and progress[ticket_key].get('analyzed'):
            print(f"[{i}/{total}] {ticket_key} 已完成，跳过")
            continue

        print(f"\n[{i}/{total}] === {ticket_key} ===")
        start = datetime.now()

        step = progress.get(ticket_key, {}).get('step', 'download')
        download_ok = step == 'analyze' or run_download(ticket_key)
        if not download_ok:
            progress[ticket_key] = {'step': 'download', 'error': 'download failed'}
            save_progress(progress)
            continue

        analyze_ok = run_analyze(ticket_key)

        elapsed = (datetime.now() - start).total_seconds()
        progress[ticket_key] = {
            'step': 'done' if analyze_ok else 'analyze',
            'analyzed': analyze_ok,
            'time': elapsed,
            'timestamp': datetime.now().isoformat()
        }
        save_progress(progress)
        done_now = sum(1 for t in tickets if progress.get(t, {}).get('analyzed'))
        print(f"  进度: {done_now}/{total} ({done_now*100//total}%)")

    print(f"\n{'=' * 60}")
    print(f"全部完成! 共分析 {sum(1 for t in tickets if progress.get(t, {}).get('analyzed'))}/{total} 个")
    print(f"详细进度: {PROGRESS_FILE}")


if __name__ == '__main__':
    main()
