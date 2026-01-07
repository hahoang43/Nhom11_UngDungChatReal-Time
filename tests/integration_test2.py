import sys
import time
import threading

sys.path.append(r'd:\UngDungChatRealtime\Nhom11_UngDungChat-Real-Time')

from src.server.server import ChatServer
from src.client.client import ChatClient

c1_msgs = []

def run_server():
    srv = ChatServer()
    srv.start()

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

time.sleep(0.5)
print('SERVER_STARTED', flush=True)

c1 = ChatClient()
print('C1_CONNECT', c1.connect('alice'), flush=True)
c1.on_message_received = lambda m: (c1_msgs.append(m), print('C1_RECV', m, flush=True))

c2 = ChatClient()
print('C2_CONNECT', c2.connect('bob'), flush=True)

# Send messages
c1.send_message('hello from alice')
print('C1_SENT', flush=True)

c2.send_private('alice', 'private hi')
print('C2_SENT_PRIVATE', flush=True)

# Wait
time.sleep(1)
print('C1_MSGS', c1_msgs, flush=True)

c1.disconnect()
c2.disconnect()
print('DONE', flush=True)
