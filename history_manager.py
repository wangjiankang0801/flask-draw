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

def delete_history_entries(indices):
    """删除指定索引的历史记录（索引是从新到旧排列的，需要转换为从旧到新）"""
    history = load_history()
    # API 返回的是倒序（最新的在前），indices 对应的是倒序后的索引
    # 需要转换为原始列表的索引
    total = len(history)
    original_indices = set()
    for idx in indices:
        if 0 <= idx < total:
            original_indices.add(total - 1 - idx)
    # 保留不在删除列表中的记录
    new_history = [item for i, item in enumerate(history) if i not in original_indices]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_history, f, ensure_ascii=False, indent=2)
