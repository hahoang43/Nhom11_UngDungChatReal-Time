import socket
import threading
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.common import protocol
from src.common.utils import AESEncryption, encrypt_message, decrypt_message

class ChatClient:
    def __init__(self, host='127.0.0.1', port=protocol.PORT, use_encryption=True, encryption_key=None):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.running = False
        self.on_message_received = None # Callback function
        self.on_login_response = None # Callback for login/register response
        self.on_file_received = None # Callback for file received
        self.waiting_for_login = False
        self.use_encryption = use_encryption
        # Tạo encryption key từ username (sẽ được set sau khi login)
        self.encryption_key = encryption_key
        self.encryption = None

    def connect(self, username, password='default'):
        """Connects to the server and performs login"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.username = username
            self.running = True
            self.waiting_for_login = True
            
            # Setup encryption với password làm key
            if self.use_encryption:
                self.encryption = AESEncryption(password=password)

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

    def send_message(self, message, encrypted=None):
        """
        Sends a text message to the server
        
        Args:
            message: Tin nhắn cần gửi
            encrypted: None để tự động mã hóa nếu use_encryption=True, True/False để override
        """
        if self.socket and self.running:
            # Mã hóa tin nhắn nếu cần
            if encrypted is None:
                encrypted = self.use_encryption
            
            if encrypted and self.encryption:
                try:
                    encrypted_msg = self.encryption.encrypt(message)
                    msg_data = {'type': protocol.MSG_TEXT, 'payload': encrypted_msg, 'encrypted': True}
                except Exception as e:
                    print(f"[CLIENT ERROR] Encryption failed: {e}")
                    msg_data = {'type': protocol.MSG_TEXT, 'payload': message, 'encrypted': False}
            else:
                msg_data = {'type': protocol.MSG_TEXT, 'payload': message, 'encrypted': False}
            
            try:
                protocol.send_json(self.socket, msg_data)
            except Exception as e:
                print(f"[CLIENT ERROR] Send failed: {e}")
                self.disconnect()
    
    def send_file(self, filepath, receiver=None, progress_callback=None):
        """
        Gửi file đến server
        
        Args:
            filepath: Đường dẫn file cần gửi
            receiver: Người nhận (None cho public)
            progress_callback: Callback function(progress, total) để cập nhật progress
        """
        if not self.socket or not self.running:
            return False
        
        try:
            from src.common.utils import get_file_info, read_file_chunks
            import base64
            
            file_info = get_file_info(filepath)
            total_size = file_info['filesize']
            chunk_size = 8192  # 8KB per chunk
            total_chunks = (total_size + chunk_size - 1) // chunk_size  # Ceiling division
            
            # Gửi file request
            file_request = {
                'type': protocol.MSG_FILE_REQUEST,
                'payload': {
                    'filename': file_info['filename'],
                    'filesize': file_info['filesize'],
                    'receiver': receiver
                }
            }
            protocol.send_json(self.socket, file_request)
            
            # Gửi file theo chunks
            chunk_num = 0
            sent_size = 0
            
            for chunk in read_file_chunks(filepath, chunk_size):
                chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                file_chunk = {
                    'type': protocol.MSG_FILE_CHUNK,
                    'payload': {
                        'chunk_num': chunk_num,
                        'data': chunk_b64
                    }
                }
                protocol.send_json(self.socket, file_chunk)
                chunk_num += 1
                sent_size += len(chunk)
                
                # Cập nhật progress
                if progress_callback:
                    progress_callback(sent_size, total_size)
            
            # Gửi file end
            file_end = {
                'type': protocol.MSG_FILE_END,
                'payload': {'filename': file_info['filename']}
            }
            protocol.send_json(self.socket, file_end)
            
            return True
        except Exception as e:
            print(f"[CLIENT ERROR] Send file failed: {e}")
            return False

    def receive_loop(self):
        """Background thread to receive messages"""
        while self.running:
            try:
                message = protocol.receive_json(self.socket)
                if message is None:
                    break
                
                msg_type = message.get('type')
                
                # Handle login/register responses
                if self.waiting_for_login:
                    if msg_type == 'LOGIN_SUCCESS':
                        self.waiting_for_login = False
                        if self.on_login_response:
                            self.on_login_response(True, message.get('payload', 'Đăng nhập thành công!'))
                    elif msg_type == 'ERROR':
                        self.waiting_for_login = False
                        error_msg = message.get('payload', 'Đăng nhập thất bại!')
                        if self.on_login_response:
                            self.on_login_response(False, error_msg)
                        self.disconnect()
                    elif msg_type == protocol.MSG_TEXT:
                        # Server might send history or welcome messages
                        content = message.get('payload')
                        if self.on_message_received:
                            self.on_message_received(content)
                else:
                    # Normal message handling
                    if msg_type == protocol.MSG_TEXT:
                        content = message.get('payload')
                        is_encrypted = message.get('encrypted', False)
                        
                        # Giải mã nếu cần
                        if is_encrypted and self.encryption:
                            try:
                                content = self.encryption.decrypt(content)
                            except Exception as e:
                                print(f"[CLIENT ERROR] Decryption failed: {e}")
                                content = "[Lỗi giải mã tin nhắn]"
                        
                        if self.on_message_received:
                            self.on_message_received(content)
                    elif msg_type == protocol.MSG_FILE:
                        # Xử lý file nhận được
                        if self.on_file_received:
                            self.on_file_received(message.get('payload'))
            except Exception as e:
                print(f"[CLIENT ERROR] Receive error: {e}")
                if self.waiting_for_login and self.on_login_response:
                    self.on_login_response(False, f"Lỗi kết nối: {e}")
                break
        
        if self.waiting_for_login:
            self.waiting_for_login = False
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
