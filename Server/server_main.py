# server/server_main.py

from .chat_server import ChatServer

def main():
    server = ChatServer(host='localhost', port=12345)
    try:
        server.start()
    except KeyboardInterrupt:
        print("The server is shutting down. Bye!")
        server.stop()

if __name__ == "__main__":
    main()
