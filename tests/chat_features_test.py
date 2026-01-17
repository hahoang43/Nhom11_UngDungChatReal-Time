import sys
import time
import threading
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.server.server import ChatServer
from src.client.client import ChatClient
from src.common import protocol

def test_chat_features():
    print("Starting integration test...")
    
    # Clean up old DB if exists to start fresh
    db_path = os.path.join('src', 'server', 'chat.db')
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Old database removed.")

    # Start Server
    server = ChatServer()
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(1) # Wait for server to start

    # Start Clients
    alice_msgs = []
    bob_msgs = []
    charlie_msgs = []

    c1 = ChatClient()
    c2 = ChatClient()
    c3 = ChatClient()

    c1.on_message_received = lambda m, t=None, e=None: (alice_msgs.append((m, t, e)), print(f"Alice received: {m}"))
    c2.on_message_received = lambda m, t=None, e=None: (bob_msgs.append((m, t, e)), print(f"Bob received: {m}"))
    c3.on_message_received = lambda m, t=None, e=None: (charlie_msgs.append((m, t, e)), print(f"Charlie received: {m}"))

    print("Connecting clients (registering)...")
    c1.register('alice', 'pw123')
    time.sleep(0.5)
    c2.register('bob', 'pw123')
    time.sleep(0.5)
    c3.register('charlie', 'pw123')
    time.sleep(2) # Give more time for login and user list broadcast

    # 1. Test Private Chat: Alice -> Bob
    print("\n--- Testing Private Chat ---")
    c1.send_private('bob', 'Hello Bob, this is a secret.')
    time.sleep(2)
    
    # Filter messages correctly - check for payloads that contain 'secret'
    bob_private_msgs = [m for m, t, e in bob_msgs if t == protocol.MSG_PRIVATE or 'secret' in str(m)]
    charlie_private_msgs = [m for m, t, e in charlie_msgs if t == protocol.MSG_PRIVATE or 'secret' in str(m)]
    
    print(f"Bob private msgs: {bob_private_msgs}")
    print(f"Charlie msgs: {charlie_msgs}")

    assert len(bob_private_msgs) > 0, "Bob should have received at least one private message"
    assert any('secret' in str(m) for m in bob_private_msgs), "Bob should have received Alice's private message content"
    assert not any('secret' in str(m) for m in charlie_private_msgs), "Charlie should NOT have received Alice's private message"
    print("Private Chat Test Passed!")

    # 2. Test Group Chat: Alice creates group, Bob joins
    print("\n--- Testing Group Chat ---")
    c1.create_group('Team 11')
    time.sleep(1)
    
    # In a fresh DB, the first group ID is 1
    c2.join_group(1)
    time.sleep(1)
    
    c1.send_group(1, 'Hello Team 11!')
    time.sleep(2)
    
    bob_group_msgs = [m for m, t, e in bob_msgs if t == protocol.MSG_GROUP or 'Team 11!' in str(m)]
    charlie_group_msgs = [m for m, t, e in charlie_msgs if t == protocol.MSG_GROUP or 'Team 11!' in str(m)]
    
    print(f"Bob group msgs: {bob_group_msgs}")

    assert len(bob_group_msgs) > 0, "Bob should have received the group message"
    assert not any('Team 11!' in str(m) for m in charlie_group_msgs), "Charlie (non-member) should NOT have received the group message"
    print("Group Chat Test Passed!")

    # Cleanup
    c1.disconnect()
    c2.disconnect()
    c3.disconnect()
    time.sleep(0.5)
    server.stop()
    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    try:
        test_chat_features()
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
