"""
Script test database SQLite
Chạy script này để kiểm tra các chức năng của database
"""

import sys
import os
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.server.db import Database

def test_database():
    """Test các chức năng của database"""
    print("=" * 50)
    print("TEST DATABASE SQLITE")
    print("=" * 50)
    
    db = Database()
    
    try:
        # Test 1: Đăng ký user mới
        print("\n1. Test đăng ký user:")
        result = db.register_user("testuser", "password123")
        print(f"   Đăng ký 'testuser': {'Thành công' if result else 'Thất bại (có thể đã tồn tại)'}")
        
        # Test 2: Đăng ký user đã tồn tại
        result2 = db.register_user("testuser", "password123")
        print(f"   Đăng ký lại 'testuser': {'Thành công' if result2 else 'Thất bại (đúng như mong đợi)'}")
        
        # Test 3: Đăng nhập với mật khẩu đúng
        print("\n2. Test đăng nhập:")
        login1 = db.login_user("testuser", "password123")
        print(f"   Đăng nhập với mật khẩu đúng: {'Thành công' if login1 else 'Thất bại'}")
        
        # Test 4: Đăng nhập với mật khẩu sai
        login2 = db.login_user("testuser", "wrongpassword")
        print(f"   Đăng nhập với mật khẩu sai: {'Thành công' if login2 else 'Thất bại (đúng như mong đợi)'}")
        
        # Test 5: Kiểm tra user tồn tại
        print("\n3. Test kiểm tra user:")
        exists1 = db.user_exists("testuser")
        exists2 = db.user_exists("nonexistent")
        print(f"   'testuser' tồn tại: {exists1}")
        print(f"   'nonexistent' tồn tại: {exists2}")
        
        # Test 6: Lưu tin nhắn
        print("\n4. Test lưu tin nhắn:")
        db.save_message("testuser", "Xin chào mọi người!", message_type='public')
        db.save_message("testuser", "Đây là tin nhắn riêng", receiver="otheruser", message_type='private')
        print("   Đã lưu 2 tin nhắn (1 public, 1 private)")
        
        # Test 7: Lấy lịch sử chat
        print("\n5. Test lấy lịch sử chat:")
        history = db.get_history(limit=10, message_type='public')
        print(f"   Số tin nhắn công khai: {len(history)}")
        for msg in history:
            print(f"   - [{msg['timestamp']}] {msg['sender']}: {msg['content']}")
        
        # Test 8: Lấy thông tin user
        print("\n6. Test lấy thông tin user:")
        user_info = db.get_user_info("testuser")
        if user_info:
            print(f"   Username: {user_info['username']}")
            print(f"   Created at: {user_info['created_at']}")
            print(f"   Last login: {user_info['last_login']}")
            print(f"   Is active: {user_info['is_active']}")
        
        # Test 9: Lấy danh sách users
        print("\n7. Test lấy danh sách users:")
        users = db.get_all_users()
        print(f"   Tổng số users: {len(users)}")
        for user in users[:5]:  # Hiển thị 5 user đầu
            print(f"   - {user['username']} (created: {user['created_at']})")
        
        # Test 10: Đếm tin nhắn
        print("\n8. Test đếm tin nhắn:")
        total_messages = db.get_message_count()
        user_messages = db.get_message_count("testuser")
        print(f"   Tổng số tin nhắn: {total_messages}")
        print(f"   Tin nhắn của 'testuser': {user_messages}")
        
        print("\n" + "=" * 50)
        print("TẤT CẢ CÁC TEST ĐÃ HOÀN THÀNH!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[ERROR] Lỗi khi test database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_database()

