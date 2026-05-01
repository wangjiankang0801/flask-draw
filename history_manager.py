# history_manager.py
import json
import os
from config import HISTORY_FILE

def load_history():
    """返回历史记录列表，按时间升序"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_history_entry(entry):
    """添加一条记录，并保持最多 50 条"""
    history = load_history()
    history.append(entry)
    if len(history) > 50:
        history = history[-50:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
