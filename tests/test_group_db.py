import sys
import os

# Add src to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.server.db import Database

def test_db():
    print("Initializing Database...")
    db = Database()
    
    print("Creating user 'testuser'...")
    db.register_user('testuser', 'password')
    
    print("Creating group 'TestGroup'...")
    group_id = db.create_group('TestGroup', 'testuser')
    print(f"Group created with ID: {group_id}")
    
    if group_id:
        print("Sending group message...")
        db.save_message('testuser', 'Hello Group DB', receiver=group_id, message_type='group')
        
        print("Checking for DB file...")
        files = os.listdir(os.path.join(os.path.dirname(__file__), '../src/server/groups_data'))
        print(f"Files in groups_data: {files}")
        
        if f'group_{group_id}.db' in files:
            print("SUCCESS: Group DB file created.")
        else:
            print("FAILURE: Group DB file NOT found.")

        print("Verifying History Retrieval...")
        history = db.get_history(message_type='group', group_id=group_id)
        print(f"History retrieved: {history}")
        if len(history) > 0 and history[0]['content'] == 'Hello Group DB':
             print("SUCCESS: Message retrieved from Group DB.")
        else:
             print("FAILURE: Could not retrieve message.")
            
    db.close()

if __name__ == "__main__":
    test_db()
