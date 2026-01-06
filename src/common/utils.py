"""
Utility functions for encryption and file handling
Mã hóa AES và xử lý file
"""

import os
import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

# AES key derivation từ password
def derive_key(password: str, salt: bytes = None) -> tuple:
    """
    Tạo AES key từ password sử dụng PBKDF2
    
    Args:
        password: Mật khẩu để tạo key
        salt: Salt (nếu None sẽ tạo mới)
        
    Returns:
        (key, salt): Tuple chứa key và salt
    """
    if salt is None:
        salt = get_random_bytes(16)
    
    # Sử dụng SHA-256 để tạo key 32 bytes (AES-256)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000, dklen=32)
    return key, salt

class AESEncryption:
    """Class để mã hóa và giải mã dữ liệu bằng AES"""
    
    def __init__(self, key: bytes = None, password: str = None):
        """
        Khởi tạo với key hoặc password
        
        Args:
            key: AES key (32 bytes cho AES-256)
            password: Password để tạo key (nếu không có key)
        """
        if key:
            self.key = key
            self.salt = None
        elif password:
            self.key, self.salt = derive_key(password)
        else:
            # Default key (nên thay đổi trong production)
            default_password = "ChatAppDefaultKey2024"
            self.key, self.salt = derive_key(default_password)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Mã hóa plaintext thành ciphertext (base64 encoded)
        
        Args:
            plaintext: Văn bản cần mã hóa
            
        Returns:
            Ciphertext dạng base64 string
        """
        try:
            # Tạo IV (Initialization Vector) ngẫu nhiên
            iv = get_random_bytes(16)
            
            # Tạo cipher
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            
            # Mã hóa với padding
            padded_data = pad(plaintext.encode('utf-8'), AES.block_size)
            ciphertext = cipher.encrypt(padded_data)
            
            # Kết hợp IV + ciphertext và encode base64
            encrypted_data = iv + ciphertext
            encrypted_b64 = base64.b64encode(encrypted_data).decode('utf-8')
            
            return encrypted_b64
        except Exception as e:
            raise Exception(f"Encryption error: {e}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Giải mã ciphertext thành plaintext
        
        Args:
            ciphertext: Ciphertext dạng base64 string
            
        Returns:
            Plaintext string
        """
        try:
            # Decode base64
            encrypted_data = base64.b64decode(ciphertext.encode('utf-8'))
            
            # Tách IV và ciphertext
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            
            # Tạo cipher
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            
            # Giải mã và unpad
            decrypted_padded = cipher.decrypt(ciphertext)
            plaintext = unpad(decrypted_padded, AES.block_size).decode('utf-8')
            
            return plaintext
        except Exception as e:
            raise Exception(f"Decryption error: {e}")

def encrypt_message(message: str, key: bytes = None, password: str = None) -> str:
    """
    Helper function để mã hóa tin nhắn
    
    Args:
        message: Tin nhắn cần mã hóa
        key: AES key (optional)
        password: Password để tạo key (optional)
        
    Returns:
        Ciphertext dạng base64
    """
    enc = AESEncryption(key=key, password=password)
    return enc.encrypt(message)

def decrypt_message(ciphertext: str, key: bytes = None, password: str = None) -> str:
    """
    Helper function để giải mã tin nhắn
    
    Args:
        ciphertext: Ciphertext cần giải mã
        key: AES key (optional)
        password: Password để tạo key (optional)
        
    Returns:
        Plaintext message
    """
    enc = AESEncryption(key=key, password=password)
    return enc.decrypt(ciphertext)

def get_file_info(filepath: str) -> dict:
    """
    Lấy thông tin file
    
    Args:
        filepath: Đường dẫn file
        
    Returns:
        Dictionary chứa thông tin file
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    
    return {
        'filename': filename,
        'filesize': filesize,
        'filepath': filepath
    }

def read_file_chunks(filepath: str, chunk_size: int = 8192):
    """
    Đọc file theo chunks (để xử lý file lớn)
    
    Args:
        filepath: Đường dẫn file
        chunk_size: Kích thước mỗi chunk (bytes)
        
    Yields:
        Chunks của file
    """
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

def save_file_chunks(filepath: str, chunks):
    """
    Lưu file từ chunks
    
    Args:
        filepath: Đường dẫn file đích
        chunks: Iterator chứa các chunks
    """
    with open(filepath, 'wb') as f:
        for chunk in chunks:
            f.write(chunk)

