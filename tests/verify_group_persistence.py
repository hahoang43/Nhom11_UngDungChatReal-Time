import unittest
import os
import sys
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.server.server import app, socketio, db

class TestGroupPersistence(unittest.TestCase):
    def setUp(self):
        # Use a temporary test database usually, but for now we'll rely on the logic 
        # not being destructive or we explicitly create unique data
        self.client = socketio.test_client(app)
        self.username = "test_user_persist_" + os.urandom(4).hex()
        self.password = "password123"
        self.group_name = "Test Group " + os.urandom(4).hex()

    def tearDown(self):
        # Clean up if possible (optional for now as we use unique names)
        pass

    def test_group_persistence(self):
        print(f"\n[TEST] Testing Persistence for {self.username}...")
        
        # 1. Register
        self.client.emit('message', {
            'type': 'REGISTER',
            'payload': {'username': self.username, 'password': self.password}
        })
        received = self.client.get_received()
        # Expect LOGIN_SUCCESS for register or ERROR if exists (we use unique name)
        
        # 2. Login
        self.client.emit('message', {
            'type': 'LOGIN',
            'payload': {'username': self.username, 'password': self.password}
        })
        received = self.client.get_received()
        login_ack = next((m for m in received if m['name'] == 'message' and m['args'].get('type') == 'LOGIN_SUCCESS'), None)
        self.assertIsNotNone(login_ack, "Login failed")

        # 3. Create Group
        self.client.emit('message', {
            'type': 'GROUP_CREATE',
            'payload': self.group_name
        })
        received = self.client.get_received()
        
        # We can find the group in the DB to be sure, or look at broadcast
        groups = db.get_all_groups()
        target_group = next((g for g in groups if g['name'] == self.group_name), None)
        self.assertIsNotNone(target_group, "Group was not created")
        group_id = target_group['id']
        print(f"[TEST] Created Group ID: {group_id}")

        # 4. Verify Immediate Membership (Creator auto-joins)
        members = db.get_group_members(group_id)
        self.assertIn(self.username, members, "User is not in group members table")

        # 5. Re-Login to check Persistence
        # Disconnect virtual client
        self.client.disconnect()
        
        # New Client Connection
        client2 = socketio.test_client(app)
        client2.emit('message', {
            'type': 'LOGIN',
            'payload': {'username': self.username, 'password': self.password}
        })
        
        received = client2.get_received()
        
        # Check for USER_GROUPS message
        user_groups_msg = next((m for m in received if m['name'] == 'message' and m['args'].get('type') == 'USER_GROUPS'), None)
        
        self.assertIsNotNone(user_groups_msg, "Did not receive USER_GROUPS message after re-login")
        payload = user_groups_msg['args']['payload']
        print(f"[TEST] Received USER_GROUPS payload: {payload}")
        
        self.assertIn(group_id, payload, f"Group ID {group_id} not preserved in USER_GROUPS: {payload}")
        print("[TEST] SUCCESS: Persistence verified!")

if __name__ == '__main__':
    unittest.main()
