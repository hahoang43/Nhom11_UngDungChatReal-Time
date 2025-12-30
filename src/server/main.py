import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.server.server import ChatServer

def main():
    print("Starting Chat Server...")
    server = ChatServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.stop()

if __name__ == "__main__":
    main()
