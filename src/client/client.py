
# ChatClient sử dụng python-socketio để kết nối Flask-SocketIO server
import socketio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.common import protocol

class ChatClient:
    def __init__(self, host='127.0.0.1', port=8000):
        self.host = host
        self.port = port
        self.sio = socketio.Client()
        self.username = None
        self.running = False
        self.on_message_received = None
        self.on_login_response = None
        self.on_users_list_received = None
        self.on_groups_list_received = None
        self.on_server_response = None
        self.waiting_for_login = False
        self._register_events()

    def _register_events(self):
        @self.sio.event
        def connect():
            self.running = True
            print("[CLIENT] Connected to server.")

        @self.sio.event
        def disconnect():
            self.running = False
            print("[CLIENT] Disconnected from server.")
            if self.on_message_received:
                self.on_message_received("Disconnected from server.")

        @self.sio.on('message')
        def on_message(data):
            msg_type = data.get('type')
            payload = data.get('payload')
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

    def connect(self, username, password='default'):
        try:
            self.username = username
            self.waiting_for_login = True
            self.sio.connect(f"http://{self.host}:{self.port}")
            login_msg = {
                'type': protocol.MSG_LOGIN,
                'payload': {'username': username, 'password': password}
            }
            self.sio.emit('message', login_msg)
            return True
        except Exception as e:
            print(f"[CLIENT ERROR] Connection failed: {e}")
            return False

    def register(self, username, password):
        try:
            self.username = username
            self.waiting_for_login = True
            self.sio.connect(f"http://{self.host}:{self.port}")
            register_msg = {
                'type': protocol.MSG_REGISTER,
                'payload': {'username': username, 'password': password}
            }
            self.sio.emit('message', register_msg)
            return True
        except Exception as e:
            print(f"[CLIENT ERROR] Connection failed: {e}")
            return False

    def send_message(self, message):
        if self.running:
            msg_data = {'type': protocol.MSG_TEXT, 'payload': message}
            self.sio.emit('message', msg_data)

    def send_private(self, receiver, message):
        if self.running:
            msg_data = {
                'type': protocol.MSG_PRIVATE,
                'payload': {'receiver': receiver, 'content': message}
            }
            self.sio.emit('message', msg_data)

    def send_group(self, group_id, message):
        if self.running:
            msg_data = {
                'type': protocol.MSG_GROUP,
                'payload': {'group_id': group_id, 'content': message}
            }
            self.sio.emit('message', msg_data)

    def create_group(self, group_name):
        if self.running:
            self.sio.emit('message', {
                'type': protocol.MSG_GROUP_CREATE,
                'payload': group_name
            })

    def join_group(self, group_id):
        if self.running:
            self.sio.emit('message', {
                'type': protocol.MSG_GROUP_JOIN,
                'payload': group_id
            })

    def leave_group(self, group_id):
        if self.running:
            self.sio.emit('message', {
                'type': protocol.MSG_GROUP_LEAVE,
                'payload': group_id
            })

    def delete_group(self, group_id):
        if self.running:
            self.sio.emit('message', {
                'type': 'GROUP_DELETE',
                'payload': {'group_id': group_id}
            })

    def disconnect(self):
        if self.running:
            try:
                self.sio.emit('message', {'type': protocol.MSG_EXIT, 'payload': ''})
            except:
                pass
            self.sio.disconnect()
            self.running = False
            if self.on_message_received:
                self.on_message_received("Disconnected from server.")
