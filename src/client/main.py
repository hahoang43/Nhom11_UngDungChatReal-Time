import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.client.client import ChatClient
from src.client.gui import ChatGUI

def main():
    client = ChatClient()
    app = ChatGUI(client)
    app.start()

if __name__ == "__main__":
    main()
