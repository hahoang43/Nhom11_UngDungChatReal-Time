
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

class TestGroupMembers(unittest.TestCase):
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
        client.get_received()
        
    def test_group_members_fetch(self):
        # 1. Create a group with 3 members
        group_name = "Team Alpha"
        members = ['UserB', 'UserC']
        
        self.client1.emit('message', {
            'type': protocol.MSG_GROUP_CREATE,
            'payload': {
                'name': group_name,
                'members': members
            }
        })
        
        # Find group_id from response
        received = self.client1.get_received()
        group_id = None
        for msg in received:
            if 'args' in msg:
                args = msg['args']
                if isinstance(args, list) and len(args) > 0:
                    data = args[0]
                elif isinstance(args, dict):
                    data = args
                else:
                    data = {}
            else:
                data = {}
            
            if data.get('type') == protocol.MSG_GROUPS_LIST:
                for g in data.get('payload', []):
                    if g['name'] == group_name:
                        group_id = g['id']
                        break
        
        self.assertIsNotNone(group_id, "Group should be created")

        # 2. Request group members as UserA
        self.client1.emit('message', {
            'type': protocol.MSG_GROUP_MEMBERS,
            'payload': {'group_id': group_id}
        })

        # 3. Verify Response
        received_mem = self.client1.get_received()
        found_response = False
        member_list = []
        
        for msg in received_mem:
            if 'args' in msg:
                args = msg['args']
                if isinstance(args, list) and len(args) > 0:
                    data = args[0]
                elif isinstance(args, dict):
                    data = args
                else:
                    data = {}
            else:
                data = {}

            if data.get('type') == protocol.MSG_GROUP_MEMBERS_RESPONSE:
                payload = data.get('payload')
                if payload['group_id'] == group_id:
                    found_response = True
                    member_list = payload['members']
                    break
        
        self.assertTrue(found_response, "Should receive MSG_GROUP_MEMBERS_RESPONSE")
        self.assertEqual(len(member_list), 3, "Should have 3 members")
        
        usernames = [m['username'] for m in member_list]
        self.assertIn('UserA', usernames)
        self.assertIn('UserB', usernames)
        self.assertIn('UserC', usernames)
        
        # Check structure fields
        first_mem = member_list[0]
        self.assertIn('display_name', first_mem)
        self.assertIn('status', first_mem) # online/offline

if __name__ == '__main__':
    unittest.main()
