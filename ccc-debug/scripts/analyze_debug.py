#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
CCC Debug 分析入口
假设附件已下载解压到 extracted/ 目录。
解压流程由 Jira_access 负责（download_jira_attachments.py）。
输出: Y:\JIRA_Logs\{ticket_key}\分析过程\完整分析报告_YYYY-MM-DD_HH-MM-SS.md
"""
import os
import sys
import json
import subprocess as subproc
from datetime import datetime
import tempfile
import time

from analyze import generate_report, run_ai_analysis


def check_extracted(extracted_dir):
    """检查解压目录是否有有效日志文件"""
    if not os.path.exists(extracted_dir):
        return False, "目录不存在"
    files = []
    for root, dirs, filenames in os.walk(extracted_dir):
        for f in filenames:
            if not f.startswith('.') and not f.endswith('.done'):
                files.append(os.path.join(root, f))
    if not files:
        return False, "目录为空"
    return True, f"已解压 {len(files)} 个文件"


def fetch_jira_context(ticket_key, output_dir):
    """获取 JIRA Issue Description + Comments"""
    print("  尝试获取 JIRA 信息...")
    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Jira_access', 'scripts'))
    jira_access_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Jira_access'))
    get_detail_script = os.path.join(script_dir, 'get_ticket_detail.py')

    if not os.path.exists(get_detail_script):
        print(f"    [跳过] 未找到 get_ticket_detail.py")
        return None

    try:
        result = subproc.run(
            ['python', get_detail_script, ticket_key, '--json'],
            capture_output=True, text=True, timeout=30,
            cwd=jira_access_dir
        )
        if result.returncode == 0 and result.stdout.strip():
            jira_context = json.loads(result.stdout)

            # 保存到文件
            context_file = os.path.join(tempfile.gettempdir(), 'jira_context_{ticket_key}.json')
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(jira_context, f, ensure_ascii=False, indent=2)
            print(f"    [成功] JIRA 信息已获取")
            return jira_context
        else:
            print(f"    [跳过] 获取失败: {result.stderr[:100] if result.stderr else 'unknown'}")
            return None
    except subproc.TimeoutExpired:
        print(f"    [跳过] 获取超时")
        return None
    except json.JSONDecodeError as e:
        print(f"    [跳过] JSON解析失败: {e}")
        return None
    except Exception as e:
        print(f"    [跳过] 错误: {e}")
        return None


def parse_description(desc_text):
    """解析 JIRA Description 文本，提取结构化字段"""
    if not desc_text:
        return {}
    import re
    fields = {}

    patterns = {
        'test_time': re.compile(r'Test/Error time.*?:\s*([^\r\n]+)', re.IGNORECASE),
        'short_text': re.compile(r'Short Text:\s*([^\r\n]+)', re.IGNORECASE),
        'precondition': re.compile(r'Precondition:\s*([^\r\n]+)', re.IGNORECASE),
        'action': re.compile(r'Action:\s*([^\r\n]+)', re.IGNORECASE),
        'actual_result': re.compile(r'Actual result:\s*([^\r\n]+)', re.IGNORECASE),
        'expected_result': re.compile(r'Expected result:\s*([^\r\n]+)', re.IGNORECASE),
        'healing': re.compile(r'Healing:\s*([^\r\n*][^\r\n]*?)(?=\n\s*\*{1,2}|\n[A-Z]|\Z)', re.IGNORECASE),
        'tester': re.compile(r'Tester/Location:\s*([^\r\n]+)', re.IGNORECASE),
        'device': re.compile(r'测试手机型号\s*[^0-9]*([^\s,，。\r\n]+)', re.IGNORECASE),
    }

    for key, pattern in patterns.items():
        m = pattern.search(desc_text)
        if m:
            val = m.group(1).strip()
            val = re.sub(r'\s{2,}', ' ', val)
            if val and val != '*':
                fields[key] = val

    remark_m = re.search(r'Remark:\s*(.+?)(?=\n[A-Z]|\n\n|\Z)', desc_text, re.IGNORECASE | re.DOTALL)
    if remark_m:
        fields['remark'] = re.sub(r'[\r\n]+', ' ', remark_m.group(1)).strip()

    return fields


def get_field_value(fv):
    if isinstance(fv, dict):
        return fv.get('value', fv.get('name', str(fv)))
    elif isinstance(fv, list):
        return ', '.join(str(get_field_value(v)) for v in fv) if fv else ''
    return str(fv).strip()


def format_jira_context_for_prompt(jira_context):
    """将 JIRA 上下文格式化为 prompt"""
    if not jira_context:
        return ""

    lines = []
    all_fields = jira_context.get('all_fields', {})

    lines.append("## 一、JIRA 信息")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("|------|------|")
    lines.append(f"| 问题ID | {jira_context.get('key', 'N/A')} |")
    lines.append(f"| 摘要 | {jira_context.get('summary', 'N/A')} |")

    issue_analysis = get_field_value(all_fields.get('customfield_20765', ''))
    vehicle_info = get_field_value(all_fields.get('customfield_20760', ''))
    if vehicle_info:
        lines.append(f"| 车型 | {vehicle_info} |")
    lines.append(f"| 状态 | {jira_context.get('status', 'N/A')} |")

    raw_desc = jira_context.get('description', '')
    if isinstance(raw_desc, dict):
        desc_text = ""
        for block in raw_desc.get('content', []):
            for content_item in block.get('content', []):
                desc_text += content_item.get('text', '')
    else:
        desc_text = str(raw_desc) if raw_desc else ""

    parsed = parse_description(desc_text) if desc_text else {}

    if parsed:
        lines.append(f"| 问题时间 | {parsed.get('test_time', 'N/A')} |")
        lines.append(f"| 测试人 | {parsed.get('tester', 'N/A')} |")
        lines.append("")
        if parsed.get('precondition'):
            lines.append(f"| 前置条件 | {parsed.get('precondition')} |")
        if parsed.get('action'):
            lines.append(f"| 操作步骤 | {parsed.get('action')} |")
        if parsed.get('actual_result'):
            lines.append(f"| 实际结果 | {parsed.get('actual_result')} |")
        if parsed.get('expected_result'):
            lines.append(f"| 期望结果 | {parsed.get('expected_result')} |")
        if parsed.get('device'):
            lines.append(f"| 测试手机 | {parsed.get('device')} |")
        if parsed.get('remark'):
            lines.append(f"| 备注 | {parsed.get('remark')} |")

    if issue_analysis:
        lines.append("")
        lines.append("| Issue Analysis | " + issue_analysis + " |")

    comments = jira_context.get('comments', [])
    if comments:
        lines.append("")
        lines.append("### JIRA 评论 (最新)")
        for c in reversed(comments[-5:]):
            body = c.get('body', {})
            created = c.get('created', '')[:16]
            author = c.get('author', {}).get('displayName', 'Unknown')
            if isinstance(body, dict):
                comment_text = ""
                for block in body.get('content', []):
                    for content_item in block.get('content', []):
                        comment_text += content_item.get('text', '')
                lines.append(f"- **{author}** [{created}]: {comment_text[:300]}")
            else:
                lines.append(f"- **{author}** [{created}]: {str(body)[:300]}")

    return '\n'.join(lines)


def main():
    t0 = time.time()
    if len(sys.argv) < 2:
        print("Usage: python analyze_debug.py <ticket_key> [--extracted-dir <path>] [--output-dir <path>]")
        sys.exit(1)

    ticket_key = sys.argv[1]
    extracted_dir = None
    output_dir = None

    for i in range(2, len(sys.argv)):
        if sys.argv[i] == '--extracted-dir' and i + 1 < len(sys.argv):
            extracted_dir = sys.argv[i + 1]
        elif sys.argv[i] == '--output-dir' and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]

    if not extracted_dir:
        base = r'Y:\JIRA_Logs'
        extracted_dir = os.path.join(base, ticket_key, 'extracted')

    if not output_dir:
        base = r'Y:\JIRA_Logs'
        output_dir = os.path.join(base, ticket_key, '分析过程')

    os.makedirs(output_dir, exist_ok=True)

    print("="*50)
    print("0. 获取 JIRA Ticket 信息...")
    t_jira = time.time()
    jira_context = fetch_jira_context(ticket_key, output_dir)
    jira_context_str = format_jira_context_for_prompt(jira_context)
    print(f"  [耗时] {time.time() - t_jira:.1f}s")

    print("="*50)
    print("检查日志目录...")
    ok, msg = check_extracted(extracted_dir)
    print(f"  {msg}")
    no_logs = not ok
    if no_logs:
        print(f"\n[警告] 日志目录为空，将基于 JIRA 信息 + 知识库生成分析报告")
        print(f"  建议：补充日志附件后重新分析以获得更精确结论")

    print("="*50)
    print("1. 生成规则匹配报告...")
    t_rule = time.time()
    report_path, report_content, log_snippets, fault_info = generate_report(ticket_key, extracted_dir, output_dir, jira_context_str, no_logs=no_logs)
    print(f"  [耗时] {time.time() - t_rule:.1f}s")

    if no_logs:
        os.makedirs(output_dir, exist_ok=True)
        from datetime import datetime as _dt
        ts = _dt.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_file = os.path.join(output_dir, f'完整分析报告_{ts}.md')

        fault_side = fault_info[0].get('fault_side', '需补充日志') if fault_info else '需补充日志'
        fault_phase = fault_info[0].get('fault_phase', '日志缺失') if fault_info else '日志缺失'
        error_code = fault_info[0].get('error_code', 'N/A') if fault_info else 'N/A'
        certainty = fault_info[0].get('certainty', '[待确认]') if fault_info else '[待确认]'
        root_cause = fault_info[0].get('root_cause', '无日志无法分析') if fault_info else '无日志无法分析'

        remediation_lines = []
        if fault_info:
            for side, measure in fault_info[0].get('remediation', []):
                remediation_lines.append(f"| {side} | {measure} |")

        issue_analysis = ""
        if jira_context_str:
            for line in jira_context_str.split('\n'):
                if 'Issue Analysis' in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        issue_analysis = parts[2].strip()
                    break

        jira_display = jira_context_str if jira_context_str else "(未获取到 JIRA 信息)"
        root_cause_detail = issue_analysis if issue_analysis else root_cause
        report_text = f"""{jira_display}

---

## 二、分析结论

**故障端**: {fault_side}
**失败环节**: {fault_phase}
**错误码**: {error_code}
**确定性**: {certainty}

---

## 三、关键日志片段

**无日志附件** — 无法提取日志片段

原因: 此 JIRA 工单未上传任何日志附件，无法进行深度分析。

**建议补充的日志**:
- CAN 日志 (ASC/BLF)：定位 PE/Polling 启停状态，确认 BLE 广播是否正常
- 车端 dk_service.log：查看 NFC/BLE 模块状态，确认配对/分享流程断点
- iOS sysdiagnose：查看手机端 CarKey 状态和 BLE 连接日志

---

## 四、根因分析

{root_cause_detail}

> 以上内容来自 JIRA Issue Analysis 字段，仅供参考。需补充日志验证。

---

## 五、整改建议

| 归属端 | 建议措施 |
|--------|----------|
{chr(10).join(remediation_lines) if remediation_lines else "| 分析 | 补充日志附件后重新分析 |"}

---

## 六、补充说明

**日志完整性: D级 (无日志)**

本次分析仅基于 JIRA 描述信息，结论不确定性较高。建议提票人补充完整日志后重新分析。

---

## 七、结论

日志缺失，无法精确定位根因。请补充 CAN 日志、车端 dk_service.log 和 iOS sysdiagnose 后重新分析。
"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"[完成] 无日志模式 - 报告已生成: {output_file}")
        print(f"  [总耗时] {time.time() - t0:.1f}s")
        summary = {
            'ticket_key': ticket_key,
            'report_path': output_file,
            'quick_report': report_path,
            'ai_report': None,
            'no_logs': True,
        }
        print(f"[完成] {json.dumps(summary)}")
        return

    print("="*50)
    print("2. 启动 AI 深度分析...")
    t_ai = time.time()
    ai_path, ai_content = run_ai_analysis(ticket_key, extracted_dir, output_dir, jira_context_str, log_snippets, fault_info)
    print(f"  [AI耗时] {time.time() - t_ai:.1f}s")
    print(f"  [总耗时] {time.time() - t0:.1f}s")

    summary = {
        'ticket_key': ticket_key,
        'report_path': ai_path if ai_path else report_path,
        'quick_report': None,
        'ai_report': ai_path,
        'no_logs': no_logs,
    }
    print(f"[完成] {json.dumps(summary)}")


if __name__ == '__main__':
    main()
