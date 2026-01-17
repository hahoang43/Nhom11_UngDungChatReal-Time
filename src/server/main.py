import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.server.server import ChatServer

def main():
    print("Starting Chat Server...")
    server = ChatServer()
    # Khởi động server HTTP cho file download
    server.start_file_download_server(port=8000)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        server.stop()

if __name__ == "__main__":
    main()
