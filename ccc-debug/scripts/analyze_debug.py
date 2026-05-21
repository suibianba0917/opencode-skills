#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
CCC Debug 分析入口
假设附件已下载解压到 extracted/ 目录。
解压流程由 Jira_access 负责（download_jira_attachments.py）。
输出: Y:\JIRA_Logs\{ticket_key}\分析过程\{ticket_key}_完整分析报告_YYYY-MM-DD_HH-MM-SS.md
"""
import os
import sys
import json
import subprocess as subproc
from datetime import datetime
import tempfile
import time

from analyze import generate_report, run_ai_analysis, parse_time_range_from_str

EMAIL_RECIPIENT = "le.xing@volkswagen-tech.com"
JIRA_BROWSE_URL = "https://devstack.vgc.com.cn/jira/browse/"


def md_to_html(md_text):
    """将 Markdown 转换为 HTML（用于 Outlook 邮件）"""
    try:
        import markdown
        import re
        html_body = markdown.markdown(
            md_text,
            extensions=['tables', 'fenced_code', 'nl2br'],
            output_format='html'
        )
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333; max-width: 900px; }}
pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; }}
code {{ background-color: #f0f0f0; padding: 2px 4px; border-radius: 2px; font-family: Consolas, monospace; font-size: 13px; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #f2f2f2; font-weight: bold; }}
h1, h2, h3, h4 {{ color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
blockquote {{ border-left: 4px solid #ddd; margin: 10px 0; padding-left: 15px; color: #666; }}
hr {{ border: none; border-top: 1px solid #ddd; margin: 15px 0; }}
a {{ color: #0066cc; text-decoration: none; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
    except ImportError:
        return f"<html><body><pre>{md_text}</pre></body></html>"


def send_email(subject, body, ticket_key=None, ticket_summary=None):
    """通过 Outlook 发送 HTML 邮件"""
    import re
    if ticket_summary:
        subject = f"{ticket_key} - {ticket_summary}"
    if ticket_key:
        jira_link = f'<a href="{JIRA_BROWSE_URL}{ticket_key}">{ticket_key}</a>'
        html_body = md_to_html(body)
        html_body = html_body.replace('<body>', f'<body><p><strong>JIRA:</strong> {jira_link}</p><hr>', 1)
    else:
        html_body = md_to_html(body)
    html_body = html_body.replace('"', '&quot;').replace('\n', '&#10;')

    ps_script = f'''
$ol = New-Object -ComObject Outlook.Application
$mail = $ol.CreateItem(0)
$mail.Subject = "{subject}"
$mail.HTMLBody = "{html_body}"
$mail.To = "{EMAIL_RECIPIENT}"
$mail.Send()
'''
    try:
        result = subproc.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            print(f"  [邮件] 已发送到 {EMAIL_RECIPIENT}")
            return True
        else:
            print(f"  [邮件] 失败: {result.stderr[:200] if result.stderr else 'unknown'}")
            return False
    except Exception as e:
        print(f"  [邮件] 异常: {e}")
        return False


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
        print(f"    [错误] 未找到 get_ticket_detail.py，停止分析")
        sys.exit(1)

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
            print(f"    [错误] 获取失败: {result.stderr[:100] if result.stderr else 'unknown'}，停止分析")
            sys.exit(1)
    except subproc.TimeoutExpired:
        print(f"    [错误] 获取超时，停止分析")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"    [错误] JSON解析失败: {e}，停止分析")
        sys.exit(1)
    except Exception as e:
        print(f"    [错误] {e}，停止分析")
        sys.exit(1)


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
        lines.append("### JIRA 评论 (全部 {count} 条，仅供参考，需日志验证)".format(count=len(comments)))
        for c in comments:
            body = c.get('body', {})
            created = c.get('created', '')[:16]
            author = c.get('author', {}).get('displayName', 'Unknown')
            if isinstance(body, dict):
                comment_text = ""
                for block in body.get('content', []):
                    for content_item in block.get('content', []):
                        comment_text += content_item.get('text', '')
                lines.append(f"- **{author}** [{created}]: {comment_text[:300]} [需日志验证]")
            else:
                lines.append(f"- **{author}** [{created}]: {str(body)[:300]} [需日志验证]")

    return '\n'.join(lines)


def main():
    t0 = time.time()
    if len(sys.argv) < 2:
        print("Usage: python analyze_debug.py <ticket_key> [--extracted-dir <path>] [--output-dir <path>] [--skip-rule]")
        sys.exit(1)

    ticket_key = sys.argv[1]
    extracted_dir = None
    output_dir = None
    skip_rule = False

    for i in range(2, len(sys.argv)):
        if sys.argv[i] == '--extracted-dir' and i + 1 < len(sys.argv):
            extracted_dir = sys.argv[i + 1]
        elif sys.argv[i] == '--output-dir' and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
        elif sys.argv[i] == '--skip-rule':
            skip_rule = True

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
    if jira_context is None:
        print("  [错误] JIRA 信息获取失败，无法继续分析")
        sys.exit(1)
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
    from datetime import datetime as _dt, timedelta

    exact_start, exact_end, _ = parse_time_range_from_str(jira_context_str)
    if exact_start and exact_end:
        print(f"[时间过滤] JIRA 时间范围: {exact_start.strftime('%Y-%m-%d %H:%M')}-{exact_end.strftime('%H:%M')}")
        window_configs = [
            ("精确时间", (exact_start, exact_end)),
            ("±5分钟", (exact_start - timedelta(minutes=5), exact_end + timedelta(minutes=5))),
            ("±15分钟", (exact_start - timedelta(minutes=15), exact_end + timedelta(minutes=15))),
        ]
    elif exact_start:
        print(f"[时间过滤] JIRA 问题时间: {exact_start.strftime('%H:%M')}")
        window_configs = [
            ("问题时间±5min", (exact_start - timedelta(minutes=5), exact_start + timedelta(minutes=5))),
            ("问题时间±15min", (exact_start - timedelta(minutes=15), exact_start + timedelta(minutes=15))),
            ("全天", None),
        ]
    else:
        print("[时间过滤] JIRA 无问题时间，使用全天日志")
        window_configs = [
            ("全天", None),
        ]

    report_path, report_content, log_snippets, fault_info = None, None, [], []
    final_time_range = None

    if no_logs:
        pass  # 跳过自适应窗口，直接到无日志处理
    elif skip_rule:
        print("  跳过规则匹配报告")
    else:
        for attempt_label, time_range in window_configs:
            print(f"\n  [尝试{attempt_label}]")
            t_rule = time.time()
            print(f"    [list_extracted_files]", end="", flush=True)
            rp, rc, ls, fi = generate_report(
                ticket_key, extracted_dir, output_dir,
                jira_context_str, no_logs=False,
                time_range_override=time_range
            )
            elapsed = time.time() - t_rule
            print(f"    [generate_report总计] {elapsed:.1f}s")

            total_snippet_lines = sum(len(v) if isinstance(v, list) else 0 for v in [ls]) if ls else 0
            has_findings = fi and any(f.get('id', 0) < 900 for f in fi)
            has_snippets = total_snippet_lines > 0

            print(f" {elapsed:.1f}s | findings={len(fi) if fi else 0} | snippets={total_snippet_lines}")

            if has_findings or has_snippets:
                print(f"    ✅ 足够，停止扩展")
                report_path, report_content, log_snippets, fault_info = rp, rc, ls, fi
                final_time_range = time_range
                break
            else:
                print(f"    ⚠️ 日志不足，继续扩展")
                report_path, report_content, log_snippets, fault_info = rp, rc, ls, fi
                final_time_range = time_range

    if no_logs:
        os.makedirs(output_dir, exist_ok=True)
        ts = _dt.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_file = os.path.join(output_dir, f'{ticket_key}_完整分析报告_{ts}.md')

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
    ai_path, ai_content = run_ai_analysis(ticket_key, extracted_dir, output_dir, jira_context_str, log_snippets, fault_info, time_range_override=final_time_range)
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

    print("="*50)
    print("3. 发送邮件...")
    t_email = time.time()
    report_file = ai_path if ai_path else report_path
    if report_file and os.path.exists(report_file):
        report_basename = os.path.basename(report_file)
        report_name = report_basename.rsplit('.', 1)[0]
        with open(report_file, 'r', encoding='utf-8') as f:
            body = f.read()
        ticket_summary = jira_context.get('summary', '') if jira_context else ''
        send_email(f"{report_name} - {ticket_summary}", body, ticket_key)
        print(f"  [邮件耗时] {time.time()-t_email:.1f}s")
    else:
        print("  [跳过] 报告文件不存在")


if __name__ == '__main__':
    main()
