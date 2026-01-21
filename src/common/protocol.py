import json
import struct

# Constants
PORT = 5555
HEADER_LENGTH = 10
encoding = 'utf-8'

# Message Types
MSG_LOGIN = "LOGIN"
MSG_REGISTER = "REGISTER"
MSG_TEXT = "TEXT"
MSG_EXIT = "EXIT"
MSG_PRIVATE = "PRIVATE"
MSG_GROUP = "GROUP"
MSG_GROUP_CREATE = "GROUP_CREATE"
MSG_GROUP_JOIN = "GROUP_JOIN"
MSG_GROUP_LEAVE = "GROUP_LEAVE"
MSG_USERS_LIST = "USERS_LIST"
MSG_GROUPS_LIST = "GROUPS_LIST"
MSG_FILE_REQUEST = "FILE_REQUEST"
MSG_FILE_CHUNK = "FILE_CHUNK"
MSG_FILE_END = "FILE_END"
MSG_FILE = "FILE"
MSG_TYPING = "TYPING"
MSG_STOP_TYPING = "STOP_TYPING"
MSG_UPDATE_NAME = "UPDATE_NAME"
MSG_UPDATE_NAME_SUCCESS = "UPDATE_NAME_SUCCESS"
MSG_FRIEND_REQUEST = "FRIEND_REQUEST"
MSG_FRIEND_ACCEPT = "FRIEND_ACCEPT"
MSG_FRIEND_REJECT = "FRIEND_REJECT"
MSG_FRIEND_LIST = "FRIEND_LIST"
MSG_USER_STATUS = "USER_STATUS"
MSG_GROUP_MEMBERS = "GROUP_MEMBERS"
MSG_GROUP_MEMBERS_RESPONSE = "GROUP_MEMBERS_RESPONSE"


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
