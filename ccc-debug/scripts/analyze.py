#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
CCC CarKey Debug 分析引擎
属于 ccc-debug skill,负责日志分析全流程:
1. 日志类型识别 (classify_logs)
2. 关键词匹配分析 (read_ios_logs / read_android_logs / analyze_backend_logs)
3. 故障分类 (classify_fault)
4. 报告生成 (generate_report)
5. AI 深度分析 (run_ai_analysis)

输出: Y:\JIRA_Logs\{ticket_key}\分析过程\{ticket_key}_完整分析报告.md + {ticket_key}_规则分析报告.md
"""
import os
import sys
import glob
import re
import json
import subprocess as subproc
import zipfile
import tarfile
import tempfile
from datetime import datetime
import time

# AI 模型配置
DEFAULT_MODEL = "LiteLLM/MiniMax-M2.5"

def _ensure_complete_sections(report_text, jira_context=None):
    SECTION_NORM = [
        ('一', '## 一、JIRA 信息'),
        ('二', '## 二、分析结论'),
        ('三', '## 三、关键日志片段'),
        ('四', '## 四、根因分析'),
        ('五', '## 五、整改建议'),
        ('六', '## 六、补充说明'),
        ('七', '## 七、结论'),
    ]
    SECTION_PLACEHOLDERS = {
        '一': '[JIRA 信息见上方]',
        '二': '[分析结论待补充]',
        '三': '[关键日志待补充]',
        '四': '[根因分析见第二章]',
        '五': '[整改建议待补充]',
        '六': '[补充说明见其他章节]',
        '七': '[结论见以上分析]',
    }
    HEADING_NORM_PATTERNS = [
        (r'^(#{1,6})\s+.*?(JIRA|jira).*$', '## 一、JIRA 信息'),
        (r'^(#{1,6})\s+.*?(分析结论).*$', '## 二、分析结论'),
        (r'^(#{1,6})\s+.*?(关键日志|日志片段|证据链).*$', '## 三、关键日志片段'),
        (r'^(#{1,6})\s+.*?(根因|故障链条|故障分析).*$', '## 四、根因分析'),
        (r'^(#{1,6})\s+.*?(整改建议|修复建议).*$', '## 五、整改建议'),
        (r'^(#{1,6})\s+.*?(补充说明|日志完整性).*$', '## 六、补充说明'),
        (r'^(#{1,6})\s+.*?(结论).*$', '## 七、结论'),
    ]

    lines = report_text.split('\n')

    section_starts = {}
    section_content = {}
    current_section = None
    current_content = []
    for i, line in enumerate(lines):
        is_heading = False
        normalized_ch = None
        for ch, std in SECTION_NORM:
            if line.strip() == std:
                is_heading = True
                normalized_ch = ch
                break
        if is_heading and normalized_ch:
            if current_section:
                section_content[current_section] = current_content
            current_section = normalized_ch
            section_starts[normalized_ch] = i
            current_content = [line]
        elif current_section:
            current_content.append(line)
        else:
            pass
    if current_section:
        section_content[current_section] = current_content

    existing = set(section_starts.keys())
    missing = [ch for ch, _ in SECTION_NORM if ch not in existing]
    if not missing:
        return report_text

    print(f"    [修复] 章节缺失，补充章节: {missing}")

    result_lines = []
    for ch, std in SECTION_NORM:
        if ch in section_content:
            result_lines.extend(section_content[ch])
        else:
            result_lines.append(std)
            result_lines.append(SECTION_PLACEHOLDERS[ch])
            result_lines.append('')

    return '\n'.join(result_lines).strip()

def _timed(name, func, *args, **kwargs):
    t = time.time()
    result = func(*args, **kwargs)
    print(f"    [{name}] {time.time() - t:.1f}s")
    return result


def _ts():
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

def _write_with_latest(directory, basename, content):
    ts = _ts()
    name_no_ext = basename.rsplit('.', 1)[0]
    ext = basename.rsplit('.', 1)[1]
    ts_name = f"{name_no_ext}_{ts}.{ext}"
    latest_name = basename
    ts_path = os.path.join(directory, ts_name)
    latest_path = os.path.join(directory, latest_name)
    with open(ts_path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    with open(latest_path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    return ts_path, latest_path


OPENCODE_CLI = r'C:\Users\WP6KCF2\AppData\Roaming\npm\opencode.ps1'

EVIDENCE_ANNOTATIONS = {
    'nfc_ecp': {
        'label': 'NFC ECP 配置状态',
        'reasoning': '通过 NFC ECP 配置参数(cccop值)判断车端NFC工作模式是否正确.cccop=1为正常模式,cccop=2为只读模式.只读模式下无法写入安全区域,导致CCC配对失败.',
    },
    'se_error': {
        'label': 'SE芯片认证结果',
        'reasoning': '通过SE(安全芯片)返回的APDU状态码判断认证是否成功.sw=0x6400表示执行失败,通常由NFC固件配置错误(cccop=2)或SE Applet未激活导致.',
    },
    'ble_error': {
        'label': '蓝牙通信状态',
        'reasoning': '通过蓝牙通信错误日志判断BLE连接和通信是否正常.recv_cb error表示车端蓝牙接收异常,NotifyToVeh error表示车控指令下发失败.reason=62表示连接未建立/同步超时,属于手机端问题,非车端故障.',
    },
    'key_info': {
        'label': '钥匙位置与绑定状态',
        'reasoning': '通过钥匙定位数据和绑定关系判断钥匙是否被正确识别和定位.BleDirection为车内外判定依据,bindkeyid2mac error表示钥匙与手机MAC绑定关系丢失.',
    },
    'kts': {
        'label': 'KTS(密钥托管服务)状态',
        'reasoning': '通过KTS相关日志判断Apple身份服务通信是否正常.KTS timeout/fail表示车企后台KTS服务无响应,TrustResult异常表示证书链校验失败.',
    },
    'carkey': {
        'label': 'CarKey核心流程状态',
        'reasoning': '通过CarKey核心日志(如Owner Pairing,Passbook)判断数字钥匙全生命周期流程是否正常.',
    },
    'sharing': {
        'label': '钥匙分享状态',
        'reasoning': '通过Pretrack和分享相关日志判断跨设备钥匙分享流程是否正常.Pretrack 404表示分享服务端点配置错误.',
    },
    'error': {
        'label': '系统错误日志',
        'reasoning': '通过系统级错误日志(Exception,CRASH,ANR等)判断APP或服务是否异常退出,直接导致功能不可用.',
    },
    'pairing': {
        'label': '配对流程状态',
        'reasoning': '通过配对相关日志判断手机与车端建立安全连接的过程是否正常完成.',
    },
    'pairstatus': {
        'label': 'CCC NFC Pairstatus 状态',
        'reasoning': '通过Pairstatus值判断NFC配对当前在哪一阶段:0=init/1=writedata/2=getdata/3=phase3/4=paired.卡在某个阶段表示该阶段对应的步骤失败.',
    },
    'bluetooth': {
        'label': '蓝牙底层状态',
        'reasoning': '通过HCI/ACL底层蓝牙日志判断物理层连接是否建立成功.',
    },
    'digital_key': {
        'label': '数字钥匙协议状态',
        'reasoning': '通过数字钥匙协议层日志(BLE_Main_UWB_TOF,TBOX_DigitalKeyInfo)判断车端是否正确解析和响应钥匙信号.',
    },
    'nfc': {
        'label': 'NFC协议交互状态',
        'reasoning': '通过NFC APDU指令日志判断NFC刷卡过程中手机与车端的通信是否正常.',
    },
    'uwb': {
        'label': 'UWB定位状态',
        'reasoning': '通过UWB信号强度和TOF数据判断钥匙的精确位置是否在有效范围内.',
    },
    'can_id': {
        'label': 'CAN总线消息状态',
        'reasoning': '通过关键CAN ID消息(如0x283数字钥匙状态,0x21C解锁请求)判断车端各ECU之间的通信是否正常.',
    },
    'abx': {
        'label': '车企后台API状态',
        'reasoning': '通过后台HTTP响应日志判断车企服务端接口是否正常返回数据.code非200或超时应关注后台服务状态.',
    },
    'config': {
        'label': 'TBOX 环境配置',
        'reasoning': '通过TBOX NVRAM配置日志判断当前连接的服务器环境(UAT/Prod).环境配置错误会导致数字钥匙请求打到错误的服务器.',
    },
}


def _load_prompts():
    pf = os.path.join(os.path.dirname(__file__), 'prompts_cn.json')
    if os.path.exists(pf):
        with open(pf, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

ANALYSIS_REPORT_TEMPLATE = """# {ticket_key} 日志分析报告

> 生成时间: {timestamp}

---

{jira_info}

---

## 一,问题摘要

共发现 {finding_count} 个问题

{finding_summary}

---

## 二,证据详解

{log_snippets}

---

## 三,整改建议汇总

| 归属端 | 建议措施 |
|--------|----------|
{remediation}
"""

IOS_KEYWORDS = [
    ('kts', ['KTS', 'KTSEligibility', 'KTSMManager', 'CheckIDSRegistration', 'PinningEvent', 'TrustResult']),
    ('carkey', ['CarKey', 'digitalcarkey', 'Owner Pairing', 'passd', 'Passbook', 'CarKeyErrorCode']),
    ('sharing', ['Friend', 'Sharing', 'share', 'Pretrack', 'trackKey', 'ktIDSPV2', 'KTPrimaryAccount']),
    ('error', ['error', 'fail', '-365', '-395', 'TransparencyError', 'Octagon', 'attestation', 'Auth鉴权超时']),
    ('seid', ['SEID', 'CloudKit', 'CKError']),
]

ANDROID_KEYWORDS = [
    ('digital_key', ['数字钥匙', 'carkey', 'digitalkey', 'digital key', 'bluetooth', 'BLE', 'NFC', 'UWB']),
    ('error', ['FATAL', 'Exception', 'CRASH', 'ANR', 'died', 'failed', 'error']),
    ('pairing', ['pairing', 'Pair', '配对', '配对', '钥匙']),
    ('bluetooth', ['Bluetooth', 'bt_', 'BLE', 'btif', 'HCI', 'acl']),
    ('nfc', ['NFC', 'IsoDep', 'APDU', 'SELECT', 'AID']),
]

BACKEND_PATTERNS = [
    ('abx', ['ABR', 'KTS request', 'KTS response', 'pretrack', 'trackKey']),
    ('auth', ['certificate', 'provisioning', 'auth', 'token', 'session']),
    ('sharing', ['friend', 'sharing', 'invite']),
    ('http', ['400', '401', '403', '404', '500', '502', '503']),
    ('config', ['TBOX_ACCOUT_REQ_URL_PATH', 'URL_PATH', 'NVRAM_SET']),
]

VEHICLE_KEYWORDS = [
    ('uwb', ['12DD540', 'UWB', 'uwb', 'ranging', 'TOF', 'range', 'distance', 'anchor', 'uwbkey1']),
    ('pe_unlock', ['PEUnlock', 'PE_Unlock', 'PEunlock', 'UnlockReq', '0x625', '0x21C', '0x224']),
    ('digital_key', ['DigitalKey', 'digitalkey', 'TBOX', '0x283', 'PollSecurity', 'UnlockEnable']),
    ('can_id', [' 283 ', ' 625 ', ' 21C ', ' 224 ', ' 12DD5', '0x283', '0x625', '0x21C']),
    ('error', ['error', 'fail', 'timeout', 'Error', 'Fault', 'fail', 'Auth1失败']),
    ('rssi', ['RSSI', 'rssi', 'signal', 'BLE']),
    ('nfc_ecp', ['cccop', 'NFC_iN', 'NFC_oN', 'ecp[', 'getdata_rsp sw=', 'cccparse', 'ccc--bleERROR', 'ccc--bleParse_Notify', 'getdata_rsp error']),
    ('ble_error', ['disconnected,reason=', 'recv_cb error', 'NotifyToVeh error', 'bleERROR']),
    ('pairing', ['Pairstatus', 'pairing', 'pair']),
]


def list_extracted_files(extracted_dir):
    result = []
    if not os.path.exists(extracted_dir):
        return result
    for root, dirs, files in os.walk(extracted_dir):
        level = root.replace(extracted_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        result.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for file in files:
            size = os.path.getsize(os.path.join(root, file))
            if size > 1024 * 1024:
                size_str = f"{size / 1024 / 1024:.1f} MB"
            else:
                size_str = f"{size / 1024:.1f} KB"
            result.append(f"{subindent}{file} ({size_str})")
    return result


def classify_logs(extracted_dir):
    types = {'ios': [], 'vehicle': [], 'backend': [], 'android': [], 'unknown': []}
    if not os.path.exists(extracted_dir):
        return types
    for root, dirs, files in os.walk(extracted_dir):
        for file in files:
            fp = os.path.join(root, file)
            rel = os.path.relpath(fp, extracted_dir)
            if 'security-sysdiagnose' in file or 'logarchive' in file:
                types['ios'].append(rel)
            elif file.endswith(('.ASC', '.BLF', '.DBC', '.qasm', '.mdf')):
                types['vehicle'].append(rel)
            elif 'main.txt' in file or 'system.txt' in file or 'kernel.txt' in file or 'crash.txt' in file:
                types['android'].append(rel)
            elif file.endswith('.log') or 'trace' in file.lower() or 'backend' in file.lower():
                types['backend'].append(rel)
            elif file not in ['README.txt']:
                types['unknown'].append(rel)
    return types


def parse_log_time(line):
    """从日志行提取时间戳，返回 datetime 或 None"""
    import re
    from datetime import datetime
    patterns = [
        (r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', '%Y-%m-%d %H:%M:%S'),
        (r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', '%m-%d %H:%M:%S'),
        (r'(\d{2}:\d{2}:\d{2})', '%H:%M:%S'),
    ]
    for pat, fmt in patterns:
        m = re.search(pat, line)
        if m:
            try:
                ts_str = m.group(1)
                if len(ts_str.split('-')[0]) == 2:
                    ts_str = '2026-' + ts_str
                return datetime.strptime(ts_str, fmt)
            except:
                pass
    return None


def parse_time_range_from_str(jira_str):
    """从 JIRA context 字符串解析时间范围
    
    支持格式:
    - "2025/10/30 16:33-16:34" → (start_dt, end_dt, None)
    - "2025/10/30 16:33" → (start_dt, start_dt, 5)  # 默认 5 分钟窗口
    - "16:33-16:34" → (today 16:33, today 16:34, None)
    - 无时间 → (None, None, 15)
    
    返回: (start_datetime, end_datetime, default_window_minutes)
    """
    import re
    from datetime import datetime, timedelta
    
    if not jira_str:
        return None, None, 15
    
    # 匹配 "2025/10/30 16:33-16:34" 或 "2025/10/30 16:33"
    m = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+(\d{1,2}:\d{2})(?:-(\d{1,2}:\d{2}))?', jira_str)
    if m:
        date_str = m.group(1)
        time_start = m.group(2)
        time_end = m.group(3) or time_start
        
        try:
            start_dt = datetime.strptime(f"{date_str} {time_start}", "%Y/%m/%d %H:%M")
            if time_end != time_start:
                end_dt = datetime.strptime(f"{date_str} {time_end}", "%Y/%m/%d %H:%M")
            else:
                end_dt = start_dt + timedelta(minutes=1)  # 单时间点默认 1 分钟窗口
            return start_dt, end_dt, None
        except:
            pass
    
    # 匹配 "16:33-16:34" (无日期)
    m = re.search(r'^(\d{1,2}:\d{2})-(\d{1,2}:\d{2})', jira_str, re.MULTILINE)
    if m:
        time_start = m.group(1)
        time_end = m.group(2)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_dt = today.replace(hour=int(time_start.split(':')[0]), minute=int(time_start.split(':')[1]))
        end_dt = today.replace(hour=int(time_end.split(':')[0]), minute=int(time_end.split(':')[1]))
        return start_dt, end_dt, None
    
    # 无时间，返回默认窗口
    return None, None, 15


def is_in_time_range(line, time_range):
    """检查日志行是否在时间范围内
    
    time_range: (start_datetime, end_datetime) 元组
    如果为 None，返回 True（不过滤）
    """
    if not time_range or time_range[0] is None:
        return True
    
    start_dt, end_dt = time_range
    log_ts = parse_log_time(line)
    if not log_ts:
        return True
    
    # 处理只有日期没有时间的日志（默认当天）
    if log_ts.year == 1900:
        log_ts = log_ts.replace(year=start_dt.year, month=start_dt.month, day=start_dt.day)
    
    return start_dt <= log_ts <= end_dt


def is_in_time_window(line, problem_time, window_minutes, time_range=None):
    """检查日志行是否在问题时间窗口内
    
    优先级: time_range (start, end) > problem_time + window_minutes
    """
    if time_range and time_range[0] is not None:
        return is_in_time_range(line, time_range)
    
    if not problem_time:
        return True
    from datetime import datetime, timedelta
    import re
    try:
        prob_ts = None
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M']:
            try:
                prob_ts = datetime.strptime(problem_time, fmt)
                break
            except:
                continue
        if not prob_ts:
            return True
        log_ts = parse_log_time(line)
        if not log_ts:
            return True
        if log_ts.year == 1900:
            log_ts = log_ts.replace(year=prob_ts.year)
        diff = abs((log_ts - prob_ts).total_seconds() / 60)
        return diff <= window_minutes
    except:
        return True


def read_ios_logs(extracted_dir, max_size_kb=5120, problem_time=None, time_window=30, time_range=None):
    results = {}
    if not os.path.exists(extracted_dir):
        return results
    txt_files = glob.glob(os.path.join(extracted_dir, '**', '*.txt'), recursive=True)
    for txt_file in txt_files:
        size_kb = os.path.getsize(txt_file) / 1024
        if size_kb > max_size_kb:
            continue
        try:
            rel = os.path.relpath(txt_file, extracted_dir)
            with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            for category, keywords in IOS_KEYWORDS:
                for kw in keywords:
                    kw_lower = kw.lower()
                    for i, line in enumerate(lines):
                        if kw_lower in line.lower() and is_in_time_window(line, problem_time, time_window, time_range):
                            content = line.rstrip('\n\r')
                            if '>>:' in content:
                                continue
                            entry = f"{rel}:{i+1}: {content}"
                            if category not in results:
                                results[category] = []
                            if entry not in results[category] and len(results[category]) < 20:
                                results[category].append(entry)
        except:
            pass
    return results


def read_android_logs(extracted_dir, max_size_kb=5120, problem_time=None, time_window=30, time_range=None):
    results = {}
    if not os.path.exists(extracted_dir):
        return results
    log_files = glob.glob(os.path.join(extracted_dir, '**', '*.log'), recursive=True)
    log_files += glob.glob(os.path.join(extracted_dir, '**', 'main.txt*'), recursive=True)
    log_files += glob.glob(os.path.join(extracted_dir, '**', 'system.txt'), recursive=True)
    for log_file in log_files:
        if not os.path.exists(log_file):
            continue
        try:
            size_kb = os.path.getsize(log_file) / 1024
        except OSError:
            continue
        if size_kb > max_size_kb:
            continue
        try:
            rel = os.path.relpath(log_file, extracted_dir)
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            for category, keywords in ANDROID_KEYWORDS:
                for kw in keywords:
                    kw_lower = kw.lower()
                    for i, line in enumerate(lines):
                        if kw_lower in line.lower() and is_in_time_window(line, problem_time, time_window, time_range):
                            content = line.rstrip('\n\r')
                            if '>>:' in content:
                                continue
                            entry = f"{rel}:{i+1}: {content}"
                            if category not in results:
                                results[category] = []
                            if entry not in results[category] and len(results[category]) < 20:
                                results[category].append(entry)
        except:
            pass
    return results


def analyze_backend_logs(extracted_dir, max_size_kb=5120, problem_time=None, time_window=30, time_range=None):
    results = {}
    for pattern_name, keywords in BACKEND_PATTERNS:
        results[pattern_name] = []
    for root, dirs, files in os.walk(extracted_dir):
        for file in files:
            if not (file.endswith('.log') or 'trace' in file.lower()):
                continue
            fp = os.path.join(root, file)
            try:
                size_kb = os.path.getsize(fp) / 1024
                if size_kb > max_size_kb:
                    continue
            except OSError:
                continue
            try:
                rel = os.path.relpath(fp, extracted_dir)
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                for pattern_name, keywords in BACKEND_PATTERNS:
                    for kw in keywords:
                        kw_lower = kw.lower()
                        for i, line in enumerate(lines):
                            if kw_lower in line.lower() and is_in_time_window(line, problem_time, time_window, time_range):
                                content = line.rstrip('\n\r')
                                if '>>:' in content:
                                    continue
                                entry = f"{rel}:{i+1}: {content}"
                                if entry not in results[pattern_name] and len(results[pattern_name]) < 15:
                                    results[pattern_name].append(entry)
            except:
                pass
    return results


def read_vehicle_logs(extracted_dir, max_size_kb=5000, problem_time=None, time_window=30, time_range=None):
    results = {}
    if not os.path.exists(extracted_dir):
        return results

    vehicle_files = glob.glob(os.path.join(extracted_dir, '**', '*.asc'), recursive=True)
    vehicle_files += glob.glob(os.path.join(extracted_dir, '**', '*.ASC'), recursive=True)
    vehicle_files += glob.glob(os.path.join(extracted_dir, '**', '*.BLF'), recursive=True)
    vehicle_files += glob.glob(os.path.join(extracted_dir, '**', '*.blf'), recursive=True)
    vehicle_files += glob.glob(os.path.join(extracted_dir, '**', '*.vw'), recursive=True)
    # VW file is binary, skip text-based reading in rule engine
    vehicle_files = [f for f in vehicle_files if not f.lower().endswith('.vw')]

    for vfile in vehicle_files:
        try:
            rel = os.path.relpath(vfile, extracted_dir)
            size_kb = os.path.getsize(vfile) / 1024
            if size_kb > max_size_kb:
                size_mb = size_kb / 1024
                results.setdefault('__info__', []).append(f"    文件 {rel} 大小 {size_mb:.1f}MB,截取前 1MB 分析")
                read_size = 1024 * 1024
            else:
                read_size = None

            with open(vfile, 'r', encoding='utf-8', errors='ignore') as f:
                if read_size:
                    content = f.read(read_size)
                else:
                    content = f.read()

            lines = content.split('\n')
            for category, keywords in VEHICLE_KEYWORDS:
                matched = []
                for kw in keywords:
                    kw_lower = kw.lower()
                    for i, line in enumerate(lines):
                        if kw_lower in line.lower() and is_in_time_window(line, problem_time, time_window, time_range):
                            content2 = line.rstrip('\n\r')
                            entry = f"{rel}:{i+1}: {content2}"
                            if entry not in matched and len(matched) < 20:
                                matched.append(entry)
                if matched:
                    if category not in results or category == '__info__':
                        results[category] = matched[:15]

        except Exception as e:
            pass
    return results


DK_SERVICE_PATTERNS = [
    ('nfc_ecp', ['cccop', 'NFC_iN', 'NFC_oN', 'ecp[', 'cccparse', 'ccc--bleERROR', 'ccc--bleParse_Notify', 'ccc--bleparse', 'nfc_pairing error']),
    ('se_error', ['sw=0x6400', 'getdata_rsp sw=', 'getdata_rsp error', 'auth1_rsp error', 'sw=6400']),
    ('key_info', ['pollingsw', 'polling_unlock_mode', 'BleDirection', 'bindkeyid2mac']),
    ('ble_error', ['recv_cb error', 'NotifyToVeh error', 'bleERROR', 'ntf parse error']),
]


def read_dk_service_logs(extracted_dir, max_lines_per_file=5000, problem_time=None, time_window=30, time_range=None):
    results = {}
    for pname, _ in DK_SERVICE_PATTERNS:
        results[pname] = []

    DK_SIGNATURE = ['dev.cpp', 'nfc.cpp', 'transaction.cpp', 'nfc_pairing', 'ccc--NFC']

    def is_dk_service_file(filepath, filename):
        if re.match(r'dk_service(\(\d+\))?\.log$', filename):
            return True
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                sample = f.read(2000)
            sig_count = sum(1 for s in DK_SIGNATURE if s in sample)
            ts_pattern = re.search(r'\[\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', sample)
            return sig_count >= 2 and ts_pattern
        except:
            return False

    for root, dirs, files in os.walk(extracted_dir):
        for file in files:
            fp = os.path.join(root, file)
            if not is_dk_service_file(fp, file):
                continue
            fp = os.path.join(root, file)
            try:
                rel = os.path.relpath(fp, extracted_dir)
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                for pname, keywords in DK_SERVICE_PATTERNS:
                    for i, line in enumerate(lines):
                        for kw in keywords:
                            if kw in line and is_in_time_window(line, problem_time, time_window, time_range):
                                content = line.rstrip('\n\r')
                                if '>>:' in content:
                                    continue
                                entry = f"{rel}:{i+1}: {content}"
                                if entry not in results[pname] and len(results[pname]) < max_lines_per_file:
                                    results[pname].append(entry)
                                if len(results[pname]) >= max_lines_per_file:
                                    break
                        if len(results[pname]) >= max_lines_per_file:
                            break
            except Exception:
                pass
    return results


def classify_fault(ios_data, backend_data, vehicle_data, android_data=None):
    findings = []
    ios_kts = ios_data.get('kts', [])
    ios_error = ios_data.get('error', [])
    ios_carkey = ios_data.get('carkey', [])
    ios_sharing = ios_data.get('sharing', [])
    backend_abx = backend_data.get('abx', [])
    vehicle_nfc = vehicle_data.get('nfc_ecp', []) if isinstance(vehicle_data, dict) else []
    vehicle_se = vehicle_data.get('se_error', []) if isinstance(vehicle_data, dict) else []
    vehicle_ble = vehicle_data.get('ble_error', []) if isinstance(vehicle_data, dict) else []
    vehicle_key = vehicle_data.get('key_info', []) if isinstance(vehicle_data, dict) else []
    vehicle_err = vehicle_data.get('error', []) if isinstance(vehicle_data, dict) else []
    android_err = android_data.get('error', []) if android_data else []
    backend_http = backend_data.get('http', []) if backend_data else []

    if any('-365' in str(e) for e in ios_error):
        findings.append({
            'id': 1,
            'fault_side': '手机端/苹果后台',
            'fault_phase': 'Phase 4 - CheckIDSRegistration 失败',
            'error_code': '-365',
            'certainty': '[确定] 有明确日志证据支持',
            'root_cause': 'iOS 系统 CheckIDSRegistration 返回 -365,表明 Apple 身份服务注册失败.',
            'evidence_categories': ['error', 'kts'],
            'remediation': [
                ('手机端/苹果后台', '检查设备 Apple Pay 证书状态'),
                ('车企后台', '检查 ABR (Apple Backend Routing) 配置'),
            ]
        })
    if any('PinningEvent' in str(e) or 'TrustResult' in str(e) for e in ios_kts):
        findings.append({
            'id': 2,
            'fault_side': '手机端/苹果后台',
            'fault_phase': 'Phase 3 - 证书链校验失败',
            'error_code': 'TrustResult 4/5',
            'certainty': '[确定] 有明确日志证据支持',
            'root_cause': 'Apple Pay 证书验证失败 (PinningEvent),证书链校验未通过.',
            'evidence_categories': ['kts', 'error'],
            'remediation': [
                ('手机端', '检查设备系统时间'),
                ('手机端', '尝试重新添加 Apple Pay 卡片'),
            ]
        })
    if any('Pretrack' in str(e) or 'trackKey' in str(e) for e in ios_sharing):
        if any('404' in str(e) or 'Not Found' in str(e) for e in backend_abx):
            findings.append({
                'id': 3,
                'fault_side': '数字钥匙后端服务',
                'fault_phase': 'Key Sharing - Pretrack 服务 404',
                'error_code': 'HTTP 404',
                'certainty': '[确定] 有明确日志证据支持',
                'root_cause': 'Pretrack 服务返回 404 Not Found,URL 配置错误或服务未部署.',
                'evidence_categories': ['sharing', 'abx'],
                'remediation': [
                    ('车企后台', '检查 Pretrack 服务部署'),
                    ('车企后台', '核对 Pretrack URL 配置'),
                ]
            })
    if any('KTS' in str(e) and ('timeout' in str(e).lower() or 'fail' in str(e).lower()) for e in ios_kts + backend_abx):
        findings.append({
            'id': 4,
            'fault_side': '数字钥匙后端服务',
            'fault_phase': 'Phase 4 - KTS 请求无响应',
            'error_code': 'KTS Timeout',
            'certainty': '[高概率] 有强关联证据',
            'root_cause': 'KTS 请求发出后未收到有效响应.',
            'evidence_categories': ['kts', 'abx'],
            'remediation': [
                ('车企后台', '检查 ABR 配置和 KTS 请求端点'),
                ('车企后台', '检查后端日志'),
            ]
        })
    has_cccopt2 = any(re.search(r'cccop\s*=\s*2', str(e)) for e in vehicle_nfc)
    has_se_error = any('sw=0x6400' in str(e) or 'getdata_rsp error' in str(e) or 'sw=6400' in str(e) for e in vehicle_nfc + vehicle_se)
    if has_cccopt2 and has_se_error:
        findings.append({
            'id': 5,
            'fault_side': '车端',
            'fault_phase': 'Phase 2-3 - NFC SE 访问失败',
            'error_code': 'cccop=2 + sw=0x6400',
            'certainty': '[确定] 有明确日志证据支持',
            'root_cause': 'NFC 固件 cccop=2(只读模式),无法写入 ECP 安全区域,导致 SE Applet 访问返回 sw=0x6400(执行失败),CCC 配对无法完成.',
            'evidence_categories': ['nfc_ecp', 'se_error'],
            'remediation': [
                ('车端', '更新 NFC 软件使 cccop 默认值=1'),
                ('车端', '通过 TBOX 配置正确的 ECP 值'),
                ('车端', '确认 ACOSe 提供的 ECP 参数已写入 NFC'),
            ]
        })
    reason62_entries = [e for e in vehicle_data.get('ble_error', []) if 'reason=62' in str(e)] if isinstance(vehicle_data, dict) else []
    if reason62_entries:
        findings.append({
            'id': 6,
            'fault_side': '手机端',
            'fault_phase': 'BLE 连接未建立',
            'error_code': 'disconnected, reason=62',
            'certainty': '[确定] 有明确日志证据支持',
            'root_cause': 'BLE 连接建立失败,链接层在6个周期广播事件内未能同步,原因通常在手机端,非车端故障.',
            'evidence_categories': ['ble_error'],
            'remediation': [
                ('手机端', '重启手机'),
                ('手机端', '检查蓝牙是否被其他设备占用'),
            ]
        })
    vehicle_ble_only = [e for e in vehicle_data.get('ble_error', []) if 'reason=62' not in str(e)] if isinstance(vehicle_data, dict) else vehicle_data.get('ble_error', [])
    if vehicle_ble_only:
        findings.append({
            'id': 7,
            'fault_side': '车端',
            'fault_phase': 'BLE 通信异常',
            'error_code': 'recv_cb error',
            'certainty': '[确定] 有日志证据支持',
            'root_cause': '车端蓝牙接收回调报错,连接不稳定或被意外断开.',
            'evidence_categories': ['ble_error'],
            'remediation': [
                ('车端', '检查蓝牙固件版本'),
                ('车端', '排查 BLE 连接稳定性'),
            ]
        })
    if any('keyid' in str(e).lower() and 'not found' in str(e).lower() for e in vehicle_key + vehicle_err + android_err):
        findings.append({
            'id': 8,
            'fault_side': '车端',
            'fault_phase': '钥匙绑定关系丢失',
            'error_code': 'bindkeyid2mac error',
            'certainty': '[高概率] 有日志证据支持',
            'root_cause': '钥匙 keyid 与手机 MAC 的绑定关系丢失,车端无法识别钥匙身份.',
            'evidence_categories': ['key_info', 'error'],
            'remediation': [
                ('车端', '检查钥匙绑定表存储机制'),
                ('车端', '重新执行钥匙绑定流程'),
            ]
        })
    if backend_http or any('error' in str(e).lower() or 'fail' in str(e).lower() for e in backend_abx):
        findings.append({
            'id': 9,
            'fault_side': '数字钥匙后端服务',
            'fault_phase': '后台 API 调用异常',
            'error_code': 'HTTP error',
            'certainty': '[确定] 有日志证据支持',
            'root_cause': '车企后台服务接口返回错误状态码,数字钥匙操作无法完成.',
            'evidence_categories': ['abx', 'http'],
            'remediation': [
                ('车企后台', '检查后台服务状态和接口日志'),
                ('车企后台', '确认数字钥匙相关接口可用'),
            ]
        })
    ios_auth_timeout = ios_data.get('error', [])
    vehicle_auth1 = vehicle_err if isinstance(vehicle_data, dict) else []
    if any('Auth鉴权超时' in str(e) or 'Auth1失败' in str(e) for e in ios_auth_timeout + vehicle_auth1):
        findings.append({
            'id': 10,
            'fault_side': '手机端',
            'fault_phase': 'Phase 2 - 安全报文 counter 不匹配',
            'error_code': 'Auth1 失败',
            'certainty': '[高概率] 有日志证据支持',
            'root_cause': '多设备切换导致旧设备缓存的安全报文 counter 小于 TBOX 端当前值,车端判定为重放攻击,Auth1 校验失败.',
            'evidence_categories': ['carkey', 'error'],
            'remediation': [
                ('手机端', '在 APP 中退出登录并删除本地数据库 .db/.db-wal/.db-shm 文件'),
                ('手机端', '重新登录后再次尝试配对'),
            ]
        })
    ios_carkey_session = ios_data.get('carkey', [])
    if any('CarKeyErrorCode' in str(e) or 'carKeySession' in str(e) or 'start session error' in str(e) for e in ios_carkey_session):
        findings.append({
            'id': 11,
            'fault_side': '手机端',
            'fault_phase': 'BLE 通道被 carKeySession 占用',
            'error_code': 'CarKeyErrorCode 错误0',
            'certainty': '[确定] 有日志证据支持',
            'root_cause': '一键注销后苹果未清理完 CarKey 信息,carKeySession 仍占用私有 BLE 通道,新连接请求失败.',
            'evidence_categories': ['carkey'],
            'remediation': [
                ('手机端', '手动在钱包中移除钥匙'),
                ('手机端', '等待 carKeySession 超时释放'),
                ('SDK', '修复多个 carKeySession 内存泄露导致的状态混乱问题'),
            ]
        })

    if not findings:
        if ios_error or ios_carkey or ios_kts or backend_abx or vehicle_nfc or vehicle_err:
            findings.append({
                'id': 99,
                'fault_side': '需进一步分析',
                'fault_phase': '配对流程 - 定位中',
                'error_code': '详见日志片段',
                'certainty': '[待确认] 需补充日志验证',
                'root_cause': '已发现相关错误信息,但无法精确定位根因.',
                'evidence_categories': [],
                'remediation': [('分析', '请提供更完整的日志')]
            })
        else:
            findings.append({
                'id': 99,
                'fault_side': '无法确定',
                'fault_phase': 'N/A',
                'error_code': 'N/A',
                'certainty': '[待确认] 需补充日志验证',
                'root_cause': '未能从现有日志中提取到关键错误信息.',
                'evidence_categories': [],
                'remediation': [('分析', '确认日志时间范围'), ('分析', '扩大搜索关键词')]
            })

    return findings
def extract_problem_time(jira_context):
    """从 jira_context 提取问题时间"""
    import re
    if not jira_context:
        return None
    if isinstance(jira_context, str):
        match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2})', jira_context)
        return match.group(1) if match else None
    all_fields = jira_context.get('all_fields', {})
    desc = all_fields.get('description', '') or ''
    test_time = all_fields.get('customfield_20760') or all_fields.get('test_time')
    if test_time:
        return test_time
    match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2})', desc)
    if match:
        return match.group(1)
    return None


def generate_report(ticket_key, extracted_dir, analysis_output_dir, jira_context=None, no_logs=False, time_range_override=None):
    """生成规则引擎分析报告
    
    time_range_override: (start_datetime, end_datetime) 元组
        - 如果传入，优先使用此时间范围
        - 不传则从 jira_context 解析
    """
    os.makedirs(analysis_output_dir, exist_ok=True)

    if time_range_override and time_range_override[0] is not None:
        time_range = time_range_override
        problem_time = None
        time_window = 15
    else:
        problem_time = extract_problem_time(jira_context)
        time_range = None
        time_window = 30
    print("    [目录扫描]")
    t0 = time.time()
    if no_logs:
        log_tree = ["(日志目录为空)"]
        log_types = {'ios': [], 'vehicle': [], 'backend': [], 'android': [], 'unknown': []}
        print("    [日志读取] 跳过(无日志)")
        ios_data = {}
        android_data = {}
        backend_data = {}
        vehicle_data = {}
        findings = [{
            'id': 999,
            'fault_side': '需补充日志',
            'fault_phase': '日志缺失',
            'error_code': 'N/A',
            'certainty': '[待确认] 无日志，基于 JIRA 描述推断',
            'root_cause': 'JIRA 中描述的现象与 CCC CarKey BLE/Polling 机制相关，但无日志无法定位具体断点.',
            'evidence_categories': [],
            'remediation': [
                ('分析', '补充 CAN 日志 (ASC/BLF) 以定位 PE/Polling 状态'),
                ('分析', '补充车端 dk_service.log 以确认 BLE 广播状态'),
                ('分析', '补充 iOS sysdiagnose 以确认手机端 BLE 连接状态'),
            ]
        }]
        log_snippets = []
        log_completeness = ["无日志附件"]
        completeness = 'D - No logs'
    else:
        log_tree = _timed("list_extracted_files", list_extracted_files, extracted_dir)
        log_types = _timed("classify_logs", classify_logs, extracted_dir)
        print("    [日志读取]")

        log_completeness = []
        log_type_names = {'ios': 'iOS sysdiagnose', 'vehicle': 'CAN/BLF', 'backend': 'Digital Key Backend', 'android': 'Android logcat'}
        for lt, files in log_types.items():
            if files:
                log_completeness.append(f"[{lt.upper()}] 找到 {len(files)} 个文件")

        ios_count = len(log_types['ios'])
        vehicle_count = len(log_types['vehicle'])
        backend_count = len(log_types['backend'])
        android_count = len(log_types['android'])
        sides_present = sum(x > 0 for x in [ios_count, android_count, vehicle_count, backend_count])
        phone_count = ios_count + android_count
        if sides_present == 0:
            completeness = 'D - No valid logs'
        elif sides_present == 1:
            completeness = f"D - Single side ({'Phone' if phone_count > 0 else 'Vehicle' if vehicle_count > 0 else 'Backend'})"
        elif sides_present == 2:
            completeness = f"C - Two sides (phone:{phone_count} vehicle:{vehicle_count} backend:{backend_count})"
        elif sides_present == 3:
            completeness = 'B - Three sides'
        else:
            completeness = 'A - All four sides'

        ios_data = _timed("read_ios_logs", read_ios_logs, extracted_dir, problem_time=problem_time, time_window=time_window, time_range=time_range)
        android_data = _timed("read_android_logs", read_android_logs, extracted_dir, problem_time=problem_time, time_window=time_window, time_range=time_range)
        backend_data = _timed("analyze_backend_logs", analyze_backend_logs, extracted_dir, problem_time=problem_time, time_window=time_window, time_range=time_range)
        vehicle_data = _timed("read_vehicle_logs", read_vehicle_logs, extracted_dir, problem_time=problem_time, time_window=time_window, time_range=time_range)
        dk_data = _timed("read_dk_service_logs", read_dk_service_logs, extracted_dir, problem_time=problem_time, time_window=time_window, time_range=time_range)
        for key, vals in dk_data.items():
            if key not in vehicle_data:
                vehicle_data[key] = []
            for v in vals:
                if v not in vehicle_data[key]:
                    vehicle_data[key].append(v)
        findings = _timed("classify_fault", classify_fault, ios_data, backend_data, vehicle_data, android_data)
        print(f"    [报告生成]")

    EVIDENCE_PRIORITY = ['error', 'se_error', 'nfc_ecp', 'ble_error', 'kts', 'carkey', 'sharing',
                          'key_info', 'pairing', 'bluetooth', 'digital_key', 'nfc', 'uwb', 'can_id', 'abx', 'pairstatus', 'config']

    def group_by_file(data_dict, extracted_dir):
        files = {}
        for category, entries in data_dict.items():
            for entry in entries:
                m = re.match(r'^(.+?):(\d+): (.+)$', entry)
                if m:
                    rel_fp = m.group(1)
                    line_no = m.group(2)
                    content = m.group(3)
                    abs_fp = os.path.abspath(os.path.join(extracted_dir, rel_fp))
                    if abs_fp not in files:
                        files[abs_fp] = {}
                    if category not in files[abs_fp]:
                        files[abs_fp][category] = []
                    full_entry = f"{line_no}: {content}"
                    if full_entry not in files[abs_fp][category]:
                        files[abs_fp][category].append(full_entry)
        return files

    def build_snippets(data_dict, section_title, findings):
        grouped = group_by_file(data_dict, extracted_dir)
        if not grouped:
            return []
        relevant_cats = set()
        for f in findings:
            relevant_cats.update(f.get('evidence_categories', []))
        lines = [f"### {section_title}"]
        for fp, categories in grouped.items():
            relevant_in_file = {c: categories[c] for c in categories if c in relevant_cats}
            if not relevant_in_file:
                relevant_in_file = dict(sorted(categories.items(), key=lambda x: (
                    EVIDENCE_PRIORITY.index(x[0]) if x[0] in EVIDENCE_PRIORITY else 99
                )))
                if not relevant_in_file:
                    continue
            for cat in sorted(relevant_in_file.keys(), key=lambda c: (
                EVIDENCE_PRIORITY.index(c) if c in EVIDENCE_PRIORITY else 99
            )):
                rel_path = os.path.relpath(fp, extracted_dir).replace('\\', '/')
                for entry in relevant_in_file[cat][:3]:
                    parts = entry.split(': ', 1)
                    line_no = parts[0] if parts else ''
                    content = parts[1] if len(parts) > 1 else entry
                    lines.append(f"【日志路径: extracted/{rel_path}，行号:{line_no}】")
                    lines.append("```")
                    lines.append(content)
                    lines.append("```")
        return lines

    log_snippets = []
    log_snippets += build_snippets({k: v for k, v in ios_data.items() if v}, "iOS 系统日志", findings)
    log_snippets += build_snippets({k: v for k, v in android_data.items() if v}, "Android 日志", findings)
    log_snippets += build_snippets({k: v for k, v in backend_data.items() if v}, "车企后台日志", findings)
    vd = {k: v for k, v in vehicle_data.items() if k not in ('__info__',) and v}
    log_snippets += build_snippets(vd, "车端日志", findings)

    if not log_snippets:
        log_snippets = ['No key log snippets extracted.']

    remediation_rows = []
    for f in findings:
        for side, measure in f['remediation']:
            remediation_rows.append(f"| {side} | {measure} |")

    finding_summary_lines = ["| # | 故障端 | 失败环节 | 错误码 | 确定性 |"]
    finding_summary_lines.append("|--|--|--|--|--|")
    for f in findings:
        finding_summary_lines.append(f"| {f['id']} | {f['fault_side']} | {f['fault_phase']} | {f['error_code']} | {f['certainty']} |")

    references = [
        'CCC-TS-101-Digital-Key-v4.0.0.pdf',
        'Apple Car Keys Message Exchange Protocol R1.pdf',
    ]

    jira_info = jira_context if jira_context else "(未获取到 JIRA 信息)"

    finding_summary = '\n'.join(finding_summary_lines)

    report = ANALYSIS_REPORT_TEMPLATE.format(
        ticket_key=ticket_key,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        jira_info=jira_info,
        finding_count=len(findings),
        finding_summary=finding_summary,
        log_snippets='\n\n'.join(log_snippets),
        remediation='\n'.join(remediation_rows)
    )

    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    rule_report_file = os.path.join(analysis_output_dir, f'{ticket_key}_规则分析报告_{ts}.md')
    t_write = time.time()
    with open(rule_report_file, 'w', encoding='utf-8') as fh:
        fh.write(report)
    print(f"    [规则报告写入] {time.time()-t_write:.1f}s")
    print(f"    [generate_report总计] {time.time()-t0:.1f}s")
    print(f"[成功] 规则分析报告已生成: {rule_report_file}")
    return rule_report_file, report, log_snippets, findings


def detect_issue_type_from_jira(jira_context_str):
    """从 JIRA context 字符串检测问题类型（兜底补充）
    
    当规则引擎未命中相关证据分类时，从 JIRA 摘要/描述中关键词补充知识库
    """
    if not jira_context_str:
        return []
    
    text = jira_context_str.lower()
    needed = []
    
    uwb_keywords = ['tof', 'tofw', 'uwb', '测距', '测距值', '定位', 'ranging',
                    '无tof', '无uwb', 'pe不解锁', '走近不解锁', 'passive entry']
    nfc_keywords = ['nfc', '刷卡', '弹窗', '无弹窗', 'ecp', 'iso7816']
    pairing_keywords = ['配对', 'pairing', 'pair', '分享', 'sharing', 'friend',
                        'invite', '钥匙分享', 'first friend', 'kts', '注册失败']
    ble_keywords = ['ble', '蓝牙', '断开', 'reason=62', '连接失败', 'carkeyerrorcode']
    backend_keywords = ['http', '404', 'pretrack', '后台', 'backend', 'abx',
                        'kts timeout', '90000008', '90000011', '99990004']
    
    for kw in uwb_keywords:
        if kw in text:
            needed.append('uwb_ranging')
            break
    for kw in nfc_keywords:
        if kw in text:
            needed.append('nfc_ecp')
            break
    for kw in pairing_keywords:
        if kw in text:
            needed.append('ccc_pairing')
            break
    for kw in ble_keywords:
        if kw in text:
            needed.append('ble_connection')
            break
    for kw in backend_keywords:
        if kw in text:
            needed.append('backend')
            break
    
    return list(set(needed))


def should_include_dbc(fault_info, log_types):
    """判断是否需要加载 DBC 参考信息
    
    条件：问题涉及 CAN 信号 + 日志有 ASC/BLF 文件
    """
    can_related_categories = {'can_id', 'uwb', 'digital_key', 'pe_unlock', 'rssi'}
    needs_can = False
    if fault_info and isinstance(fault_info, list):
        for f in fault_info:
            cats = f.get('evidence_categories', [])
            for cat in cats:
                if cat in can_related_categories:
                    needs_can = True
                    break
            if needs_can:
                break
    
    if not needs_can:
        return False
    
    has_can_logs = any(
        f.lower().endswith(('.asc', '.blf')) or 'can' in os.path.basename(f).lower()
        for f in log_types.get('vehicle', [])
    )
    
    return has_can_logs


def load_dbc_info(issue_type=None, fault_info=None):
    """加载 DBC 缓存并格式化为 AI 可读的摘要
    
    按问题类型选择性加载:
    - uwb: 只加载 UWB 相关 (0x12DD5xx / 0x283)
    - pairing/pe_unlock: 加载配对相关 (0x21C, 0x224, 0x625)
    - 默认: 加载通用数字钥匙信号
    
    使用 should_include_dbc() 判断是否需要加载
    """
    cache_file = os.path.join(os.path.dirname(__file__), 'cache', 'dbc_cache.json')
    if not os.path.exists(cache_file):
        return ""
    try:
        import json as _json
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        msgs = data.get('messages', {})
        
        # 按问题类型选择 CAN 消息
        if issue_type in ('uwb', 'uwb_ranging'):
            KEY_MSGS = [1577]  # 0x12DD5xx UWBKey
        elif issue_type in ('pairing', 'nfc', 'ccc_pairing'):
            KEY_MSGS = [552, 657, 662]  # 0x21C, 0x291, 0x296
        elif issue_type in ('pe_unlock',):
            KEY_MSGS = [628, 643]  # 0x274 PEUnlock, 0x283 DigitalKey
        elif issue_type == 'ble':
            KEY_MSGS = [540]  # 0x21C BLE info
        else:
            # 默认加载通用数字钥匙相关
            KEY_MSGS = [643, 1577, 540, 548, 552, 657, 662, 628]
        
        lines = ["## DBC 数字钥匙信号参考(预解析)"]
        lines.append(f"* 来源: {data.get('source_dir', '')} / {data.get('generated_at', '')}")
        if issue_type:
            lines.append(f"* 按问题类型筛选: {issue_type}")
        lines.append("")
        for mid in KEY_MSGS:
            if str(mid) not in msgs:
                continue
            msg = msgs[str(mid)]
            lines.append(f"### {msg['hex_id']} {msg['name']}")
            if msg.get('cycle_time_ms'):
                lines.append(f"* 周期: {msg['cycle_time_ms']}ms")
            sig_lines = []
            for sig in msg.get('signals', []):
                bits = f"Bit{sig['start_bit']}"
                vals = ""
                if sig['values']:
                    val_strs = [f"{k}={v}" for k, v in list(sig['values'].items())[:5]]
                    vals = f" ({', '.join(val_strs)})"
                unit = f" [{sig['unit']}]" if sig['unit'] else ""
                sig_lines.append(f"  - {sig['name']}: {bits}{unit}{vals}")
            lines.extend(sig_lines[:25])
            lines.append("")
        return '\n'.join(lines)
    except Exception:
        return ""

def load_knowledge_summaries(issue_type=None, fault_info=None, jira_issue_types=None):
    """按需加载知识库摘要

    优先级：issue_type > fault_info 推断 > jira_issue_types 关键词检测

    映射关系:
      nfc_ecp/se_error/nfc  → nfc_ecp
      uwb/can_id/pe_unlock  → uwb_ranging
      pairing/kts/carkey/sharing/pairstatus → ccc_pairing
      ble_error/bluetooth/key_info → ble_connection
      abx/config/error/auth → backend
      digital_key/android   → mdk_ops（兜底）
    """
    summaries_file = os.path.join(os.path.dirname(__file__), 'cache', 'knowledge_summaries.json')
    if not os.path.exists(summaries_file):
        return ""
    try:
        with open(summaries_file, 'r', encoding='utf-8-sig') as f:
            summaries = json.load(f)
    except Exception:
        return ""

    target_keys = set()

    # 1. fault_info 推断
    if fault_info and isinstance(fault_info, list):
        for f in fault_info:
            cats = f.get('evidence_categories', [])
            for cat in cats:
                if cat in ('nfc_ecp', 'se_error', 'nfc'):
                    target_keys.add('nfc_ecp')
                elif cat in ('uwb', 'can_id', 'pe_unlock'):
                    target_keys.add('uwb_ranging')
                elif cat in ('pairing', 'kts', 'carkey', 'sharing', 'pairstatus'):
                    target_keys.add('ccc_pairing')
                elif cat in ('ble_error', 'bluetooth', 'key_info'):
                    target_keys.add('ble_connection')
                elif cat in ('abx', 'config', 'auth'):
                    target_keys.add('backend')
                elif cat in ('error', 'digital_key'):
                    target_keys.add('mdk_ops')

    # 2. JIRA 关键词兜底（规则引擎未命中时补充）
    if jira_issue_types and isinstance(jira_issue_types, list):
        target_keys.update(jira_issue_types)

    # 3. issue_type 显式指定（最高优先级）
    if issue_type:
        if isinstance(issue_type, str):
            target_keys.add(issue_type)
        elif isinstance(issue_type, list):
            target_keys.update(issue_type)

    reliability_note = {
        "high": "【官方/权威】",
        "medium": "【经验/参考】",
        "low": "【待验证】"
    }

    if not target_keys:
        return ""

    summaries = {k: v for k, v in summaries.items() if k in target_keys}

    lines = ["## 故障域知识库摘要"]
    lines.append("")
    lines.append("> 重要提示：以下知识库摘要中，reliability=high 的内容可作为权威依据；reliability=medium 的内容仅供参考，需结合日志验证；reliability=low 的内容为待验证信息，请谨慎使用。")
    lines.append("")
    for key, info in summaries.items():
        rel = reliability_note.get(info.get('reliability', 'medium'), "【参考】")
        source = info.get('source', '未知来源')
        lines.append(f"### {info['title']} (`{info['file']}`) {rel}")
        lines.append(f"*来源: {source}*")
        lines.append("")
        lines.append(info['summary'])
        lines.append("")
        for sec in info.get('sections', []):
            sec_rel = reliability_note.get(sec.get('reliability', 'medium'), "【参考】")
            lines.append(f"- **章节: {sec['id']}** {sec_rel} - {sec['content']}")
        lines.append("")
    return '\n'.join(lines)

def run_ai_analysis(ticket_key, extracted_dir, analysis_output_dir, jira_context=None, log_snippets=None, fault_info=None, no_logs=False, time_range_override=None):
    print("[AI] 开始 opencode AI 深度分析...")
    t_ai_total = time.time()
    print("    [扫描日志文件]")
    t_scan = time.time()
    log_files = []
    log_types = {'vehicle': [], 'ios': [], 'backend': [], 'android': [], 'unknown': []}
    if no_logs:
        log_tree = ["(日志目录为空，未获取到任何附件日志)"]
        log_summary = "Log types: 无日志附件"
        print("      扫描完成: 0.0s (无日志)")
    else:
        if os.path.exists(extracted_dir):
            for root, dirs, files in os.walk(extracted_dir):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in ('.txt', '.log', '.asc', '.vw', '.mdf') or 'main.txt' in file or 'security-sysdiagnose' in file:
                        fp = os.path.join(root, file)
                        size_mb = os.path.getsize(fp) / 1024 / 1024
                        is_can_file = ext in ('.asc', '.blf') or file.lower().startswith('can')
                        if size_mb > 50:
                            if is_can_file:
                                log_files.append((fp, f"[{size_mb:.1f}MB - reading first 1MB]"))
                            else:
                                log_files.append((fp, f"[{size_mb:.1f}MB - too large, skipped]"))
                        else:
                            log_files.append((fp, None))
        log_tree = list_extracted_files(extracted_dir)
        log_types = classify_logs(extracted_dir)
        present = [k for k, v in log_types.items() if v]
        log_summary = f"Log types: {', '.join(present) if present else 'unknown'}"
        print(f"      扫描完成: {time.time()-t_scan:.1f}s")

    jira_section = ""
    if jira_context:
        jira_section = f"""{jira_context}
"""

    # DBC 按需判断：问题涉及 CAN + 日志有 ASC/BLF
    include_dbc = should_include_dbc(fault_info, log_types)
    if include_dbc:
        # 从 fault_info 推断需要的 DBC 类型
        issue_type = None
        if fault_info and isinstance(fault_info, list):
            for f in fault_info:
                cats = f.get('evidence_categories', [])
                if 'uwb' in cats:
                    issue_type = 'uwb'
                    break
                elif 'can_id' in cats or 'pe_unlock' in cats:
                    issue_type = 'pe_unlock'
                    break
                elif 'nfc_ecp' in cats or 'pairing' in cats:
                    issue_type = 'pairing'
                    break
        dbc_section = load_dbc_info(issue_type=issue_type)
        print(f"    [DBC] 按需加载: {issue_type or '默认'}")
    else:
        dbc_section = ""
        print(f"    [DBC] 跳过 (问题不涉及 CAN 或无 CAN 日志)")

    # 知识摘要按需加载（fault_info 推断 + JIRA 关键词兜底）
    jira_issue_types = detect_issue_type_from_jira(jira_context)
    knowledge_section = load_knowledge_summaries(fault_info=fault_info, jira_issue_types=jira_issue_types)
    knowledge_size = len(knowledge_section)
    print(f"    [知识库] 按需注入: {knowledge_size} 字符 (jira关键词: {jira_issue_types})")

    print("    [读取日志内容]")
    t_read = time.time()
    prompt_lines = [
        f"# JIRA Ticket: {ticket_key}",
        f"## {log_summary}",
        jira_section,
        "## 日志目录结构",
        "```",
        '\n'.join(log_tree[:80]) if log_tree else "(empty)",
        "```",
        "",
        dbc_section,
        "",
        "## 日志文件内容",
    ]
    log_text_size = 0  # 统计实际日志文本大小
    
    # Snippets 充足时减少原始日志读取
    snippet_count = len(log_snippets) if log_snippets else 0
    max_log_files = 15
    max_raw_size = 50000
    if snippet_count > 50:
        max_log_files = 5
        max_raw_size = 20000
        print(f"    [原始日志] Snippets 充足({snippet_count}条)，减少读取: {max_log_files}文件, {max_raw_size/1024:.0f}KB")
    elif snippet_count > 30:
        max_log_files = 8
        max_raw_size = 30000
        print(f"    [原始日志] Snippets 充足({snippet_count}条)，适当减少: {max_log_files}文件")
    
    if no_logs:
        prompt_lines.append("(无日志附件，以下分析基于 JIRA 描述 + 知识库)")
    else:
        for fp, note in log_files[:max_log_files]:
            rel = os.path.relpath(fp, extracted_dir)
            ext = os.path.splitext(fp)[1].lower()
            is_can_file = ext in ('.asc', '.blf') or 'can' in os.path.basename(fp).lower()
            is_dk_service = os.path.basename(fp) == 'dk_service.log'
            
            if time_range_override and time_range_override[0] is not None:
                # 策略1: 时间过滤读取（流式，逐行处理，不全部加载内存）
                try:
                    size_mb = os.path.getsize(fp) / 1024 / 1024
                    # 大文件限制行数，避免 OOM 和超时
                    max_lines = 200000 if size_mb > 10 else 50000
                    
                    matched_lines = []  # (line_no, content)
                    bytes_read = 0
                    line_no = 0
                    
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            line_no += 1
                            if line_no > max_lines:
                                break
                            bytes_read += len(line)
                            if bytes_read > 2 * 1024 * 1024:
                                break
                            if is_in_time_range(line, time_range_override):
                                matched_lines.append((line_no, line.rstrip('\n\r')))
                    
                    # 保留匹配行及其前后各2行（前后上下文）
                    matched_set = set()
                    final_lines = []
                    for ln, content in matched_lines:
                        for j in range(max(1, ln - 2), ln + 3):
                            if j not in matched_set:
                                matched_set.add(j)
                                final_lines.append((j, None))  # placeholder
                    
                    # 重新读取上下文行（流式二次扫描）
                    context_lines = {}
                    scan_count = 0
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            scan_count += 1
                            if scan_count > max_lines:
                                break
                            if scan_count in matched_set:
                                context_lines[scan_count] = line.rstrip('\n\r')
                    
                    content_lines = [context_lines[i] for i in sorted(context_lines.keys()) if i in context_lines]
                    content = '\n'.join(content_lines[:200])
                    
                    if not content.strip():
                        # 兜底：读首部 5KB
                        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(5000)
                        prompt_lines.append(f"\n### {rel} (时间窗口内无日志，读取首部5KB)")
                        prompt_lines.append("```")
                        prompt_lines.append(content[:5000])
                        prompt_lines.append("```")
                    else:
                        log_text_size += len(content)
                        prompt_lines.append(f"\n### {rel} (时间过滤, {len(content_lines)}行)")
                        prompt_lines.append("```")
                        prompt_lines.append(content[:8000])
                        prompt_lines.append("```")
                except Exception as e:
                    log_text_size += 50
                    prompt_lines.append(f"- {rel} [read error: {e}]")
            elif note:
                # 策略2: 无时间过滤，按原逻辑（大小限制的 head/tail）
                prompt_lines.append(f"- {rel} {note}")
                if is_can_file:
                    try:
                        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(20 * 1024)
                        log_text_size += len(content)
                        prompt_lines.append(f"\n### {rel} (首20KB)")
                        prompt_lines.append("```")
                        prompt_lines.append(content[:5000])
                        prompt_lines.append("```")
                    except Exception as e:
                        log_text_size += 50
                        prompt_lines.append(f"  [read error: {e}]")
            else:
                # 策略3: 无时间过滤，按原逻辑（末尾5KB）
                try:
                    size_mb = os.path.getsize(fp) / 1024 / 1024
                    if size_mb > 10:
                        prompt_lines.append(f"- {rel} [{size_mb:.0f}MB - skipped]")
                    else:
                        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(max_raw_size)
                        log_text_size += len(content)
                        prompt_lines.append(f"\n### {rel}")
                        prompt_lines.append("```")
                        if is_dk_service:
                            prompt_lines.append("[dk_service.log 过大,按关键词全文搜索关键片段]")
                        # Snippets 充足时只取末尾 3KB，否则末尾 5KB
                        tail_size = 3000 if snippet_count > 30 else 5000
                        prompt_lines.append(content[-tail_size:])
                        prompt_lines.append("```")
                except Exception as e:
                    log_text_size += 50
                    prompt_lines.append(f"- {rel} [read error: {e}]")
    print(f"      读取完成: {time.time()-t_read:.1f}s")

    if log_snippets and not no_logs:
        snippet_preview = []
        for s in log_snippets[:10]:
            snippet_preview.append(s)
        prompt_lines.append("")
        prompt_lines.append("## 规则引擎提取的关键日志片段")
        prompt_lines.append("(以下是关键日志，供分析参考，不要原样输出到报告中)")
        prompt_lines.append("---")
        for s in snippet_preview:
            prompt_lines.append(s)

    if fault_info and isinstance(fault_info, list):
        prompt_lines.append("")
        prompt_lines.append("## 规则引擎已知结论(权威结论,AI 分析时不得推翻,如日志证据与结论矛盾才可修正)")
        for i, f in enumerate(fault_info):
            prompt_lines.append(f"""
### 问题{i+1}
**故障端**: {f.get('fault_side', 'N/A')}
**失败环节**: {f.get('fault_phase', 'N/A')}
**错误码**: {f.get('error_code', 'N/A')}
**确定性**: {f.get('certainty', 'N/A')}
**根因**: {f.get('root_cause', 'N/A')}
""")

    prompt_text = '\n'.join(prompt_lines)

    LOG_SIZE_THRESHOLD = 1024
    is_low_log = log_text_size < LOG_SIZE_THRESHOLD and not no_logs
    skip_ai = log_text_size == 0 and not no_logs

    # 日志为 0 时直接生成报告，无需 AI
    if skip_ai:
        print(f"    [跳过 AI] 日志文本=0字节，仅基于规则引擎生成报告")
        report = f"""## 一、JIRA 信息
{jira_section}

## 二、分析结论
**故障端**: 日志缺失
**根因**: 无可用日志，无法定位。附件内容为二进制文件（.vw/.ubin），无可读文本。

## 三、关键日志片段
无有效日志（附件为二进制格式）

## 四、根因分析
由于所有附件均为二进制文件（.vw/.ubin），无法提取可读文本内容进行 AI 分析。
建议下次提单时附上 .log / .txt / .clog 等文本格式日志。

## 五、整改建议
| 归属端 | 建议 |
|--------|------|
| 用户提单 | 附上 dk_service.log / security-sysdiagnose.txt 等文本日志 |
| 用户提单 | 附上 OneApp Android 日志（.log / .txt） |

## 六、补充说明
**日志完整性**: D级（无文本日志）
**解压文件数**: {len(log_files) if 'log_files' in dir() else 'N/A'}，全部为二进制格式

## 七、结论
**日志严重缺失**，所有附件均为二进制格式，无可读文本。无法进行有效的 CCC CarKey 配对失败分析。建议用户重新提单并附上文本格式日志。
"""
        ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_file = os.path.join(analysis_output_dir, f'{ticket_key}_完整分析报告_{ts}.md')
        with open(output_file, 'w', encoding='utf-8-sig') as f:
            f.write(report)
        print(f"    [生成跳过报告] {output_file}")
        return report, None

    knowledge_context = """## 报告输出要求

### 格式约束（必须遵守）
- 每个章节只能出现一次，编号必须连续
- 禁止出现重复章节（如两个 ## 三、或两个 ## 七）
- 禁止复制模板中的占位符文字

### 章节结构（必须按顺序输出）
## 一、JIRA 信息
【在此填写JIRA ticket信息、摘要、Issue Analysis等】
## 二、分析结论
【在此填写故障端、错误码、根因摘要】
## 三、关键日志片段
【在此填写日志路径和内容，格式：日志路径: extracted/xxx.log，行号:N】
## 四、根因分析
【在此填写详细根因分析】
## 五、整改建议
【在此填写修复建议表格】
## 六、补充说明
【在此填写日志完整性评估】
## 七、结论
【在此填写最终结论】

### 日志路径格式示例
【日志路径: {ticket_key}/extracted/dk_service.log，行号:123】
```
日志原文内容
```

"""

    ts_ai = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    output_file = os.path.join(analysis_output_dir, f'{ticket_key}_完整分析报告_{ts_ai}.md')
    knowledge_context = knowledge_context.format(ticket_key=ticket_key).replace('\uff1a', ':').replace('\uff0c', ',').replace('\u3002', '.').replace('\u3001', ',').replace('\uff08', '(').replace('\uff09', ')').replace('\u201c', '"').replace('\u201d', '"')

    header = "You are a CCC CarKey digital key fault analysis engineer.\n\nOutput a 7-section report in Chinese. Section format:\n## 一、JIRA 信息\n## 二、分析结论 (fault side, error code, root cause)\n## 三、关键日志片段\n## 四、根因分析\n## 五、整改建议 (table format)\n## 六、补充说明\n## 七、结论\n\nConstraints: No placeholders like 'to be filled', no 'see above'. Analyze based on logs."
    full_prompt = header + jira_section + "\n\n---\n\n"
    if knowledge_section:
        full_prompt += knowledge_section + "\n\n---\n\n"
    full_prompt += knowledge_context + "\n\n---\n\n" + "## 日志文件内容\n\n" + prompt_text

    # 日志过少时使用简化 prompt（跳过知识库，AI 快速返回）
    if is_low_log:
        print(f"    [日志过少] 文本={log_text_size}字节 < 1KB，使用简化 prompt")
        short_header = """你是 CCC CarKey 数字钥匙故障分析工程师。
基于 JIRA ticket 信息输出 7 章节完整分析报告（如日志确实不足，在各章节如实说明）。

重要约束：
1. 仅输出报告正文，禁止内部思考
2. 每个章节（## 一~七）只能出现一次，禁止重复
3. 禁止复制占位符文字（如"待补充"、"见上方"）
4. 第二章必须包含故障端+根因摘要
5. 第七章必须输出一段总结性文字

"""
        full_prompt = short_header + jira_section + "\n\n---\n\n" + knowledge_context + "\n\n---\n\n日志文件内容（极少或为二进制）：\n" + prompt_text

    try:
        MAX_TOKENS = 160000
        estimated_tokens = len(full_prompt) // 4
        if estimated_tokens > MAX_TOKENS:
            suffix = f"\n\n[prompt truncated: {estimated_tokens:,} tokens, limit {MAX_TOKENS:,}]"
            available = MAX_TOKENS * 4 - len(suffix)
            full_prompt = full_prompt[:available] + suffix

        prompt_file = os.path.join(tempfile.gettempdir(), f'ccc_prompt_{ticket_key}.txt')
        ps_script_file = os.path.join(tempfile.gettempdir(), f'ccc_ai_{ticket_key}.ps1')

        with open(prompt_file, 'w', encoding='utf-8-sig') as f:
            f.write(full_prompt)

        node_exe = os.path.join(os.environ.get('APPDATA', ''), 'npm', 'node_modules', 'opencode-ai', 'bin', 'opencode.exe')
        fallback = 'opencode'
        exe_path = node_exe if os.path.exists(node_exe) else fallback
        with open(ps_script_file, 'w', encoding='utf-8-sig') as f:
            f.write(f'Get-Content -LiteralPath "{prompt_file}" -Raw -Encoding UTF8 | & "{exe_path}" run --model {DEFAULT_MODEL} --format json 2>$null')

        print(f"    [调用 opencode] prompt_size={len(full_prompt)/1024:.0f}KB model={DEFAULT_MODEL}")
        t_opencode = time.time()
        
        MAX_RETRIES = 3
        result = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = subproc.run(
                    ['powershell', '-ExecutionPolicy', 'Bypass', '-File', ps_script_file],
                    capture_output=True, text=True, timeout=900
                )
                if result.returncode == 0 and result.stdout and result.stdout.strip():
                    print(f"      opencode返回: {time.time()-t_opencode:.1f}s (尝试 {attempt}/{MAX_RETRIES})")
                    break
                else:
                    print(f"      [尝试{attempt}] 返回码={result.returncode}, 重试中...")
                    if attempt < MAX_RETRIES:
                        time.sleep(5 * attempt)
            except subproc.TimeoutExpired:
                print(f"      [尝试{attempt}] 超时 (>15min), 重试中...")
                if attempt < MAX_RETRIES:
                    time.sleep(10 * attempt)
                result = None
            except Exception as e:
                print(f"      [尝试{attempt}] 异常: {e}, 重试中...")
                if attempt < MAX_RETRIES:
                    time.sleep(5 * attempt)
                result = None

        for fp in (prompt_file, ps_script_file):
            if os.path.exists(fp):
                try: os.remove(fp)
                except: pass

        if not result or result.returncode != 0 or not result.stdout:
            print(f"[AI] opencode 全部 {MAX_RETRIES} 次尝试失败")
            print(f"    [AI总计] {time.time()-t_ai_total:.1f}s")
            return None, None

        if result.returncode == 0 and result.stdout:
            ai_text = []
            try:
                for line in result.stdout.split('\n'):
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        if event.get('type') == 'text':
                            part = event.get('part', {})
                            if part.get('type') == 'text':
                                ai_text.append(part.get('text', ''))
                    except json.JSONDecodeError:
                        pass
                combined = '\n'.join(ai_text)
                if combined.strip():
                    final_report = combined
                    final_report = re.sub(r'<think>[\s\S]*?</think>', '', final_report)
                    final_report = re.sub(r'^让我先查看[\s\S]*?关键发现：\s*', '', final_report)
                    final_report = re.sub(r'^日志信息已收集完毕[\s\S]*?发现：\s*', '', final_report)
                    final_report = re.sub(r'^以下是基于[\s\S]*?分析：\s*', '', final_report)

                    lines = final_report.split('\n')
                    section_start = -1
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if re.match(r'^##\s+[一二三四五六七]', stripped):
                            section_start = i
                            break
                    if section_start >= 0:
                        final_report = '\n'.join(lines[section_start:])
                    else:
                        for i, line in enumerate(lines):
                            if re.match(r'^#{1,6}\s', line.strip()):
                                final_report = '\n'.join(lines[i:])
                                break

                    CHAPTER_NAMES = {
                        '一': '一、JIRA 信息',
                        '二': '二、分析结论',
                        '三': '三、关键日志片段',
                        '四': '四、根因分析',
                        '五': '五、整改建议',
                        '六': '六、补充说明',
                        '七': '七、结论',
                    }

                    heading_patterns = [
                        (r'^(#{1,6})\s+.*?(JIRA|jira).*$', r'## 一、JIRA 信息'),
                        (r'^(#{1,6})\s+.*?(分析结论|结论).*$', r'## 二、分析结论'),
                        (r'^(#{1,6})\s+.*?(关键日志|日志片段|证据链).*$', r'## 三、关键日志片段'),
                        (r'^(#{1,6})\s+.*?(根因|故障链条|故障分析).*$', r'## 四、根因分析'),
                        (r'^(#{1,6})\s+.*?(整改建议|修复建议).*$', r'## 五、整改建议'),
                        (r'^(#{1,6})\s+.*?(补充说明|日志完整性).*$', r'## 六、补充说明'),
                        (r'^(#{1,6})\s+.*?(结论).*$', r'## 七、结论'),
                    ]
                    for pat, repl in heading_patterns:
                        try:
                            final_report = re.sub(pat, repl, final_report, flags=re.MULTILINE)
                        except Exception as e:
                            print(f"    [正则错误] pattern={pat}, error={e}")
                            raise

                    has_log_path = '【日志路径' in final_report
                    if not has_log_path and log_snippets:
                        log_block = ['## 三、关键日志片段', '']
                        for s in log_snippets[:10]:
                            log_block.append(s)
                        log_block.append('')
                        final_report = final_report + '\n\n' + '\n'.join(log_block)

                    for unwanted in [
                        re.compile(r'#{1,6}\s*待确认.*', re.DOTALL),
                        re.compile(r'#{1,6}\s*快速总结.*', re.DOTALL),
                        re.compile(r'#{1,6}\s*输出文件.*', re.DOTALL),
                    ]:
                        final_report = unwanted.sub('', final_report)
                    final_report = re.sub(r'^- \[.\] .*\n?', '', final_report)
                    final_report = re.sub(r'\n{3,}', '\n\n', final_report).strip()

                    final_report = _ensure_complete_sections(final_report, jira_context)

                    if jira_context:
                        starts_with_chapter = re.match(r'^##\s+[一二三四五六七]、', final_report)
                        if starts_with_chapter:
                            first_chapter = starts_with_chapter.group(0)
                            if first_chapter != '## 一、':
                                print(f"    [修复] AI跳过章节，补充JIRA信息")
                                final_report = jira_context + "\n\n---\n\n" + final_report

                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(final_report)
                    print(f"[AI] 完整分析报告已生成: {output_file}")
                    print(f"    [AI总计] {time.time()-t_ai_total:.1f}s")
                    return output_file, final_report
                else:
                    print(f"    [调试] combined为空, ai_text条数={len(ai_text)}, 前200字符=[{combined[:200]}]")
            except Exception as e:
                import traceback
                print(f"    [AI解析错误] {e}")
                print(f"    [详细] {traceback.format_exc()[:500]}")
                print(f"    [stdout前500] {result.stdout[:500]}")
                print(f"    [AI总计] {time.time()-t_ai_total:.1f}s")
                return None, None
            print("[AI] No valid analysis content")
            print(f"    [AI总计] {time.time()-t_ai_total:.1f}s")
            return None, None
    except Exception as e:
        print(f"[AI] opencode error: {e}")
        import traceback
        print(f"    [详细] {traceback.format_exc()[:300]}")
        print(f"    [AI总计] {time.time()-t_ai_total:.1f}s")
        return None, None
