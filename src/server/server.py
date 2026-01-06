import socket
import threading
import sys
import os

# Add project root to path to import common modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.common import protocol
from src.server import websocket_handler
from src.server.db import Database
import json

class ChatServer:
    def __init__(self, host='0.0.0.0', port=protocol.PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {} # Dictionary to map socket -> username
        self.client_types = {} # Dictionary to map socket -> 'tcp' or 'ws'
        self.db = Database()
        self.lock = threading.Lock()
        self.running = True

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
                    
                    # Send chat history to the new user
                    history = self.db.get_history(20, message_type='public', username=username)
                    for row in history:
                        # Access Row objects by column name
                        sender = row['sender']
                        content = row['content']
                        timestamp = row['timestamp']
                        history_msg = {'type': protocol.MSG_TEXT, 'payload': f"[{timestamp}] {sender}: {content}"}
                        if client_type == 'tcp':
                            protocol.send_json(client_socket, history_msg)
                        else:
                            websocket_handler.send_frame(client_socket, json.dumps(history_msg))

                    self.broadcast({'type': protocol.MSG_TEXT, 'payload': f"Server: {username} has joined the chat."})
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
                            # Assume WS client sends JSON. If just text, wrap it.
                            # Try parsing as JSON first
                            message = json.loads(raw_msg)
                        except json.JSONDecodeError:
                            # If not JSON, treat as simple text message
                            message = {'type': protocol.MSG_TEXT, 'payload': raw_msg}
                    else:
                        message = None # Connection closed

                if message is None:
                    break # Connection closed
                
                if message.get('type') == protocol.MSG_EXIT:
                    break
                
                if message.get('type') == protocol.MSG_TEXT:
                    content = message.get('payload')
                    print(f"[{username}] {content}")
                    
                    # Save to DB (public message)
                    self.db.save_message(username, content, message_type='public')

                    # Broadcast to others
                    self.broadcast({
                        'type': protocol.MSG_TEXT, 
                        'payload': f"{username}: {content}"
                    }, exclude_socket=client_socket)

        except Exception as e:
            print(f"[ERROR] Error handling client {username}: {e}")
        finally:
            # Cleanup
            with self.lock:
                if client_socket in self.clients:
                    del self.clients[client_socket]
                if client_socket in self.client_types:
                    del self.client_types[client_socket]
            
            client_socket.close()
            if username:
                print(f"[DISCONNECT] User '{username}' disconnected.")
                self.broadcast({'type': protocol.MSG_TEXT, 'payload': f"Server: {username} has left the chat."})

    def broadcast(self, message_dict, exclude_socket=None):
        """Sends a message to all connected clients (TCP and WS)"""
        with self.lock:
            for client_sock in list(self.clients.keys()):
                if client_sock != exclude_socket:
                    c_type = self.client_types.get(client_sock, 'tcp')
                    try:
                        if c_type == 'tcp':
                            protocol.send_json(client_sock, message_dict)
                        else:
                            # Send as JSON string in a WS frame
                            websocket_handler.send_frame(client_sock, json.dumps(message_dict))
                    except:
                        # If sending fails, assume client disconnected
                        client_sock.close()
                        if client_sock in self.clients:
                            del self.clients[client_sock]
                        if client_sock in self.client_types:
                            del self.client_types[client_sock]

if __name__ == "__main__":
    server = ChatServer()
    server.start()
