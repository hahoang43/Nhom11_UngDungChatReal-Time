import socket
import threading
import sys
import os
import json
import base64

# Add project root to path to import common modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.common import protocol
from src.server import websocket_handler
from src.server.db import Database

class ChatServer:
    def start_file_download_server(self, port=8000):
        import urllib.parse
        from http.server import SimpleHTTPRequestHandler, HTTPServer
        files_dir = self.files_dir
        class FileDownloadHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == '/download':
                    params = urllib.parse.parse_qs(parsed.query)
                    filename = params.get('filename', [None])[0]
                    if not filename:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'Missing filename')
                        return
                    safe_name = os.path.basename(filename)
                    file_path = os.path.join(files_dir, safe_name)
                    if not os.path.isfile(file_path):
                        self.send_response(404)
                        self.end_headers()
                        self.wfile.write(b'File not found')
                        return
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/octet-stream')
                    self.send_header('Content-Disposition', f'attachment; filename="{safe_name}"')
                    self.end_headers()
                    with open(file_path, 'rb') as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                else:
                    self.send_response(404)
                    self.end_headers()
        def run_server():
            httpd = HTTPServer(('0.0.0.0', port), FileDownloadHandler)
            print(f"[DOWNLOAD] File download server running on port {port}")
            httpd.serve_forever()
        t = threading.Thread(target=run_server, daemon=True)
        t.start()

    def __init__(self, host='0.0.0.0', port=protocol.PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {} # Dictionary to map socket -> username
        self.client_types = {} # Dictionary to map socket -> 'tcp' or 'ws'
        self.file_transfers = {} # Dictionary to track file transfers: socket -> file_data
        self.db = Database()
        self.lock = threading.Lock()
        self.running = True
        # Tạo thư mục lưu file ở ngoài src để tránh bị reload
        self.files_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/received_files'))
        os.makedirs(self.files_dir, exist_ok=True)

    def start(self):
        """Starts the server listening loop"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[SERVER] Listening on {self.host}:{self.port}")

            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"[CONNECTION] New connection from {client_address}")
                    
                    # Start a new thread for this client
                    thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                    thread.daemon = True
                    thread.start()
                except OSError:
                    break

        except Exception as e:
            print(f"[ERROR] Server failed to start: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stops the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self.db:
            self.db.close()
        print("[SERVER] Server stopped.")

    def handle_client(self, client_socket):
        """Main loop for handling a single client (TCP or WebSocket)"""
        username = None
        client_type = 'tcp'
        
        try:
            # Peek at the first few bytes to determine protocol
            first_bytes = client_socket.recv(10, socket.MSG_PEEK)
            
            if first_bytes.startswith(b'GET'):
                client_type = 'ws'
                # Read the full handshake request
                data = client_socket.recv(4096)
                if not websocket_handler.handshake(client_socket, data):
                    print("[ERROR] WebSocket handshake failed")
                    client_socket.close()
                    return
                print("[WS] WebSocket Handshake successful")
            
            with self.lock:
                self.client_types[client_socket] = client_type

            # --- LOGIN PHASE ---
            request = None
            if client_type == 'tcp':
                request = protocol.receive_json(client_socket)
            else:
                # For WS, wait for the first frame which should be the login JSON
                raw_msg = websocket_handler.receive_frame(client_socket)
                if raw_msg:
                    try:
                        request = json.loads(raw_msg)
                    except json.JSONDecodeError:
                        pass

            # Handle LOGIN or REGISTER request
            if request and request.get('type') in [protocol.MSG_LOGIN, protocol.MSG_REGISTER]:
                msg_type = request.get('type')
                payload = request.get('payload')
                
                # Support both old format (just username) and new format (dict with username/password)
                if isinstance(payload, dict):
                    username = payload.get('username', '')
                    password = payload.get('password', '')
                else:
                    # Backward compatibility: if payload is just a string, treat as username
                    username = payload if payload else ''
                    password = 'default'  # Default password for backward compatibility
                
                if not username:
                    error_msg = {'type': 'ERROR', 'payload': 'Username is required'}
                    if client_type == 'tcp':
                        protocol.send_json(client_socket, error_msg)
                    else:
                        websocket_handler.send_frame(client_socket, json.dumps(error_msg))
                    client_socket.close()
                    return
                
                login_success = False
                
                if msg_type == protocol.MSG_REGISTER:
                    # Registration
                    if self.db.user_exists(username):
                        error_msg = {'type': 'ERROR', 'payload': 'Username already exists'}
                        if client_type == 'tcp':
                            protocol.send_json(client_socket, error_msg)
                        else:
                            websocket_handler.send_frame(client_socket, json.dumps(error_msg))
                        client_socket.close()
                        return
                    else:
                        if self.db.register_user(username, password):
                            login_success = True
                            print(f"[REGISTER] New user '{username}' registered via {client_type.upper()}.")
                        else:
                            error_msg = {'type': 'ERROR', 'payload': 'Registration failed'}
                            if client_type == 'tcp':
                                protocol.send_json(client_socket, error_msg)
                            else:
                                websocket_handler.send_frame(client_socket, json.dumps(error_msg))
                            client_socket.close()
                            return
                else:
                    # Login
                    if self.db.user_exists(username):
                        if self.db.login_user(username, password):
                            login_success = True
                        else:
                            error_msg = {'type': 'ERROR', 'payload': 'Invalid username or password'}
                            if client_type == 'tcp':
                                protocol.send_json(client_socket, error_msg)
                            else:
                                websocket_handler.send_frame(client_socket, json.dumps(error_msg))
                            client_socket.close()
                            return
                    else:
                        # Auto-register for backward compatibility (if no password provided or default password)
                        if password == 'default' or not password:
                            if self.db.register_user(username, password or 'default'):
                                login_success = True
                                print(f"[AUTO-REGISTER] User '{username}' auto-registered via {client_type.upper()}.")
                            else:
                                error_msg = {'type': 'ERROR', 'payload': 'Auto-registration failed'}
                                if client_type == 'tcp':
                                    protocol.send_json(client_socket, error_msg)
                                else:
                                    websocket_handler.send_frame(client_socket, json.dumps(error_msg))
                                client_socket.close()
                                return
                        else:
                            error_msg = {'type': 'ERROR', 'payload': 'User does not exist. Please register first.'}
                            if client_type == 'tcp':
                                protocol.send_json(client_socket, error_msg)
                            else:
                                websocket_handler.send_frame(client_socket, json.dumps(error_msg))
                            client_socket.close()
                            return
                
                if login_success:
                    with self.lock:
                        self.clients[client_socket] = username
                    
                    print(f"[LOGIN] User '{username}' logged in via {client_type.upper()}.")
                    
                    # Send success message
                    success_msg = {'type': 'LOGIN_SUCCESS', 'payload': f'Welcome {username}!'}
                    if client_type == 'tcp':
                        protocol.send_json(client_socket, success_msg)
                    else:
                        websocket_handler.send_frame(client_socket, json.dumps(success_msg))
                    

                    # Gửi lịch sử chat công khai
                    public_history = self.db.get_history(20, message_type='public', username=username)
                    for row in public_history:
                        sender = row['sender']
                        content = row['content']
                        timestamp = row['timestamp']
                        history_msg = {
                            'type': protocol.MSG_TEXT,
                            'payload': f"[{timestamp}] {sender}: {content}"
                        }
                        if client_type == 'tcp':
                            protocol.send_json(client_socket, history_msg)
                        else:
                            websocket_handler.send_frame(client_socket, json.dumps(history_msg))

                    # Gửi lịch sử chat cá nhân (private)
                    private_history = self.db.get_history(20, message_type='private', username=username)
                    for row in private_history:
                        sender = row['sender']
                        receiver = row['receiver']
                        content = row['content']
                        timestamp = row['timestamp']
                        private_msg = {
                            'type': protocol.MSG_PRIVATE,
                            'payload': {
                                'sender': sender,
                                'receiver': receiver,
                                'content': content,
                                'timestamp': timestamp
                            }
                        }
                        if client_type == 'tcp':
                            protocol.send_json(client_socket, private_msg)
                        else:
                            websocket_handler.send_frame(client_socket, json.dumps(private_msg))

                    self.broadcast({
                        'type': protocol.MSG_TEXT, 
                        'payload': f"Server: {username} has joined the chat."
                    })
                    
                    # Broadcast updated users list
                    self.broadcast_users_list()
                    self.broadcast_groups_list()
            else:
                print(f"[ERROR] Invalid login attempt from {client_type}.")
                client_socket.close()
                return

            # --- MESSAGE LOOP ---
            while True:
                message = None
                if client_type == 'tcp':
                    message = protocol.receive_json(client_socket)
                else:
                    raw_msg = websocket_handler.receive_frame(client_socket)
                    if raw_msg:
                        try:
                            message = json.loads(raw_msg)
                        except json.JSONDecodeError:
                            message = {'type': protocol.MSG_TEXT, 'payload': raw_msg}
                    else:
                        message = None

                if message is None:
                    break

                # Khi client yêu cầu lịch sử chat nhóm/cá nhân
                if message.get('type') == 'HISTORY_REQUEST':
                    payload = message.get('payload', {})
                    history_type = payload.get('history_type')
                    target = payload.get('target')
                    if history_type == 'private' and target:
                        private_history = self.db.get_history(50, message_type='private', username=target)
                        for row in private_history:
                            sender = row['sender']
                            receiver = row['receiver']
                            content = row['content']
                            timestamp = row['timestamp']
                            private_msg = {
                                'type': protocol.MSG_PRIVATE,
                                'payload': {
                                    'sender': sender,
                                    'receiver': receiver,
                                    'content': content,
                                    'timestamp': timestamp
                                }
                            }
                            self._send_to_client(client_socket, private_msg)
                    elif history_type == 'group' and target:
                        group_history = self.db.get_history(50, message_type='group', group_id=target)
                        for row in group_history:
                            sender = row['sender']
                            content = row['content']
                            timestamp = row['timestamp']
                            group_msg = {
                                'type': protocol.MSG_GROUP,
                                'payload': {
                                    'sender': sender,
                                    'group_id': target,
                                    'content': content,
                                    'timestamp': timestamp
                                }
                            }
                            self._send_to_client(client_socket, group_msg)
                    continue

                if message.get('type') == protocol.MSG_EXIT:
                    break

                if message.get('type') == protocol.MSG_TEXT:
                    content = message.get('payload')
                    print(f"[{username}] {content}")
                    self.db.save_message(username, content, message_type='public')
                    self.broadcast({
                        'type': protocol.MSG_TEXT,
                        'payload': f"{username}: {content}"
                    }, exclude_socket=client_socket)

                elif message.get('type') == protocol.MSG_PRIVATE:
                    payload = message.get('payload', {})
                    receiver = payload.get('receiver')
                    content = payload.get('content')
                    
                    print(f"[PRIVATE] {username} to {receiver}: {content}")
                    self.db.save_message(username, content, receiver=receiver, message_type='private')
                    
                    target_msg = {
                        'type': protocol.MSG_PRIVATE,
                        'payload': {'sender': username, 'content': content}
                    }
                    
                    # Find receiver socket
                    target_socket = self._get_socket_by_username(receiver)
                    if target_socket:
                        self._send_to_client(target_socket, target_msg)
                    else:
                        error_msg = {'type': 'ERROR', 'payload': f"User {receiver} is offline."}
                        self._send_to_client(client_socket, error_msg)

                elif message.get('type') == protocol.MSG_GROUP:
                    payload = message.get('payload', {})
                    group_id = payload.get('group_id')
                    content = payload.get('content')
                    
                    print(f"[GROUP {group_id}] {username}: {content}")
                    self.db.save_message(username, content, receiver=group_id, message_type='group')
                    
                    group_msg = {
                        'type': protocol.MSG_GROUP,
                        'payload': {'sender': username, 'group_id': group_id, 'content': content}
                    }
                    self.broadcast_to_group(group_id, group_msg, exclude_socket=client_socket)

                elif message.get('type') == protocol.MSG_GROUP_CREATE:
                    group_name = message.get('payload')
                    group_id = self.db.create_group(group_name, username)
                    if group_id:
                        self._send_to_client(client_socket, {
                            'type': 'SUCCESS', 
                            'payload': f"Group '{group_name}' created with ID {group_id}"
                        })
                        self.broadcast_groups_list()
                    else:
                        self._send_to_client(client_socket, {'type': 'ERROR', 'payload': "Failed to create group"})

                elif message.get('type') == protocol.MSG_GROUP_JOIN:
                    group_id = message.get('payload')
                    if self.db.add_member_to_group(group_id, username):
                        self._send_to_client(client_socket, {
                            'type': 'SUCCESS', 
                            'payload': f"Joined group {group_id}"
                        })
                    else:
                        self._send_to_client(client_socket, {'type': 'ERROR', 'payload': "Failed to join group"})

                elif message.get('type') == protocol.MSG_GROUP_LEAVE:
                    group_id = message.get('payload')
                    if self.db.remove_member_from_group(group_id, username):
                        self._send_to_client(client_socket, {
                            'type': 'SUCCESS', 
                            'payload': f"Left group {group_id}"
                        })
                    else:
                        self._send_to_client(client_socket, {'type': 'ERROR', 'payload': "Failed to leave group"})

                elif message.get('type') == protocol.MSG_FILE_REQUEST:
                    file_info = message.get('payload', {})
                    filename = file_info.get('filename')
                    filesize = file_info.get('filesize')
                    receiver = file_info.get('receiver')
                    print(f"[FILE] {username} sending file: {filename} ({filesize} bytes)")
                    filepath = os.path.join(self.files_dir, filename)
                    try:
                        f = open(filepath, 'wb')
                    except Exception as e:
                        print(f"[ERROR] Cannot open file for writing: {e}")
                        continue
                    with self.lock:
                        self.file_transfers[client_socket] = {
                            'sender': username,
                            'filename': filename,
                            'filesize': filesize,
                            'receiver': receiver,
                            'file': f
                        }
                elif message.get('type') == protocol.MSG_FILE_CHUNK:
                    chunk_data = message.get('payload', {})
                    chunk_b64 = chunk_data.get('data', '')
                    f = None
                    with self.lock:
                        if client_socket in self.file_transfers:
                            f = self.file_transfers[client_socket]['file']
                    if f:
                        try:
                            data = base64.b64decode(chunk_b64)
                            f.write(data)
                        except Exception as e:
                            print(f"[ERROR] Write chunk failed: {e}")
                elif message.get('type') == protocol.MSG_FILE_END:
                    file_data = None
                    with self.lock:
                        if client_socket in self.file_transfers:
                            file_data = self.file_transfers[client_socket]
                            del self.file_transfers[client_socket]
                    if file_data:
                        f = file_data['file']
                        try:
                            f.close()
                        except Exception:
                            pass
                        filepath = os.path.join(self.files_dir, file_data['filename'])
                        if filepath:
                            file_msg = f"📎 File: {file_data['filename']} ({self._format_file_size(file_data['filesize'])})"
                            self.db.save_message(username, file_msg, message_type='public')
                            file_info = {
                                'type': protocol.MSG_FILE,
                                'payload': {
                                    'sender': username,
                                    'filename': file_data['filename'],
                                    'filesize': file_data['filesize'],
                                    'filepath': filepath,
                                    'message': f"{username} đã gửi file: {file_data['filename']}"
                                },
                                'encrypted': False
                            }
                            self.broadcast_file_info(file_info)

        except Exception as e:
            print(f"[ERROR] Error handling client {username}: {e}")
        finally:
            # Cleanup
            with self.lock:
                if client_socket in self.clients:
                    del self.clients[client_socket]
                if client_socket in self.client_types:
                    del self.client_types[client_socket]
                if client_socket in self.file_transfers:
                    del self.file_transfers[client_socket]
            
            client_socket.close()
            if username:
                print(f"[DISCONNECT] User '{username}' disconnected.")
                self.broadcast({
                    'type': protocol.MSG_TEXT, 
                    'payload': f"Server: {username} has left the chat."
                })
                self.broadcast_users_list()

    def _send_to_client(self, client_socket, message_dict):
        """Helper to send a message to a specific client"""
        c_type = self.client_types.get(client_socket, 'tcp')
        try:
            if c_type == 'tcp':
                protocol.send_json(client_socket, message_dict)
            else:
                websocket_handler.send_frame(client_socket, json.dumps(message_dict))
        except:
            pass

    def _get_socket_by_username(self, username):
        """Finds the socket associated with a username"""
        with self.lock:
            for sock, name in self.clients.items():
                if name == username:
                    return sock
        return None

    def broadcast_users_list(self):
        """Broadcasts the list of online users to everyone"""
        with self.lock:
            online_users = list(set(self.clients.values()))
        self.broadcast({
            'type': protocol.MSG_USERS_LIST,
            'payload': online_users
        })

    def broadcast_groups_list(self):
        """Broadcasts the list of all groups to everyone"""
        groups = self.db.get_all_groups()
        self.broadcast({
            'type': protocol.MSG_GROUPS_LIST,
            'payload': groups
        })

    def broadcast_to_group(self, group_id, message_dict, exclude_socket=None):
        """Broadcasts a message to all members of a group who are currently online"""
        members = self.db.get_group_members(group_id)
        with self.lock:
            for sock, name in self.clients.items():
                if name in members and sock != exclude_socket:
                    self._send_to_client(sock, message_dict)

    def broadcast(self, message_dict, exclude_socket=None):
        """Sends a message to all connected clients (TCP and WS)"""
        with self.lock:
            for client_sock in list(self.clients.keys()):
                if client_sock != exclude_socket:
                    c_type = self.client_types.get(client_sock, 'tcp')
                    
                    # Gửi tin nhắn đến client
                    msg_to_send = message_dict.copy()
                    
                    try:
                        if c_type == 'tcp':
                            protocol.send_json(client_sock, msg_to_send)
                        else:
                            # Send as JSON string in a WS frame
                            websocket_handler.send_frame(client_sock, json.dumps(msg_to_send))
                    except:
                        # If sending fails, assume client disconnected
                        client_sock.close()
                        if client_sock in self.clients:
                            del self.clients[client_sock]
                        if client_sock in self.client_types:
                            del self.client_types[client_sock]
    
    def _save_received_file(self, file_data, username):
        """Lưu file đã nhận được"""
        try:
            # Sắp xếp chunks theo thứ tự
            chunks = sorted(file_data['chunks'], key=lambda x: x[0])
            
            # Tạo tên file với timestamp để tránh trùng
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{file_data['filename']}"
            filepath = os.path.join(self.files_dir, safe_filename)
            
            # Ghép các chunks lại
            with open(filepath, 'wb') as f:
                for chunk_num, chunk_b64 in chunks:
                    chunk_data = base64.b64decode(chunk_b64)
                    f.write(chunk_data)
            
            print(f"[FILE] Saved file from {username}: {filepath}")
            return filepath
        except Exception as e:
            print(f"[ERROR] Failed to save file: {e}")
            return None
    
    def _format_file_size(self, size_bytes):
        """Format file size thành string dễ đọc"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
    
    def broadcast_file_info(self, file_info_dict):
        """Broadcast file info đến tất cả clients"""
        with self.lock:
            for client_sock in list(self.clients.keys()):
                c_type = self.client_types.get(client_sock, 'tcp')
                try:
                    if c_type == 'tcp':
                        protocol.send_json(client_sock, file_info_dict)
                    else:
                        websocket_handler.send_frame(client_sock, json.dumps(file_info_dict))
                except:
                    # If sending fails, assume client disconnected
                    client_sock.close()
                    if client_sock in self.clients:
                        del self.clients[client_sock]
                    if client_sock in self.client_types:
                        del self.client_types[client_sock]

if __name__ == "__main__":
    server = ChatServer()
    server.start_file_download_server(port=8000)
    server.start()
