import socket
import json
import threading
import hashlib

from Server.protocol_json import create_msg
from Server.data_store import users, active_users
from Server.handlers import (
    handle_login, handle_create, handle_list, handle_send,
    handle_read, handle_delete_msg, handle_delete, handle_logoff, handle_view_conv
)

class ChatServer:
    MSGLEN = 409600

    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.running = True

        # Store conversations (keyed by tuple of sorted usernames)
        self.conversations = {}

    def start(self):
        self.server.listen()
        print(f"Server is listening on {self.host}:{self.port}")

        while self.running:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
            thread.start()

    def stop(self):
        self.running = False
        self.server.close()

    def read_messages(self, conn):
        buffer = ""
        while True:
            try:
                data = conn.recv(ChatServer.MSGLEN).decode()
            except Exception as e:
                print("Error reading from connection:", e)
                break

            if not data:
                break

            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                yield line
        return 0

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def handle_client(self, conn, addr):
        print(f"{addr} has connected to the server!")

        try:
            for raw_msg in self.read_messages(conn):
                if not raw_msg:
                    continue

                try:
                    parts = json.loads(raw_msg)
                except json.JSONDecodeError:
                    conn.send(create_msg("error", body="Invalid JSON", err=True))
                    continue

                cmd = parts.get("cmd", "")
                username = parts.get("from", "")

                # Route commands to handlers
                if cmd == "login":
                    handle_login(self, conn, parts)
                elif cmd == "create":
                    handle_create(self, conn, parts)
                elif cmd == "list":
                    handle_list(self, conn, parts)
                elif cmd == "send":
                    handle_send(self, conn, parts)
                elif cmd == "read":
                    handle_read(self, conn, parts)
                elif cmd == "delete_msg":
                    handle_delete_msg(self, conn, parts)
                elif cmd == "delete":
                    handle_delete(self, conn, parts)
                elif cmd == "logoff":
                    handle_logoff(self, conn, parts)
                elif cmd == "view_conv":
                    handle_view_conv(self, conn, parts)
                elif cmd == "close":
                    print(f"{addr} has been successfully disconnected!")
                    break
                else:
                    conn.send(create_msg("error", body="Unknown command", err=True))

        except Exception as e:
            print(f"Exception handling client {addr}: {e}")

        finally:
            conn.close()
            print(f"{addr} has been disconnected and the connection was closed.")
