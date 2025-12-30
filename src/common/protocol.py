import json
import struct

# Constants
PORT = 5555
HEADER_LENGTH = 10
encoding = 'utf-8'

# Message Types
MSG_LOGIN = "LOGIN"
MSG_TEXT = "TEXT"
MSG_EXIT = "EXIT"

def send_json(socket, data):
    """Helper to send JSON data with a fixed-length header"""
    json_data = json.dumps(data).encode(encoding)
    # Header contains the length of the message, padded to 10 bytes
    header = f"{len(json_data):<{HEADER_LENGTH}}".encode(encoding)
    socket.send(header + json_data)

def receive_json(socket):
    """Helper to receive JSON data"""
    try:
        header = socket.recv(HEADER_LENGTH)
        if not header:
            return None
        message_length = int(header.decode(encoding).strip())
        data = socket.recv(message_length).decode(encoding)
        return json.loads(data)
    except Exception as e:
        return None
