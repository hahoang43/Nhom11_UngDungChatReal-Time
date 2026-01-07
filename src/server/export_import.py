#!/usr/bin/env python3
"""
Script để export/import lịch sử chat giữa các máy
Sử dụng: python export_import.py [export|import] [filepath]
"""

import sys
import os
from db import Database

def main():
    if len(sys.argv) < 3:
        print("Sử dụng: python export_import.py [export|import] [filepath]")
        print("Ví dụ:")
        print("  python export_import.py export chat_history.json")
        print("  python export_import.py import chat_history.json")
        return

    action = sys.argv[1].lower()
    filepath = sys.argv[2]

    if action not in ['export', 'import']:
        print("Action phải là 'export' hoặc 'import'")
        return

    try:
        with Database() as db:
            if action == 'export':
                count = db.export_messages(filepath)
                print(f"✅ Đã xuất thành công {count} tin nhắn vào {filepath}")
            elif action == 'import':
                if not os.path.exists(filepath):
                    print(f"❌ File {filepath} không tồn tại")
                    return
                count = db.import_messages(filepath)
                print(f"✅ Đã nhập thành công {count} tin nhắn từ {filepath}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    main()