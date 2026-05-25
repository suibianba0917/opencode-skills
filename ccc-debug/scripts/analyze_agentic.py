#!/usr/bin/env python3
# -*- coding: utf-8
r"""
CCC CarKey Debug Agentic 分析引擎 (新架构)
==========================================
核心思想：JIRA驱动排查方向 → AI自主生成假设 → 搜索验证 → 收敛/换假设 → 结论

流程:
1. 加载JIRA信息，理解问题本质
2. 生成排查假设(关键词列表)
3. Agent Loop: 搜索日志 → 验证假设 → 收敛/换假设
4. 输出7章节结构化报告

与旧架构区别:
- 旧: 规则引擎决定看什么 → snippets给AI分析
- 新: AI理解JIRA → 自主决定排查方向 → 搜索验证
"""
import os
import sys
import json
import glob
import re
import subprocess
import subprocess as subproc
import time
import tempfile
from datetime import datetime
from typing import List, Dict, Tuple, Optional

DEFAULT_MODEL = "LiteLLM/MiniMax-M2.5"

JIRA_BROWSE_URL = "https://devstack.vgc.com.cn/jira/browse/"


def md_to_html(md_text):
    try:
        import markdown
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
    EMAIL_RECIPIENT = "le.xing@volkswagen-tech.com"
    body_clean = body.replace('✅', '[OK]').replace('❌', '[FAIL]').replace('⚠️', '[WARN]')
    if ticket_summary:
        subject = f"{ticket_key} - {ticket_summary}"
    if ticket_key:
        jira_link = f'<a href="{JIRA_BROWSE_URL}{ticket_key}">{ticket_key}</a>'
        html_body = md_to_html(body_clean)
        html_body = html_body.replace('<body>', f'<body><p><strong>JIRA:</strong> {jira_link}</p><hr>', 1)
    else:
        html_body = md_to_html(body_clean)

    tmp_html = os.path.join(tempfile.gettempdir(), 'email_body_temp.html')
    with open(tmp_html, 'w', encoding='utf-8') as f:
        f.write(html_body)

    ps_script = f'''
$ol = New-Object -ComObject Outlook.Application
$mail = $ol.CreateItem(0)
$mail.Subject = "{subject}"
$bodyContent = Get-Content -Path "{tmp_html}" -Encoding UTF8 -Raw
$mail.HTMLBody = $bodyContent
$mail.To = "{EMAIL_RECIPIENT}"
$mail.Send()
Remove-Item -Path "{tmp_html}" -Force
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

# ===== 工具层 =====
class LogTool:
    """日志搜索和读取工具"""

    def __init__(self, extracted_dir: str):
        self.extracted_dir = extracted_dir
        self._file_cache = {}
        self._grep_results = {}
        self._cleaned_content = {}  # {rel_path: [cleaned_line, ...]}

    def list_logs(self) -> List[Dict]:
        """列出所有可用日志文件"""
        if not os.path.exists(self.extracted_dir):
            return []
        files = []
        for root, dirs, filenames in os.walk(self.extracted_dir):
            for f in filenames:
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, self.extracted_dir)
                size = os.path.getsize(fp)
                files.append({
                    'path': rel,
                    'size': size,
                    'size_str': f"{size/1024/1024:.1f}MB" if size > 1024*1024 else f"{size/1024:.1f}KB"
                })
        return files

    def grep_logs(self, patterns: List[str], max_results_per_pattern: int = 30) -> Dict[str, List[Dict]]:
        """多关键词全文搜索，返回匹配结果

        优先搜索清洗后的内存内容，其次搜索原始文件。

        Args:
            patterns: 搜索关键词列表
            max_results_per_pattern: 每个关键词最多返回结果数

        Returns:
            {pattern: [{file, line_no, content}]}
        """
        results = {}
        if not os.path.exists(self.extracted_dir):
            return results

        all_files = glob.glob(os.path.join(self.extracted_dir, '**', '*'), recursive=True)
        text_files = [f for f in all_files if f.endswith(('.txt', '.log', '.json'))]
        text_files = [f for f in text_files if os.path.getsize(f) <= 5 * 1024 * 1024]
        text_files.sort(key=lambda f: (0 if re.search(r'\\dk_service\.log$', f, re.IGNORECASE) else 1,
                                        0 if re.search(r'\\dk_service\.\d+\.log$', f, re.IGNORECASE) else 1,
                                        0 if re.search(r'\\tboxapp', f, re.IGNORECASE) else 1,
                                        0 if f.lower().endswith('.log') else 1,
                                        f))

        for pattern in patterns:
            pattern_lower = pattern.lower()
            matches = []

            for fp in text_files:
                if len(matches) >= max_results_per_pattern:
                    break
                try:
                    rel = os.path.relpath(fp, self.extracted_dir)

                    if rel in self._cleaned_content:
                        lines = self._cleaned_content[rel]
                    else:
                        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()

                    for i, line in enumerate(lines):
                        if pattern_lower in line.lower():
                            matches.append({
                                'file': rel,
                                'line_no': i + 1,
                                'content': line.strip()[:300]
                            })
                            if len(matches) >= max_results_per_pattern:
                                break
                except:
                    pass

            results[pattern] = matches

        self._grep_results.update(results)
        return results

    def read_snippets(self, file_path: str, line_nos: List[int], context_lines: int = 5) -> Dict[str, str]:
        """读取指定行及上下文

        Args:
            file_path: 文件相对路径
            line_nos: 行号列表(1-indexed)
            context_lines: 上下文行数

        Returns:
            {line_no: "full line content with context"}
        """
        fp = os.path.join(self.extracted_dir, file_path)
        if not os.path.exists(fp):
            return {}

        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except:
            return {}

        snippets = {}
        for ln in line_nos:
            start = max(0, ln - 1 - context_lines)
            end = min(len(lines), ln - 1 + context_lines + 1)
            snippet_lines = [f"{i+1}: {lines[i].rstrip()}" for i in range(start, end)]
            snippets[ln] = '\n'.join(snippet_lines)

        return snippets


# ===== JIRA 信息加载 =====
def load_jira_context(ticket_key: str) -> dict:
    """从JIRA获取ticket信息"""
    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Jira_access', 'scripts'))
    jira_access_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Jira_access'))
    get_detail_script = os.path.join(script_dir, 'get_ticket_detail.py')

    if not os.path.exists(get_detail_script):
        print(f"  [错误] 未找到 get_ticket_detail.py")
        sys.exit(1)

    try:
        result = subproc.run(
            [sys.executable, get_detail_script, ticket_key, '--json'],
            capture_output=True, text=True, timeout=30,
            cwd=jira_access_dir
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        else:
            print(f"  [错误] 获取JIRA失败: {result.stderr[:100] if result.stderr else 'unknown'}")
            return {}
    except Exception as e:
        print(f"  [错误] {e}")
        return {}


def format_jira_for_analysis(jira_context: dict) -> str:
    """将JIRA信息格式化为分析用文本"""
    if not jira_context:
        return "无可用JIRA信息"

    lines = []
    all_fields = jira_context.get('all_fields', {})

    lines.append(f"## 问题ID: {jira_context.get('key', 'N/A')}")

    summary = jira_context.get('summary', 'N/A')
    lines.append(f"## 标题: {summary}")

    issue_analysis = all_fields.get('customfield_20765', {})
    if isinstance(issue_analysis, dict):
        issue_analysis = issue_analysis.get('value', '')
    if issue_analysis:
        issue_analysis = re.sub(r'\s+', ' ', str(issue_analysis)).strip()
        if len(issue_analysis) > 500:
            issue_analysis = issue_analysis[:500] + '...'
        lines.append(f"## Issue Analysis: {issue_analysis}")

    raw_desc = jira_context.get('description', '')
    if isinstance(raw_desc, dict):
        desc_text = ""
        for block in raw_desc.get('content', []):
            for content_item in block.get('content', []):
                desc_text += content_item.get('text', '')
    else:
        desc_text = str(raw_desc) if raw_desc else ""

    if desc_text:
        lines.append(f"## 问题描述:\n{desc_text[:2000]}")

    comments = jira_context.get('comments', [])
    if comments:
        lines.append(f"## 历史评论({len(comments)}条):")
        for c in comments[:10]:
            author = c.get('author', {}).get('displayName', 'Unknown')
            body = c.get('body', {})
            if isinstance(body, dict):
                body_text = ''
                for block in body.get('content', []):
                    for item in block.get('content', []):
                        body_text += item.get('text', '') + ' '
                body = body_text[:300]
            created = c.get('created', '')[:10]
            lines.append(f"- [{created}] {author}: {body}")

    return '\n'.join(lines)


# ===== 知识库 =====
def load_knowledge_summary() -> str:
    """加载知识库摘要"""
    knowledge_dir = os.path.join(os.path.dirname(__file__), '..', 'knowledge')
    summary_file = os.path.join(knowledge_dir, '00_索引.md')

    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            return f.read()[:3000]
    return ""


# ===== AI 调用 =====
def call_opencode(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """调用opencode AI"""
    cli = r'C:\Users\WP6KCF2\AppData\Roaming\npm\opencode.ps1'

    ps_script = f'''
$prompt = @"
{prompt}
"@
$result = & "{cli}" -p $prompt 2>&1
Write-Output $result
'''

    try:
        result = subproc.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True, text=True, timeout=300
        )
        return result.stdout if result.returncode == 0 else f"[AI调用失败: {result.stderr[:200]}]"
    except Exception as e:
        return f"[AI异常: {e}]"


# ===== Hypothesis Generator =====
def _parse_hypotheses_from_text(response: str, jira_info: str) -> Dict:
    """从自然语言文本中解析假设
    
    假设来源分析：
    - AI prompt 喂入了完整的 JIRA 信息（标题 + Issue Analysis + 描述 + 评论）
    - AI 分析这些内容后生成假设
    - 当 AI 返回文本格式时，正则解析假设列表
    - 兜底时：基于 JIRA 标题中的关键词 + 领域知识库映射生成假设
    """
    hyps = []
    understanding = ""
    likely_side = ""

    m = re.search(r'问题理解[:：]\s*(.+)', response)
    if m:
        understanding = m.group(1).strip()
    else:
        m = re.search(r'本质[:：]\s*(.+)', response)
        if m:
            understanding = m.group(1).strip()
        else:
            m = re.search(r'理解[:：]\s*(.+)', response)
            if m:
                understanding = m.group(1).strip()

    if not understanding:
        for kw in ['预置证书', '激活失败', '无法激活', '蓝牙钥匙', '配对', '签名无效', '数字钥匙']:
            if kw in jira_info and kw in response:
                understanding = f"JIRA中提及「{kw}」，分析其根因"
                break

    for side in ['车企后台', '车端', '手机端', '苹果后台', '未知']:
        if side in response:
            likely_side = side
            break

    lines = response.split('\n')
    current_hyp = None
    for line in lines:
        line = line.strip()
        m = re.match(r'^假设(\d+)[:：](.+)', line)
        if m:
            if current_hyp and current_hyp.get('description'):
                hyps.append(current_hyp)
            current_hyp = {
                'id': int(m.group(1)),
                'description': m.group(2).strip(),
                'keywords': [],
                'reasoning': '',
                'searched': False,
                'evidence': [],
                'status': 'pending'
            }
            continue
        if current_hyp:
            m_kw = re.match(r'关键词[:：]\s*(.+)', line)
            if m_kw:
                kws = re.split(r'[,，]', m_kw.group(1))
                current_hyp['keywords'] = [k.strip() for k in kws if k.strip()]
                continue
            m_rsn = re.match(r'理由[:：](.+)', line)
            if m_rsn:
                current_hyp['reasoning'] = m_rsn.group(1).strip()
                continue

    if current_hyp and current_hyp.get('description'):
        hyps.append(current_hyp)

    if not hyps:
        key_map = {
            '预置证书': ['factory/certificate/preset', 'certificate/preset', 'vehicleCert', 'ccc preset', 'ble preset', '预置证书', 'preset============================'],
            'KTS服务': ['KTS request', 'KTS response', 'KTS', 'TrustResult', 'CheckIDS', 'CheckIDSRegistration'],
            '后台API': ['pretrack', 'trackKey', 'backend', 'ABR', 'HTTP error', '404', '500', '400'],
            '车端NFC': ['cccop', 'NFC_iN', 'getdata_rsp sw=', 'cccparse', 'sw=0x6400', 'NFC_oN', 'ecp['],
            '车端BLE': ['recv_cb error', 'NotifyToVeh error', 'bleERROR', 'disconnected,reason=', 'BLE', 'bluetooth'],
            '钥匙分享': ['sharing', 'friend', 'invite', 'ShareKey', 'ktIDSPV2'],
            '通用错误': ['error', 'fail', 'Exception', 'CRASH', 'ANR', 'FATAL', 'failed'],
        }

        if '预置证书' in jira_info or 'preset' in jira_info.lower():
            hyps.append({
                'id': 1,
                'description': '后台预置证书问题',
                'keywords': key_map['预置证书'],
                'reasoning': 'JIRA标题明确提到"车辆无法预置证书"',
                'searched': False,
                'evidence': [],
                'status': 'pending'
            })

        if 'KTS' in jira_info or '远程服务' in jira_info:
            hyps.append({
                'id': 2,
                'description': '车企后台KTS服务问题',
                'keywords': key_map['KTS服务'],
                'reasoning': '评论中提到"调用远程服务失败"',
                'searched': False,
                'evidence': [],
                'status': 'pending'
            })

        hyps.append({
            'id': len(hyps) + 1,
            'description': '车端NFC/SE问题',
            'keywords': key_map['车端NFC'],
            'reasoning': '预置证书失败可能与车端SE applet状态有关',
            'searched': False,
            'evidence': [],
            'status': 'pending'
        })

        hyps.append({
            'id': len(hyps) + 1,
            'description': '车企后台API调用问题',
            'keywords': key_map['后台API'],
            'reasoning': '预置证书依赖后台API下发',
            'searched': False,
            'evidence': [],
            'status': 'pending'
        })

        hyps.append({
            'id': len(hyps) + 1,
            'description': 'APP层崩溃/异常',
            'keywords': key_map['通用错误'],
            'reasoning': '日志中存在Android crash/anr系统错误',
            'searched': False,
            'evidence': [],
            'status': 'pending'
        })

        if not likely_side:
            likely_side = '车企后台'

        if not understanding:
            understanding = 'JIRA描述手机蓝牙钥匙激活失败，提示预置证书异常'

    return {
        'understanding': understanding[:200],
        'likely_side': likely_side,
        'hypotheses': hyps[:5]
    }


def generate_hypotheses(jira_info: str, knowledge: str, available_logs: List[Dict]) -> Dict:
    """根据JIRA信息生成排查假设

    Returns:
        {
            'understanding': '问题理解',
            'likely_side': '最可能故障端',
            'hypotheses': [...]
        }
    """
    log_summary = "\n".join([f"- {f['path']} ({f['size_str']})" for f in available_logs[:30]])

    prompt = f"""你是CCC CarKey数字钥匙故障排查专家。

## 当前任务
根据JIRA信息，分析问题本质，列出排查假设。

## JIRA信息
{jira_info}

## 知识库摘要
{knowledge}

## 可用日志文件(部分)
{log_summary}

## 分析要求
1. 仔细阅读JIRA标题、Issue Analysis、操作步骤和评论
2. 理解问题的本质是什么（是预置证书未下发？还是证书下发后激活失败？）
3. 判断最可能的故障端（手机端/车端/车企后台/苹果后台）
4. 列出3-5个排查假设，每个假设包含：
   - 假设描述（如：后台未下发预置证书）
   - 搜索关键词（用于在日志中搜索验证该假设）
   - 提出该假设的理由

## 输出格式
问题理解: [一句话描述问题本质]
最可能故障端: [手机端/车端/车企后台/苹果后台/未知]

假设1: [描述]
  关键词: [kw1], [kw2], [kw3]
  理由: [为什么提出这个假设]

假设2: [描述]
  关键词: [kw1], [kw2]
  理由: [...]

[以此类推3-5个假设]

只输出分析结果，不要其他内容。
"""

    response = call_opencode(prompt)
    result = _parse_hypotheses_from_text(response, jira_info)

    if not result['hypotheses']:
        result['hypotheses'] = [{
            'id': 1,
            'description': '通用故障排查',
            'keywords': ['error', 'fail', 'exception', 'carkey', 'pairing'],
            'reasoning': '默认假设',
            'searched': False,
            'evidence': [],
            'status': 'pending'
        }]

    return result


# ===== Agent Loop =====
def agent_loop(hypothesis_data: Dict, log_tool: LogTool, max_rounds: int = 3) -> Dict:
    """Agent循环：搜索验证假设

    流程:
    - Round 1: 搜索所有假设的关键词
    - Round 2: 读取证据片段，分析收敛或扩大搜索
    - Round 3: 最终收敛判断
    - 收敛条件: 找到明确证据指向单一故障端，或确认日志不足
    """
    hypotheses = hypothesis_data['hypotheses']
    round_num = 0
    all_keywords_searched = set()

    while round_num < max_rounds:
        round_num += 1
        print(f"  [Round {round_num}] 搜索验证...")

        if round_num == 1:
            pending_hypotheses = [h for h in hypotheses if not h['searched']]
        else:
            pending_hypotheses = [h for h in hypotheses]

        all_keywords = []
        for h in pending_hypotheses:
            for kw in h.get('keywords', []):
                if kw not in all_keywords_searched:
                    all_keywords.append(kw)

        unique_keywords = list(set(all_keywords))[:15]

        grep_results = log_tool.grep_logs(unique_keywords, max_results_per_pattern=30)

        for kw in unique_keywords:
            all_keywords_searched.add(kw)

        for h in hypotheses:
            if h['searched'] and round_num == 1:
                continue
            h['searched'] = True
            h_keywords = h.get('keywords', [])
            evidence = []
            evidence_files = {}

            for kw in h_keywords:
                matches = grep_results.get(kw, [])
                for m in matches[:10]:
                    f = m['file']
                    if f not in evidence_files:
                        evidence_files[f] = []
                    m_with_kw = dict(m)
                    m_with_kw['keyword'] = kw
                    evidence_files[f].append(m_with_kw)

            for f, matches in evidence_files.items():
                for m in matches[:5]:
                    evidence.append({
                        'keyword': m['keyword'],
                        'file': f,
                        'line_no': m['line_no'],
                        'content': m['content']
                    })

            h['evidence'] = evidence
            h['status'] = 'has_evidence' if evidence else 'no_evidence'

        all_evidence = {h['id']: {'desc': h.get('description', ''), 'evidence': h.get('evidence', [])} for h in hypotheses}

        total_evidence = sum(len(h['evidence']) for h in hypotheses)
        no_evidence_count = sum(1 for h in hypotheses if not h['evidence'])

        if round_num == 1 and no_evidence_count == len(hypotheses):
            print(f"  [Round 1] 所有假设均无证据，尝试扩展搜索关键词...")
            extra_kws = ['数字钥匙', 'carkey', 'digitalkey', 'Bluetooth', 'BLE', 'NFC', '配对', 'pairing', '钥匙', 'key']
            extra_results = log_tool.grep_logs(extra_kws, max_results_per_pattern=20)
            for kw, matches in extra_results.items():
                for h in hypotheses:
                    if kw in h.get('keywords', []):
                        continue
                    for m in matches[:5]:
                        h['evidence'].append({
                            'keyword': kw,
                            'file': m.get('file', ''),
                            'line_no': m.get('line_no', 0),
                            'content': m.get('content', '')
                        })
                    if h['evidence']:
                        h['status'] = 'has_evidence'
            continue

        if round_num >= 2 or total_evidence > 0:
            has_strong_evidence = any(
                h['evidence'] and any(
                    ekw in ['error', 'fail', 'sw=', 'Exception', 'CRASH', 'ANR', 'http', 'HTTP']
                    for e in h['evidence']
                    for ekw in [e.get('keyword', '').lower()]
                )
                for h in hypotheses
            )

            if has_strong_evidence:
                best_h = max(hypotheses, key=lambda h: len(h.get('evidence', [])))
                print(f"  [收敛] 假设「{best_h['description']}」有明确证据")
                evidence_summary = f"找到 {len(best_h['evidence'])} 条证据，主要关键词: {best_h.get('keywords', [])[0]}"
                return {
                    'converged': True,
                    'conclusion': f"故障端: {best_h['description']}。{evidence_summary}",
                    'hypothesis_id': best_h['id'],
                    'evidence_summary': evidence_summary,
                    'all_hypotheses': hypotheses
                }

            if round_num >= max_rounds:
                print(f"  [达到最大轮数] 无明确证据收敛")
                break

            if total_evidence == 0 and round_num >= 2:
                print(f"  [收敛] 无证据，判定为日志不足")
                break

    best_h = max(hypotheses, key=lambda h: len(h.get('evidence', [])))
    if best_h.get('evidence'):
        return {
            'converged': False,
            'partial_conclusion': f"假设「{best_h['description']}」有部分证据但不足以确定",
            'all_hypotheses': hypotheses
        }

    return {
        'converged': False,
        'all_hypotheses': hypotheses
    }


# ===== 报告生成 =====
def generate_report(ticket_key: str, jira_info: str, hypothesis_result: Dict, log_tool: LogTool) -> str:
    """生成7章节结构化报告"""

    hypotheses = hypothesis_result.get('all_hypotheses', [])

    lines = []
    lines.append(f"# {ticket_key} 完整分析报告")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 一、JIRA 信息")
    lines.append("")
    lines.append(jira_info)

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 二、分析结论")

    if hypothesis_result.get('converged'):
        lines.append(f"**【确定】** {hypothesis_result.get('conclusion', '')}")
    else:
        lines.append("**【待定】** 经过多轮搜索，未能收敛到明确结论")
        lines.append("")
        lines.append("### 假设状态汇总")
        for h in hypotheses:
            status_icon = "✅" if h.get('evidence') else "❌"
            lines.append(f"- {status_icon} {h.get('description', '')} ({h.get('status', '')})")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 三、证据链详情")

    for h in hypotheses:
        if h.get('evidence'):
            lines.append(f"### 假设: {h.get('description', '')}")
            lines.append("")
            evidence_by_file = {}
            for e in h['evidence'][:20]:
                f = e['file']
                if f not in evidence_by_file:
                    evidence_by_file[f] = []
                evidence_by_file[f].append(e)

            for f, evs in evidence_by_file.items():
                lines.append(f"**{f}**")
                for e in evs[:5]:
                    lines.append(f"  - L{e['line_no']}: {e['content'][:150]}")
                lines.append("")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 四、故障链条总结")

    if hypothesis_result.get('converged'):
        lines.append("基于证据链，定位故障端为: " + hypothesis_result.get('conclusion', '未知'))
    else:
        lines.append("未能形成完整的故障链条，需要更多信息")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 五、整改建议")

    if hypothesis_result.get('converged'):
        lines.append("| 归属端 | 建议措施 |")
        lines.append("|--------|----------|")
        lines.append("| 待确认 | 根据结论补充建议 |")
    else:
        lines.append("| 归属端 | 建议措施 |")
        lines.append("|--------|----------|")
        lines.append("| 待排查 | 建议补充日志后重新分析 |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 六、日志完整性评估")

    all_logs = log_tool.list_logs()
    lines.append(f"可用日志文件: {len(all_logs)}个")
    categories = {'ios': 0, 'android': 0, 'vehicle': 0, 'backend': 0, 'unknown': 0}
    for f in all_logs:
        p = f['path'].lower()
        if 'security-sysdiagnose' in p or 'ios' in p:
            categories['ios'] += 1
        elif 'android' in p or 'logcat' in p:
            categories['android'] += 1
        elif any(x in p for x in ['.asc', '.blf', 'can', 'dbc']):
            categories['vehicle'] += 1
        elif 'backend' in p or 'log' in p:
            categories['backend'] += 1
        else:
            categories['unknown'] += 1

    lines.append(f"- iOS日志: {categories['ios']}个")
    lines.append(f"- Android日志: {categories['android']}个")
    lines.append(f"- 车端日志: {categories['vehicle']}个")
    lines.append(f"- 后台日志: {categories['backend']}个")

    log_grade = 'D级'
    if categories['ios'] > 0 and categories['backend'] > 0:
        log_grade = 'B级'
    elif categories['ios'] > 0 or categories['android'] > 0:
        log_grade = 'C级'

    lines.append(f"**完整性等级: {log_grade}**")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 七、结论")

    if hypothesis_result.get('converged'):
        lines.append(f"根据Agent多轮搜索验证，结论为: {hypothesis_result.get('conclusion', '')}")
    else:
        lines.append("当前日志不足以支撑明确结论，建议:")
        lines.append("1. 补充车端dk_service.log")
        lines.append("2. 补充车企后台Pretrack/KTS日志")
        lines.append("3. 提供更精确的问题时间点")

    return '\n'.join(lines)


# ===== 预处理：解压附件 + 复制非压缩文件 =====
def preprocess_extraction(ticket_dir: str) -> int:
    """解压未完成的附件，复制非压缩文件

    逻辑:
    1. 先扫描 extracted/ 已有哪些目录/文件（已解压的标记）
    2. 识别附件中的分卷压缩包组（.001/.002... + -1.001等）
    3. 分卷组只需解压第一个(.001)，7z会自动识别
    4. 对于分卷：只解压.001，跳过同组的.002/.003
    5. 对于普通zip：直接解压
    6. 对于非压缩文件(.txt/.blf/.asc/.log)：复制到extracted/
    7. 跳过图片/视频/markdown

    Returns: 新增文件数量
    """
    import shutil
    import zipfile
    import tarfile

    attachments_dir = os.path.join(ticket_dir, 'Attachments')
    extracted_dir = os.path.join(ticket_dir, 'extracted')
    os.makedirs(extracted_dir, exist_ok=True)

    if not os.path.exists(attachments_dir):
        return 0

    seven_zip = None
    for path in [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]:
        if os.path.exists(path):
            seven_zip = path
            break

    existing_dirs = set(os.listdir(extracted_dir))
    existing_files = set()
    for root, dirs, files in os.walk(extracted_dir):
        for f in files:
            existing_files.add(os.path.join(root, f).lower())

    files_to_process = os.listdir(attachments_dir)

    split_archives = {}
    for fname in files_to_process:
        if fname.endswith('.001'):
            base = fname[:-4]
            if base not in split_archives:
                split_archives[base] = []
            split_archives[base].append(fname)

    handled_bases = set()
    new_files = 0

    for fname in files_to_process:
        att_path = os.path.join(attachments_dir, fname)

        ext_lower = os.path.splitext(fname)[1].lower()
        fname_lower = fname.lower()

        if fname_lower.endswith('.mp4') or fname_lower.endswith('.jpg') or fname_lower.endswith('.png') or fname_lower.endswith('.md'):
            continue

        if any(ord(c) > 127 for c in fname) and any(kw in fname_lower for kw in ['blf', 'mp4', 'jpg', 'png']):
            continue

        if fname.endswith('.001'):
            base = fname[:-4]
            if base in handled_bases:
                continue
            handled_bases.add(base)

            archive_name = base.split('.')[0] if '.' in base else base
            if archive_name.lower() in existing_dirs:
                print(f"  [跳过] {fname} ({archive_name}/ 已存在)")
                continue

            print(f"  [分卷解压] {base}.xxx ({len(split_archives.get(base, []))} 卷)")
            if seven_zip:
                first_part = att_path
                if os.path.exists(first_part):
                    try:
                        result = subproc.run(
                            [seven_zip, 'x', first_part, f'-o{extracted_dir}', '-y'],
                            capture_output=True, text=True, timeout=600
                        )
                        if result.returncode == 0:
                            print(f"    [OK] {base}")
                        else:
                            print(f"    [失败] {result.stderr[:150] if result.stderr else 'unknown'}")
                    except Exception as e:
                        print(f"    [异常] {e}")
            continue

        if fname.endswith('.002') or fname.endswith('.003') or fname.endswith('.004'):
            for base in list(handled_bases):
                if base.startswith(fname[:-4]):
                    print(f"  [跳过] {fname} (属于 {base})")
                    continue

        if fname.endswith('.zip'):
            zip_name = fname[:-4].strip()
            zip_basename = zip_name.split('/')[-1].strip()
            possible_dirs = {d.lower() for d in existing_dirs}
            already_extracted = (
                zip_name.lower() in possible_dirs or
                zip_basename.lower() in possible_dirs or
                any(zip_basename.lower() in d.lower() for d in existing_dirs)
            )

            if already_extracted:
                print(f"  [跳过] {fname} (已解压)")
                continue

            try:
                with zipfile.ZipFile(att_path, 'r') as zf:
                    entries = zf.namelist()
                    top_level_dirs = set()
                    for entry in entries:
                        parts = entry.strip('/').split('/')
                        if len(parts) > 1:
                            top_level_dirs.add(parts[0])
                        elif len(parts) == 1 and '.' not in parts[0]:
                            top_level_dirs.add(parts[0])

                    top_dir_match = any(d.lower() in possible_dirs for d in top_level_dirs)
                    if top_dir_match:
                        print(f"  [跳过] {fname} (内容已存在)")
                        continue
            except:
                pass

            print(f"  [解压] {fname}")
            extracted = False
            if seven_zip:
                try:
                    result = subproc.run(
                        [seven_zip, 'x', att_path, f'-o{extracted_dir}', '-y'],
                        capture_output=True, text=True, timeout=600
                    )
                    if result.returncode == 0:
                        print(f"    [OK] 7-Zip")
                        extracted = True
                        new_files += 1
                    else:
                        print(f"    [7-Zip失败，尝试Python...]")
                except subprocess.TimeoutExpired:
                    print(f"    [7-Zip超时，跳过]")
                    continue
                except Exception as e:
                    print(f"    [7-Zip异常: {str(e)[:50]}，尝试Python...]")

            if not extracted:
                try:
                    with zipfile.ZipFile(att_path, 'r') as zf:
                        for name in zf.namelist():
                            try:
                                zf.extract(name, extracted_dir)
                                new_files += 1
                            except:
                                pass
                    print(f"    [OK] Python zipfile")
                except Exception as e:
                    print(f"    [失败] {e}")
            continue

        if fname.endswith('.tar'):
            print(f"  [解压] {fname}")
            try:
                with tarfile.open(att_path, 'r') as tf:
                    for member in tf.getmembers():
                        if member.isfile():
                            dest_path = os.path.join(extracted_dir, member.name)
                            if not os.path.exists(dest_path):
                                tf.extract(member, extracted_dir)
                                new_files += 1
                    print(f"    [OK]")
            except Exception as e:
                print(f"    [失败] {e}")
            continue

        if ext_lower in ['.txt', '.blf', '.asc', '.log']:
            dest = os.path.join(extracted_dir, fname)
            if not os.path.exists(dest):
                shutil.copy2(att_path, dest)
                new_files += 1
                print(f"  [复制] {fname}")
            else:
                print(f"  [跳过] {fname} (已存在)")
            continue

    return new_files


# ===== 日志清洗：AI预处理 =====
def _ai_clean_single_file(file_path: str, rel_path: str, model: str = DEFAULT_MODEL) -> List[str]:
    """AI分析日志文件，保留数字钥匙相关内容"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        total_lines = len(lines)
        if total_lines <= 2000:
            sample_lines = lines
        else:
            sample_lines = lines[:1000] + lines[total_lines//2-500:total_lines//2+500]

        sample_text = '\n'.join(l.rstrip() for l in sample_lines[:300])

        prompt = f"""你是CCC CarKey数字钥匙日志分析专家。请分析以下日志文件样本，判断哪些行与数字钥匙相关。

## 日志文件: {rel_path}
## 总行数: {total_lines}

## 日志样本(前300行):
{sample_text}

## 任务
1. 分析这个日志的格式和内容类型（哪些是数字钥匙相关，哪些是系统/其他APP/无关内容）
2. 识别数字钥匙相关的关键词和模式（如 carkey, CCC, NFC, BLE, pairing, KTS, certificate, SE, 预置证书 等）
3. 识别需要过滤的无关模式（如纯音频、UI渲染、第三方APP等系统噪音）
4. 输出JSON格式的过滤规则

## 输出格式
```json
{{
  "include_patterns": ["关键词1", "关键词2"],
  "exclude_patterns": ["无关模式1", "无关模式2"],
  "summary": "日志内容概括"
}}
```
只输出JSON，不要其他内容。
"""
        response = call_opencode(prompt, model=model)

        include_kws = []
        exclude_kws = []
        try:
            data = json.loads(response)
            include_kws = data.get('include_patterns', [])
            exclude_kws = data.get('exclude_patterns', [])
        except:
            include_kws = ['carkey', 'CCC', 'NFC', 'BLE', 'pairing', '配对', 'KTS',
                          'digitalkey', 'certificate', 'SE', 'UWB', 'pretrack',
                          'trackKey', 'TrustResult', 'CheckIDS', 'cccop', 'vehicleCert',
                          'preset', 'dk_service', '数字钥匙']
            exclude_kws = []

        include_lower = [kw.lower() for kw in include_kws]
        exclude_lower = [kw.lower() for kw in exclude_kws]

        filtered = []
        for line in lines:
            line_lower = line.lower()
            if exclude_lower and any(kw in line_lower for kw in exclude_lower):
                continue
            if any(kw in line_lower for kw in include_lower):
                filtered.append(line.rstrip())
            elif len(filtered) > 0 and len(filtered) < 5000:
                pass

        if not filtered:
            filtered = [l.rstrip() for l in lines[:5000]]

        return filtered

    except Exception as e:
        return []


def clean_logs(log_tool: LogTool, debug: bool = False) -> Dict[str, int]:
    """使用AI清洗日志，只保留数字钥匙相关内容

    Args:
        log_tool: LogTool实例
        debug: 是否落库到cleaned/目录

    Returns:
        {rel_path: kept_line_count} 清洗后保留的行数
    """
    files = log_tool.list_logs()

    dk_files = [f for f in files if any(k in f['path'].lower() for k in ['dk_service', 'tboxapp', 'tboxapp.exe'])]
    dk_files.sort(key=lambda f: (0 if f['path'].lower() == 'dk_service.log' or f['path'].lower().endswith('dk_service.log') else 1, f['path']))
    mixed_files = [f for f in files if f not in dk_files and f['size'] > 500 * 1024]

    dk_to_skip_clean = dk_files[:5]
    mixed_to_clean = mixed_files[:3]

    if not dk_to_skip_clean and not mixed_to_clean:
        return {}

    print(f"  检查日志: {len(dk_to_skip_clean)} 个专项日志 + {len(mixed_to_clean)} 个待清洗")

    cleaned_stats = {}

    for f in dk_to_skip_clean:
        rel = f['path']
        try:
            with open(os.path.join(log_tool.extracted_dir, rel), 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()
            log_tool._cleaned_content[rel] = [l.rstrip() for l in lines]
            cleaned_stats[rel] = len(lines)
            print(f"    {rel}: {len(lines)} 行 (专项日志，不清洗)")
        except:
            pass

    for f in mixed_to_clean:
        fp = os.path.join(log_tool.extracted_dir, f['path'])
        rel = f['path']
        total_lines = 0

        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as file:
                total_lines = len(file.readlines())
        except:
            pass

        print(f"    {rel}: {total_lines} 行 -> AI清洗中...", end='', flush=True)
        t0 = time.time()

        filtered = _ai_clean_single_file(fp, rel)

        if filtered:
            log_tool._cleaned_content[rel] = filtered
            cleaned_stats[rel] = len(filtered)
            print(f" {total_lines} -> {len(filtered)} 行 ({time.time()-t0:.1f}s)")
        else:
            print(f" 清洗失败，保留原始")

    if debug and cleaned_stats:
        cleaned_dir = os.path.join(os.path.dirname(log_tool.extracted_dir), 'cleaned')
        os.makedirs(cleaned_dir, exist_ok=True)
        for rel, lines in log_tool._cleaned_content.items():
            clean_path = os.path.join(cleaned_dir, f"{rel}_cleaned.log")
            os.makedirs(os.path.dirname(clean_path), exist_ok=True)
            with open(clean_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        print(f"     [Debug] 清洗结果已落库: cleaned/")

    return cleaned_stats


# ===== 主入口 =====
def main(ticket_key: str, work_dir: str = r"Y:\JIRA_Logs", debug: bool = False):
    print(f"\n{'='*50}")
    print(f"Agentic 分析: {ticket_key}")
    print(f"{'='*50}")

    ticket_dir = os.path.join(work_dir, ticket_key)
    extracted_dir = os.path.join(ticket_dir, 'extracted')

    print("  0. 预处理：解压附件 + 复制非压缩文件...")
    t_prep = time.time()
    new_count = preprocess_extraction(ticket_dir)
    if new_count > 0:
        print(f"     新增 {new_count} 个文件，耗时 {time.time()-t_prep:.1f}s")
    else:
        print(f"     无新增文件，耗时 {time.time()-t_prep:.1f}s")
    output_dir = os.path.join(ticket_dir, '分析过程')
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(extracted_dir):
        print(f"  [错误] 日志目录不存在: {extracted_dir}")
        sys.exit(1)

    t0 = time.time()

    print("  1. 加载JIRA信息...")
    jira_context = load_jira_context(ticket_key)
    jira_info = format_jira_for_analysis(jira_context)
    print(f"     JIRA信息已加载")

    print("  2. 扫描可用日志...")
    log_tool = LogTool(extracted_dir)
    available_logs = log_tool.list_logs()
    print(f"     找到 {len(available_logs)} 个日志文件")

    print("  3. 日志清洗（AI预处理）...")
    t_clean = time.time()
    cleaned_stats = clean_logs(log_tool, debug=debug)
    if cleaned_stats:
        total_kept = sum(cleaned_stats.values())
        print(f"     清洗完成: {len(cleaned_stats)} 个文件，保留 {total_kept} 行，耗时 {time.time()-t_clean:.1f}s")
    else:
        print(f"     无需清洗，耗时 {time.time()-t_clean:.1f}s")

    print("  4. 加载知识库...")
    knowledge = load_knowledge_summary()
    print(f"     知识库已加载")

    print("  5. 生成排查假设...")
    hypothesis_data = generate_hypotheses(jira_info, knowledge, available_logs)
    print(f"     生成 {len(hypothesis_data['hypotheses'])} 个假设")
    print(f"     问题理解: {hypothesis_data['understanding'][:100]}")
    print(f"     可能故障端: {hypothesis_data['likely_side']}")
    for h in hypothesis_data['hypotheses'][:3]:
        print(f"       - {h.get('title', str(h))}")

    print("  6. Agent循环搜索...")
    if 'rounds' in result:
        for round_detail in result['rounds']:
            rnum = round_detail.get('round', '?')
            action = round_detail.get('action', '')
            res = round_detail.get('result', '')
            print(f"     [Round {rnum}] {action} | {res}")
            for ev in round_detail.get('evidence', [])[:3]:
                print(f"       证据: {ev.get('file','')} L{ev.get('line_no','')}: {ev.get('content','')[:120]}")
    else:
        print(f"     [收敛] {result.get('conclusion', '')}")
        print(f"     关键发现: {str(result)[:300]}")

    print("  6. Agent循环搜索...")
    result = agent_loop(hypothesis_data, log_tool, max_rounds=3)

    print("  7. 生成报告...")
    report = generate_report(ticket_key, jira_info, result, log_tool)

    print(f"\n{'='*60}")
    print("报告内容:")
    print(f"{'='*60}")
    print(report)

    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    report_path = os.path.join(output_dir, f"{ticket_key}_Agent分析报告_{ts}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n[完成] 报告已打印上方并保存: {report_path}")
    print(f"[耗时] {time.time() - t0:.1f}s")

    print("  8. 发送邮件...")
    summary = jira_context.get('summary', '')[:50] if jira_context else ''
    send_email(f"Agent分析 - {ticket_key}", report, ticket_key=ticket_key, ticket_summary=summary)

    return report_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python analyze_agentic.py <JIRA号> [--debug]")
        sys.exit(1)
    ticket = sys.argv[1]
    debug = '--debug' in sys.argv
    main(ticket, debug=debug)
