#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书消息发送脚本
"""
import requests
import sys
import json

# 飞书Webhook地址
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/113f3db8-5da9-4efc-b95c-a197820ccd86"

def send_message(text):
    """发送文本消息到飞书"""
    payload = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, json=payload, timeout=10)
        result = response.json()
        
        if result.get("code") == 0:
            print("✅ 消息发送成功")
            return True
        else:
            print(f"❌ 发送失败: {result.get('msg', '未知错误')}")
            return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        send_message(message)
    else:
        print("用法: python feishu_send.py <消息内容>")
