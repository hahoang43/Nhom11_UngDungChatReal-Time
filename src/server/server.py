
# Flask-SocketIO server with Database integration
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import sys
import json
import base64

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.server.db import Database
from src.common import protocol

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
db = Database()

# Dictionary to map sid -> username
clients = {}
# Track file transfers: sid -> {filename, filesize, receiver, file_obj}
file_transfers = {}
# Files directory
FILES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/received_files'))
os.makedirs(FILES_DIR, exist_ok=True)

@app.route("/")
def index():
    return "Nhom11 Chat Server is running!"

@app.route("/download")
def download_file():
    filename = request.args.get('filename')
    if not filename:
        return "Missing filename", 400
    safe_name = os.path.basename(filename)
    file_path = os.path.join(FILES_DIR, safe_name)
    if not os.path.isfile(file_path):
        return "File not found", 404
    from flask import send_from_directory
    return send_from_directory(FILES_DIR, safe_name, as_attachment=True)

@socketio.on('connect')
def handle_connect():
    print(f"[SERVER] Client connected: {request.sid}", flush=True)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in clients:
        username = clients[sid]
        print(f"User {username} disconnected")
        del clients[sid]
        if sid in file_transfers:
            try:
                file_transfers[sid]['file'].close()
            except:
                pass
            del file_transfers[sid]
        emit('message', {
            'type': protocol.MSG_TEXT,
            'payload': f"Server: {username} has left the chat."
        }, broadcast=True)
        broadcast_users_list()

@socketio.on('message')
def handle_message(data):
    sid = request.sid
    print(f"[SERVER] Nhận message từ client: {data}", flush=True)
    msg_type = data.get('type')
    payload = data.get('payload')

    # Xử lý yêu cầu lấy danh sách nhóm từ client
    if msg_type == 'GROUPS_REQUEST':
        groups = db.get_all_groups()
        # Convert datetime fields to string
        for g in groups:
            for k, v in g.items():
                if hasattr(v, 'isoformat'):
                    g[k] = v.isoformat()
        emit('message', {'type': protocol.MSG_GROUPS_LIST, 'payload': groups}, room=sid)
        return

    if msg_type == protocol.MSG_REGISTER:
        username = payload.get('username')
        password = payload.get('password', 'default')
        if db.user_exists(username):
            emit('message', {'type': 'ERROR', 'payload': 'Tên đăng nhập đã tồn tại'})
        elif db.register_user(username, password):
            emit('message', {'type': 'LOGIN_SUCCESS', 'payload': f'Đăng ký thành công! Chào mừng {username}!'})
        else:
            emit('message', {'type': 'ERROR', 'payload': 'Đăng ký thất bại. Vui lòng thử lại.'})
        return

    # Lấy username cho các nhánh cần xác thực (sau LOGIN/REGISTER)
    if msg_type not in [protocol.MSG_LOGIN, protocol.MSG_REGISTER]:
        username = clients.get(sid)
        if not username:
            emit('message', {'type': 'ERROR', 'payload': 'Chưa đăng nhập hoặc phiên đăng nhập hết hạn'})
            return

    if msg_type == protocol.MSG_LOGIN:
        username = payload.get('username')
        password = payload.get('password', 'default')
        if db.login_user(username, password):
            clients[sid] = username
            emit('message', {'type': 'LOGIN_SUCCESS', 'payload': f'Welcome {username}!'})
            
            # Send history
            send_history(sid, username)

            # Restore group memberships
            user_groups = db.get_user_groups(username)
            group_ids = []
            for g in user_groups:
                gid = g['id']
                join_room(f"group_{gid}")
                group_ids.append(gid)
            emit('message', {'type': 'USER_GROUPS', 'payload': group_ids})
            
            # Broadcast join message
            emit('message', {
                'type': protocol.MSG_TEXT,
                'payload': f"Server: {username} has joined the chat."
            }, broadcast=True, include_self=False)
            
            broadcast_users_list()
            broadcast_groups_list()
        else:
            emit('message', {'type': 'ERROR', 'payload': 'Invalid username or password'})

    if msg_type == protocol.MSG_LOGIN:
        username = payload.get('username')
        password = payload.get('password', 'default')
        if db.login_user(username, password):
            clients[sid] = username
            emit('message', {'type': 'LOGIN_SUCCESS', 'payload': f'Welcome {username}!'} )
            # Do NOT send public history or join any group
            emit('message', {'type': 'USER_GROUPS', 'payload': []})
            broadcast_users_list()
            broadcast_groups_list()
        else:
            emit('message', {'type': 'ERROR', 'payload': 'Invalid username or password'})

    # Đã loại bỏ hoàn toàn luồng chat công khai MSG_TEXT

    elif msg_type == protocol.MSG_PRIVATE:
        receiver = payload.get('receiver')
        content = payload.get('content')
        db.save_message(username, content, receiver=receiver, message_type='private')
        
        target_sid = get_sid_by_username(receiver)
        if target_sid:
            emit('message', {
                'type': protocol.MSG_PRIVATE,
                'payload': {'sender': username, 'content': content}
            }, room=target_sid)
        else:
            emit('message', {'type': 'ERROR', 'payload': f"User {receiver} is offline."})

    elif msg_type == protocol.MSG_GROUP:
        group_id = payload.get('group_id')
        content = payload.get('content')
        db.save_message(username, content, receiver=group_id, message_type='group')
        
        emit('message', {
            'type': protocol.MSG_GROUP,
            'payload': {'sender': username, 'group_id': group_id, 'content': content}
        }, room=f"group_{group_id}", include_self=False)

    elif msg_type == 'HISTORY_REQUEST':
        history_type = payload.get('history_type')
        target = payload.get('target')
        if history_type == 'private' and target:
            history = db.get_history(50, message_type='private', username=target)
            print(f"DEBUG: Sending private history ({len(history)} items). First: {history[0]['timestamp'] if history else 'None'}, Last: {history[-1]['timestamp'] if history else 'None'}")
            for row in history: # Send in chronological order
                emit('message', {
                    'type': protocol.MSG_PRIVATE,
                    'payload': {
                        'sender': row['sender'],
                        'receiver': row['receiver'],
                        'content': row['content'],
                        'timestamp': row['timestamp']
                    }
                })
        elif history_type == 'group' and target:
            history = db.get_history(50, message_type='group', group_id=target)
            for row in history:
                emit('message', {
                    'type': protocol.MSG_GROUP,
                    'payload': {
                        'sender': row['sender'],
                        'group_id': target,
                        'content': row['content'],
                        'timestamp': row['timestamp']
                    }
                })

    elif msg_type == protocol.MSG_GROUP_CREATE:
        group_name = payload
        group_id = db.create_group(group_name, username)
        if group_id:
            db.add_member_to_group(group_id, username)
            join_room(f"group_{group_id}")
            emit('message', {'type': 'SUCCESS', 'payload': f"Group '{group_name}' created"})
            broadcast_groups_list()
        else:
            emit('message', {'type': 'ERROR', 'payload': "Failed to create group"})

    elif msg_type == protocol.MSG_GROUP_JOIN:
        group_id = payload
        if db.add_member_to_group(group_id, username):
            join_room(f"group_{group_id}")
            emit('message', {'type': 'SUCCESS', 'payload': f"Joined group {group_id}"})
        else:
            emit('message', {'type': 'ERROR', 'payload': "Failed to join group"})

    elif msg_type == protocol.MSG_GROUP_LEAVE:
        group_id = payload
        if db.remove_member_from_group(group_id, username):
            leave_room(f"group_{group_id}")
            emit('message', {'type': 'SUCCESS', 'payload': f"Left group {group_id}"})
        else:
            emit('message', {'type': 'ERROR', 'payload': "Failed to leave group"})

    elif msg_type == 'GROUP_DELETE':
        group_id = payload.get('group_id')
        print(f"[SERVER] Nhận yêu cầu xóa nhóm: group_id={group_id}, username={username}", flush=True)
        # Only allow creator to delete
        if db.delete_group(group_id, username):
            print(f"[SERVER] Đã xóa nhóm thành công: group_id={group_id}", flush=True)
            emit('message', {'type': 'SUCCESS', 'payload': f'Group {group_id} deleted'})
            broadcast_groups_list()
        else:
            print(f"[SERVER] Không xóa được nhóm: group_id={group_id}, username={username}", flush=True)
            emit('message', {'type': 'ERROR', 'payload': 'You are not allowed to delete this group or deletion failed.'})

    elif msg_type == protocol.MSG_FILE_REQUEST:
        filename = payload.get('filename')
        filesize = payload.get('filesize')
        receiver = payload.get('receiver')
        print(f"[FILE] {username} sending file: {filename} ({filesize} bytes)")
        filepath = os.path.join(FILES_DIR, filename)
        try:
            f = open(filepath, 'wb')
            file_transfers[sid] = {
                'sender': username,
                'filename': filename,
                'filesize': filesize,
                'receiver': receiver,
                'file': f
            }
        except Exception as e:
            print(f"[ERROR] Cannot open file for writing: {e}")

    elif msg_type == protocol.MSG_FILE_CHUNK:
        chunk_b64 = payload.get('data', '')
        if sid in file_transfers:
            try:
                data_chunk = base64.b64decode(chunk_b64)
                file_transfers[sid]['file'].write(data_chunk)
            except Exception as e:
                print(f"[ERROR] Write chunk failed: {e}")

    elif msg_type == protocol.MSG_FILE_END:
        if sid in file_transfers:
            info = file_transfers[sid]
            info['file'].close()
            filename = info['filename']
            filesize = info['filesize']
            
            file_msg = f"📎 File: {filename} ({format_file_size(filesize)})"
            db.save_message(username, file_msg, message_type='public')
            
            broadcast_msg = {
                'type': protocol.MSG_FILE,
                'payload': {
                    'sender': username,
                    'filename': filename,
                    'filesize': filesize,
                    'message': f"{username} đã gửi file: {filename}"
                }
            }
            emit('message', broadcast_msg, broadcast=True)
            del file_transfers[sid]

    elif msg_type == protocol.MSG_TYPING:
        target_mode = payload.get('mode') # 'private' or 'group'
        target_id = payload.get('target') # username or group_id
        
        if target_mode == 'private':
            target_sid = get_sid_by_username(target_id)
            if target_sid:
                emit('message', {
                    'type': protocol.MSG_TYPING,
                    'payload': {'sender': username, 'mode': 'private'}
                }, room=target_sid)
        elif target_mode == 'group':
             emit('message', {
                    'type': protocol.MSG_TYPING,
                    'payload': {'sender': username, 'mode': 'group', 'group_id': target_id}
                }, room=f"group_{target_id}", include_self=False)
        elif target_mode == 'public':
            emit('message', {
                'type': protocol.MSG_TYPING,
                'payload': {'sender': username, 'mode': 'public'}
            }, broadcast=True, include_self=False)

    elif msg_type == protocol.MSG_STOP_TYPING:
        target_mode = payload.get('mode')
        target_id = payload.get('target')
        
        if target_mode == 'private':
            target_sid = get_sid_by_username(target_id)
            if target_sid:
                emit('message', {
                    'type': protocol.MSG_STOP_TYPING,
                    'payload': {'sender': username, 'mode': 'private'}
                }, room=target_sid)
        elif target_mode == 'group':
             emit('message', {
                    'type': protocol.MSG_STOP_TYPING,
                    'payload': {'sender': username, 'mode': 'group', 'group_id': target_id}
                }, room=f"group_{target_id}", include_self=False)
        elif target_mode == 'public':
            emit('message', {
                'type': protocol.MSG_STOP_TYPING,
                'payload': {'sender': username, 'mode': 'public'}
            }, broadcast=True, include_self=False)

def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def send_history(sid, username):
    # Public history
    public_history = db.get_history(20, message_type='public')
    for row in reversed(list(public_history)):
        emit('message', {
            'type': protocol.MSG_TEXT,
            'payload': f"[{row['timestamp']}] {row['sender']}: {row['content']}"
        }, room=sid)

    # Private history
    private_history = db.get_history(20, message_type='private', username=username)
    for row in reversed(list(private_history)):
        emit('message', {
            'type': protocol.MSG_PRIVATE,
            'payload': {
                'sender': row['sender'],
                'receiver': row['receiver'],
                'content': row['content'],
                'timestamp': row['timestamp']
            }
        }, room=sid)

def broadcast_users_list():
    online_users = list(set(clients.values()))
    emit('message', {
        'type': protocol.MSG_USERS_LIST,
        'payload': online_users
    }, broadcast=True)

def broadcast_groups_list():
    groups = db.get_all_groups()
    # Convert datetime fields to string
    for g in groups:
        for k, v in g.items():
            if hasattr(v, 'isoformat'):
                g[k] = v.isoformat()
    emit('message', {
        'type': protocol.MSG_GROUPS_LIST,
        'payload': groups
    }, broadcast=True)

def get_sid_by_username(username):
    for sid, name in clients.items():
        if name == username:
            return sid
    return None

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    socketio.run(app, host="0.0.0.0", port=port)

