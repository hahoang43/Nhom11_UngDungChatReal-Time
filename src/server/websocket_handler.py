import base64
import hashlib
import struct

MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def handshake(client_socket, data):
    """
    Performs the WebSocket handshake.
    :param client_socket: The socket connection
    :param data: The initial data received (HTTP GET request)
    :return: True if handshake successful, False otherwise
    """
    try:
        request = data.decode('utf-8')
        headers = {}
        lines = request.split("\r\n")
        for line in lines:
            if ": " in line:
                key, value = line.split(": ", 1)
                headers[key] = value
        
        if "Sec-WebSocket-Key" not in headers:
            return False
        
        key = headers["Sec-WebSocket-Key"]
        accept_key = base64.b64encode(hashlib.sha1((key + MAGIC_STRING).encode('utf-8')).digest()).decode('utf-8')
        
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
        )
        
        client_socket.send(response.encode('utf-8'))
        return True
    except Exception as e:
        print(f"[WS ERROR] Handshake failed: {e}")
        return False

def receive_frame(client_socket):
    """
    Receives and decodes a WebSocket frame.
    :return: The decoded payload (string) or None if connection closed/error
    """
    try:
        # Read first 2 bytes
        head = client_socket.recv(2)
        if not head: return None
        
        b1, b2 = struct.unpack("!BB", head)
        
        fin = b1 & 0x80
        opcode = b1 & 0x0F
        masked = b2 & 0x80
        payload_length = b2 & 0x7F
        
        if opcode == 8: # Close frame
            return None
            
        if payload_length == 126:
            payload_length = struct.unpack("!H", client_socket.recv(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack("!Q", client_socket.recv(8))[0]
            
        masks = None
        if masked:
            masks = client_socket.recv(4)
            
        payload = b""
        remaining = payload_length
        while remaining > 0:
            chunk = client_socket.recv(min(4096, remaining))
            if not chunk: break
            payload += chunk
            remaining -= len(chunk)
            
        if masked:
            decoded = bytearray()
            for i in range(len(payload)):
                decoded.append(payload[i] ^ masks[i % 4])
            payload = decoded
            
        return payload.decode('utf-8')
        
    except Exception as e:
        # print(f"[WS ERROR] Receive frame failed: {e}")
        return None

def send_frame(client_socket, message):
    """
    Encodes and sends a WebSocket frame (Text).
    """
    try:
        payload = message.encode('utf-8')
        payload_length = len(payload)
        
        header = bytearray()
        # FIN=1, Opcode=1 (Text)
        header.append(0x81)
        
        if payload_length <= 125:
            header.append(payload_length)
        elif payload_length <= 65535:
            header.append(126)
            header.extend(struct.pack("!H", payload_length))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", payload_length))
            
        client_socket.send(header + payload)
    except Exception as e:
        print(f"[WS ERROR] Send frame failed: {e}")
