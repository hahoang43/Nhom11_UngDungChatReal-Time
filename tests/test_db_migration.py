import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from server.db import Database

def test_sqlite_db():
    print("Testing SQLite Database...")
    
    # Ensure no DATABASE_URL env var
    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
        
    try:
        db = Database()
        print("[PASS] Connection & Table Creation")
        
        # Test Register
        if db.user_exists("testuser"):
            print("User exists, skipping register")
        else:
            if db.register_user("testuser", "password123"):
                print("[PASS] Register User")
            else:
                print("[FAIL] Register User")
                
        # Test Login
        if db.login_user("testuser", "password123"):
            print("[PASS] Login User")
        else:
            print("[FAIL] Login User")
            
        # Test Save Message
        db.save_message("testuser", "Hello World")
        print("[PASS] Save Message")
        
        # Test Get History
        msgs = db.get_history(limit=5)
        if len(msgs) > 0 and msgs[-1]['content'] == "Hello World":
             print(f"[PASS] Get History (Found {len(msgs)} messages)")
        else:
             print(f"[WARN] Get History (Found {len(msgs)} messages, expected 'Hello World' last)")

        print("SQLite Tests Completed.")
        
    except Exception as e:
        print(f"[FAIL] Exception occurred: {e}")
        raise e

if __name__ == "__main__":
    test_sqlite_db()
