
import unittest
import sys
import os
import json
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Monkeypatch DB_PATH to use a test database
import src.server.db as db_module
# Use a temp file for testing
import tempfile
test_db_fd, test_db_path = tempfile.mkstemp(suffix='.db')
os.close(test_db_fd)
db_module.DB_PATH = test_db_path

from src.server.server import app, socketio, db
from src.common import protocol

class TestGroupCreate(unittest.TestCase):
    def setUp(self):
        # Re-initialize database with the test path
        db.close()
        db.connect_sqlite()
        db.create_tables()
        self.client1 = socketio.test_client(app)
        self.client2 = socketio.test_client(app)
        self.client3 = socketio.test_client(app)
        
        # Create users
        self.register_and_login(self.client1, 'UserA', 'pass1')
        self.register_and_login(self.client2, 'UserB', 'pass2')
        self.register_and_login(self.client3, 'UserC', 'pass3')

    def tearDown(self):
        self.client1.disconnect()
        self.client2.disconnect()
        self.client3.disconnect()
        db.close()
        # Clean up database file
        try:
            os.remove(test_db_path)
        except:
            pass

    def register_and_login(self, client, username, password):
        # Register
        client.emit('message', {
            'type': protocol.MSG_REGISTER,
            'payload': {'username': username, 'password': password}
        })
        # Login
        client.emit('message', {
            'type': protocol.MSG_LOGIN,
            'payload': {'username': username, 'password': password}
        })
        # Consume welcome messages
        received = client.get_received()
        
    def test_create_group_min_members(self):
        # Try to create group with only 2 members (UserA + UserB)
        self.client1.emit('message', {
            'type': protocol.MSG_GROUP_CREATE,
            'payload': {
                'name': 'Small Group',
                'members': ['UserB']
            }
        })
        
        received = self.client1.get_received()
        # Should contain ERROR
        has_error = False
        for msg in received:
            if 'args' in msg:
                args = msg['args']
                if isinstance(args, list) and len(args) > 0:
                    data = args[0]
                elif isinstance(args, dict):
                    data = args
                else:
                    data = {}
                
                if data.get('type') == 'ERROR' and "3 thành viên" in data.get('payload', ''):
                    has_error = True
                    break
        self.assertTrue(has_error, "Should fail to create group with < 3 members")

    def test_create_group_success(self):
        # Create group with 3 members
        group_name = "My Test Group"
        members = ['UserB', 'UserC']
        
        self.client1.emit('message', {
            'type': protocol.MSG_GROUP_CREATE,
            'payload': {
                'name': group_name,
                'members': members
            }
        })
        
        # Check UserA response
        received_a = self.client1.get_received()
        created = False
        group_id = None
        for msg in received_a:
            if 'args' in msg:
                args = msg['args']
                if isinstance(args, list) and len(args) > 0:
                    data = args[0]
                elif isinstance(args, dict):
                    data = args
                else:
                    data = {}

                if data.get('type') == 'SUCCESS' and f"Group '{group_name}' created" in data.get('payload', ''):
                    created = True
                if data.get('type') == protocol.MSG_GROUPS_LIST:
                    for g in data['payload']:
                        if g['name'] == group_name:
                            group_id = g['id']
                        
        self.assertTrue(created, "UserA should receive creation success message")
        self.assertIsNotNone(group_id, "Group should allow finding ID")
        
        # Check UserB received notification
        received_b = self.client2.get_received()
        user_b_added = False
        for msg in received_b:
            if 'args' in msg:
                args = msg['args']
                if isinstance(args, list) and len(args) > 0:
                    data = args[0]
                elif isinstance(args, dict):
                    data = args
                else:
                    data = {}

                if data.get('type') == 'SUCCESS' and f"bạn đã được thêm vào nhóm '{group_name}'".lower() in data.get('payload', '').lower():
                    user_b_added = True
        self.assertTrue(user_b_added, "UserB should be notified")
        
        # Verify DB members
        db_members = db.get_group_members(group_id)
        self.assertIn('UserA', db_members)
        self.assertIn('UserB', db_members)
        self.assertIn('UserC', db_members)
        self.assertEqual(len(db_members), 3)

if __name__ == '__main__':
    unittest.main()
