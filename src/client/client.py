import socket
import threading
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.common import protocol

class ChatClient:
    def __init__(self, host='127.0.0.1', port=protocol.PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.running = False
        self.on_message_received = None # Callback function

    def connect(self, username):
        """Connects to the server and performs login"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.username = username
            self.running = True

            # Send Login Message
            login_msg = {'type': protocol.MSG_LOGIN, 'payload': username}
            protocol.send_json(self.socket, login_msg)

            # Start listening thread
            receive_thread = threading.Thread(target=self.receive_loop)
            receive_thread.daemon = True
            receive_thread.start()
            
            return True
        except Exception as e:
            print(f"[CLIENT ERROR] Connection failed: {e}")
            return False

    def send_message(self, message):
        """Sends a text message to the server"""
        if self.socket and self.running:
            msg_data = {'type': protocol.MSG_TEXT, 'payload': message}
            try:
                protocol.send_json(self.socket, msg_data)
            except Exception as e:
                print(f"[CLIENT ERROR] Send failed: {e}")
                self.disconnect()

    def receive_loop(self):
        """Background thread to receive messages"""
        while self.running:
            try:
                message = protocol.receive_json(self.socket)
                if message is None:
                    break
                
                if message.get('type') == protocol.MSG_TEXT:
                    content = message.get('payload')
                    if self.on_message_received:
                        self.on_message_received(content)
            except Exception as e:
                print(f"[CLIENT ERROR] Receive error: {e}")
                break
        
        self.disconnect()

    def disconnect(self):
        """Closes the connection"""
        self.running = False
        if self.socket:
            try:
                # Send exit message
                protocol.send_json(self.socket, {'type': protocol.MSG_EXIT, 'payload': ''})
            except:
                pass
            self.socket.close()
            self.socket = None
        if self.on_message_received:
            self.on_message_received("Disconnected from server.")
