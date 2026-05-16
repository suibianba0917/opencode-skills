import os, re, json, datetime

DBC_DIR = r'C:\Users\WP6KCF2\Documents\MDK\DBC\DBC_MY26_SR1.1'
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'cache', 'dbc_cache.json')
CACHE_DIR = os.path.dirname(CACHE_FILE)

ALWAYS_INCLUDE_MSGS = [
    'TBOX_DigitalKeyInfo', 'LDCU_EntrySysInfo', 'LDCU_BodySysSt1', 'LDCU_BodySysSt2',
    'DM_LDCU_BodySysSt1', 'DM_LDCU_BodySysSt2', 'DM_LDCU_CycleEventCtrl',
    'TBOX_BLE_CtrlFB', 'TBOX_VehSysSt',
]
RELEVANT_KEYWORDS = [
    'DigitalKey', 'Phone', 'PE', 'Unlock', 'Lock', 'Ranging',
    'UWB', 'BLE', 'TBOX', 'NFC', 'Carkey', 'CarKey',
    'Polling', 'Security', 'Authority', 'Enable', 'Welcome', 'Location',
    'FOB', 'Trunk', 'Charport', 'UWBKey',
]

def parse_dbc_file(filepath):
    messages = {}
    current = None

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        raw = f.read()

    for line in raw.split('\n'):
        line = line.strip()

        # BO_ <id> <name>: <dlc> <sender>
        m = re.match(r'^BO_ (\d+) (\S+?): (\d+) (\S+)', line)
        if m:
            if current and current['signals']:
                messages[current['id']] = current
            msg_id = int(m.group(1))
            current = {'id': msg_id, 'hex_id': f"0x{msg_id:03X}", 'name': m.group(2), 'signals': [], 'cycle_time_ms': None}
            continue

        # SG_ <name> : <start>|<len>@<byteorder><sign> ...
        m = re.match(r'^SG_ (\S+?) : (\d+)\|(\d+)@([01])([+-]) \((\S+),(\S+)\) \[(\S+)\|(\S+)\] "([^"]*)" ([\w,_]+)', line)
        if m and current:
            current['signals'].append({
                'name': m.group(1),
                'start_bit': int(m.group(2)),
                'length': int(m.group(3)),
                'byte_order': m.group(4),
                'signed': m.group(5) == '-',
                'factor': float(m.group(6)),
                'offset': float(m.group(7)),
                'min': m.group(8),
                'max': m.group(9),
                'unit': m.group(10),
                'receivers': m.group(11),
                'values': {},
            })
            continue

        # VAL_ <msg_id> <sig_name> <vals>;
        m = re.match(r'^VAL_ (\d+) (\S+?) (.+);$', line)
        if m and current and int(m.group(1)) == current['id']:
            for vm in re.finditer(r'(\d+)\s+"([^"]*)"', m.group(3)):
                for sig in current['signals']:
                    if sig['name'] == m.group(2):
                        sig['values'][int(vm.group(1))] = vm.group(2)
                        break
            continue

        # GenMsgCycleTime
        m = re.match(r'^BA_ "GenMsgCycleTime" BO_ (\d+) (\d+);', line)
        if m and current and int(m.group(1)) == current['id']:
            current['cycle_time_ms'] = int(m.group(2))
            continue

    if current and current['signals']:
        messages[current['id']] = current

    return messages

def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    all_messages = {}
    dbc_files = sorted([f for f in os.listdir(DBC_DIR) if f.endswith('.dbc')])

    print(f"解析 {len(dbc_files)} 个 DBC 文件...")

    for fname in dbc_files:
        fpath = os.path.join(DBC_DIR, fname)
        print(f"  {fname}...")
        for mid, msg in parse_dbc_file(fpath).items():
            if not msg['signals']:
                continue
            msg_always = any(k in msg['name'] for k in ALWAYS_INCLUDE_MSGS)
            sig_relevant = any(
                any(kw in sig['name'] for kw in RELEVANT_KEYWORDS)
                for sig in msg['signals']
            )
            if msg_always or sig_relevant:
                if mid not in all_messages:
                    all_messages[mid] = msg
                    print(f"    + {msg['hex_id']} {msg['name']} ({len(msg['signals'])} signals)")
                else:
                    print(f"    = {msg['hex_id']} {msg['name']} (already exists)")
            else:
                print(f"    - {msg['hex_id']} {msg['name']} (filtered out)")

    result = {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source_dir': DBC_DIR,
        'dbc_files': dbc_files,
        'message_count': len(all_messages),
        'messages': all_messages,
    }

    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n缓存已生成: {CACHE_FILE}")
    print(f"数字钥匙相关消息数: {len(all_messages)}")
    for mid, msg in sorted(all_messages.items()):
        print(f"  {msg['hex_id']} ({mid:4d}) {msg['name']} - {len(msg['signals'])} signals")

if __name__ == '__main__':
    main()
