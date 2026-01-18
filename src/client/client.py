import socket
import threading
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.common import protocol

class ChatClient:
    def delete_group(self, group_id):
        """Request to delete a group (creator only)"""
        if self.socket and self.running:
            try:
                protocol.send_json(self.socket, {
                    'type': 'GROUP_DELETE',
                    'payload': {'group_id': group_id}
                })
            except Exception as e:
                print(f"[CLIENT ERROR] Delete group failed: {e}")

    def __init__(self, host='127.0.0.1', port=protocol.PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.running = False
        self.on_message_received = None # Callback function
        self.on_login_response = None # Callback for login/register response
        self.on_users_list_received = None # Callback for user list
        self.on_groups_list_received = None # Callback for group list
        self.on_server_response = None # Callback for SUCCESS/ERROR messages
        self.waiting_for_login = False

    def connect(self, username, password='default'):
        """Connects to the server and performs login"""
        # ... (rest of connect remains same)
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.username = username
            self.running = True
            self.waiting_for_login = True

            # Send Login Message with username and password
            login_msg = {
                'type': protocol.MSG_LOGIN, 
                'payload': {'username': username, 'password': password}
            }
            protocol.send_json(self.socket, login_msg)

            # Start listening thread
            receive_thread = threading.Thread(target=self.receive_loop)
            receive_thread.daemon = True
            receive_thread.start()
            
            return True
        except Exception as e:
            print(f"[CLIENT ERROR] Connection failed: {e}")
            return False

    def register(self, username, password):
        """Connects to the server and performs registration"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.username = username
            self.running = True
            self.waiting_for_login = True

            # Send Register Message with username and password
            register_msg = {
                'type': protocol.MSG_REGISTER, 
                'payload': {'username': username, 'password': password}
            }
            protocol.send_json(self.socket, register_msg)

            # Start listening thread
            receive_thread = threading.Thread(target=self.receive_loop)
            receive_thread.daemon = True
            receive_thread.start()
            
            return True
        except Exception as e:
            print(f"[CLIENT ERROR] Connection failed: {e}")
            return False

    def send_message(self, message):
        """Sends a public text message to the server"""
        if self.socket and self.running:
            msg_data = {'type': protocol.MSG_TEXT, 'payload': message}
            try:
                protocol.send_json(self.socket, msg_data)
            except Exception as e:
                print(f"[CLIENT ERROR] Send failed: {e}")
                self.disconnect()

    def send_private(self, receiver, message):
        """Sends a private message to a specific user"""
        if self.socket and self.running:
            msg_data = {
                'type': protocol.MSG_PRIVATE,
                'payload': {'receiver': receiver, 'content': message}
            }
            try:
                protocol.send_json(self.socket, msg_data)
            except Exception as e:
                print(f"[CLIENT ERROR] Private send failed: {e}")

    def send_group(self, group_id, message):
        """Sends a message to a group"""
        if self.socket and self.running:
            msg_data = {
                'type': protocol.MSG_GROUP,
                'payload': {'group_id': group_id, 'content': message}
            }
            try:
                protocol.send_json(self.socket, msg_data)
            except Exception as e:
                print(f"[CLIENT ERROR] Group send failed: {e}")

    def create_group(self, group_name):
        """Request to create a group"""
        if self.socket and self.running:
            try:
                protocol.send_json(self.socket, {
                    'type': protocol.MSG_GROUP_CREATE, 
                    'payload': group_name
                })
            except Exception as e:
                print(f"[CLIENT ERROR] Create group failed: {e}")

    def join_group(self, group_id):
        """Request to join a group"""
        if self.socket and self.running:
            try:
                protocol.send_json(self.socket, {
                    'type': protocol.MSG_GROUP_JOIN, 
                    'payload': group_id
                })
            except Exception as e:
                print(f"[CLIENT ERROR] Join group failed: {e}")

    def leave_group(self, group_id):
        """Request to leave a group"""
        if self.socket and self.running:
            try:
                protocol.send_json(self.socket, {
                    'type': protocol.MSG_GROUP_LEAVE, 
                    'payload': group_id
                })
            except Exception as e:
                print(f"[CLIENT ERROR] Leave group failed: {e}")

    def receive_loop(self):
        """Background thread to receive messages"""
        while self.running:
            try:
                message = protocol.receive_json(self.socket)
                if message is None:
                    break
                
                msg_type = message.get('type')
                payload = message.get('payload')
                
                # Handle login/register responses
                if self.waiting_for_login:
                    if msg_type == 'LOGIN_SUCCESS':
                        self.waiting_for_login = False
                        if self.on_login_response:
                            self.on_login_response(True, payload)
                    elif msg_type == 'ERROR':
                        self.waiting_for_login = False
                        if self.on_login_response:
                            self.on_login_response(False, payload)
                        self.disconnect()
                    elif msg_type == protocol.MSG_TEXT:
                        if self.on_message_received:
                            self.on_message_received(payload)
                else:
                    # Normal message handling
                    if msg_type == protocol.MSG_TEXT:
                        if self.on_message_received:
                            self.on_message_received(payload)
                    elif msg_type == protocol.MSG_PRIVATE:
                        sender = payload.get('sender')
                        content = payload.get('content')
                        if self.on_message_received:
                            self.on_message_received(f"[Private] {sender}: {content}", msg_type, sender)
                    elif msg_type == protocol.MSG_GROUP:
                        sender = payload.get('sender')
                        group_id = payload.get('group_id')
                        content = payload.get('content')
                        if self.on_message_received:
                            self.on_message_received(f"[Group {group_id}] {sender}: {content}", msg_type, group_id)
                    elif msg_type == protocol.MSG_USERS_LIST:
                        if self.on_users_list_received:
                            self.on_users_list_received(payload)
                    elif msg_type == protocol.MSG_GROUPS_LIST:
                        if self.on_groups_list_received:
                            self.on_groups_list_received(payload)
                    elif msg_type in ['SUCCESS', 'ERROR']:
                        if self.on_server_response:
                            self.on_server_response(msg_type, payload)
            except Exception as e:
                print(f"[CLIENT ERROR] Receive error: {e}")
                break
        
        self.disconnect()

    def disconnect(self):
        """Closes the connection"""
        self.running = False
        if self.socket:
            try:
                protocol.send_json(self.socket, {'type': protocol.MSG_EXIT, 'payload': ''})
            except:
                pass
            self.socket.close()
            self.socket = None
        if self.on_message_received:
            self.on_message_received("Disconnected from server.")
