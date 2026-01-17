import socket
import base64
import os
import struct
import json
import time

PORT = 5555
HOST = 'localhost'

def create_ws_key():
    return base64.b64encode(os.urandom(16)).decode('utf-8')

def test_ws():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
        print(f"Connected to {HOST}:{PORT}")
        
        # Handshake
        key = create_ws_key()
        request = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {HOST}:{PORT}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.send(request.encode('utf-8'))
        
        response = sock.recv(4096).decode('utf-8', errors='ignore')
        print("Handshake Response Headers:\n", response)
        
        if "101 Switching Protocols" in response:
            print("SUCCESS: Handshake completed.")
        else:
            print("FAILURE: Handshake failed.")
            return

        # Prepare Login Message
        login_msg = {
            "type": "LOGIN",
            "payload": {
                "username": "test_ws_user",
                "password": "123"
            }
        }
        json_str = json.dumps(login_msg)
        
        # Frame the message
        # FIN=1, Opcode=1 (text), Masked=1
        frame = bytearray()
        frame.append(0x81) # FIN + Text
        
        payload_bytes = json_str.encode('utf-8')
        length = len(payload_bytes)
        
        # We must mask client-to-server frames per spec
        frame.append(0x80 | length) # Masked bit + length (assuming < 126 for this short msg)
        
        mask = os.urandom(4)
        frame.extend(mask)
        
        masked_payload = bytearray(length)
        for i in range(length):
            masked_payload[i] = payload_bytes[i] ^ mask[i % 4]
            
        frame.extend(masked_payload)
        
        sock.send(frame)
        print("Sent Login Frame.")
        
        # Read response
        # We'll just read raw bytes and check if we see "LOGIN_SUCCESS" or similar in them
        # since implementing full unmasking/parsing here is tedious.
        # Server response is NOT masked.
        
        time.sleep(1)
        resp_data = sock.recv(4096)
        print(f"Received {len(resp_data)} bytes raw response.")
        
        # Simple heuristic decode
        try:
             # Skip header bytes effectively?
             # Server sends unmasked frames. 
             # Byte 0: FIN+Opcode. Byte 1: Length (if <126).
             if len(resp_data) > 2:
                payload_len = resp_data[1] & 0x7F
                start = 2
                if payload_len == 126:
                    start = 4
                elif payload_len == 127:
                    start = 10
                
                payload = resp_data[start:]
                print("Decoded Response:", payload.decode('utf-8', errors='ignore'))
        except Exception as e:
            print("Error decoding:", e)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    test_ws()
