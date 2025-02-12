# client/client_main.py

import threading
import time
from .chat_client import ChatClient

PORT = 12345
host_ip = input("Enter host IP address: ")
client = ChatClient(host_ip, PORT)

def main():
    threading.Thread(target=client.handle_user, daemon=True).start()
    threading.Thread(target=client.handle_message, daemon=True).start()

    # Keep the main thread alive
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
