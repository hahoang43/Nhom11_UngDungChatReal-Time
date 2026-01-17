import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.server.server import app, socketio
import os

def main():
    print("Starting Nhom11 Chat Server (Socket.IO)...")
    port = int(os.environ.get('PORT', 8000))
    try:
        socketio.run(app, host="0.0.0.0", port=port)
    except KeyboardInterrupt:
        print("\nServer shutting down...")

if __name__ == "__main__":
    main()
