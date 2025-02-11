import socket
import json
import fnmatch
import threading
import hashlib
from collections import OrderedDict

class ChatServer:
    MSGLEN = 409600

    def create_msg(self, cmd, src = "", to = "", body = "", err = False):
        
        msg = {
            "cmd": cmd,
            "from": src,
            "to": to,
            "body": body,
            "error": err
        }
        return (json.dumps(msg) + "\n").encode()

    def __init__(self, host = 'localhost', port = 12345):
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = port

        # maps users to their hashed password and undelivered messages, which is a tuple [sender: messsage]
        self.users = OrderedDict()
        self.active_users = {}
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.running = True

    def start(self):
        self.server.listen()
        print(f"Server is listening on {self.host}:{self.port}")

        while self.running:
            conn, addr = self.server.accept()
            thread = threading.Thread(target = self.handle_client, args = (conn, addr))
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

    # hash the password for safety purposes
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
                    conn.send(self.create_msg("error", body = "Invalid JSON", err = True))
                    continue

                cmd = parts.get("cmd")
                username = parts.get("from")

                if cmd == "login":
                    
                    password = parts.get("password", "")
                    
                    if username not in self.users:
                        conn.send(self.create_msg(cmd, body = "Invalid or incorrect username", err = True))

                    else:
                        stored_hash = self.users[username]["password_hash"]
                        if stored_hash != self.hash_password(password):
                            conn.send(self.create_msg(cmd, body = "Invalid or incorrect password", err = True))

                        elif username in self.active_users:
                            conn.send(self.create_msg(cmd, body= "You are already logged in!", err = True))
                        else:
                            self.active_users[username] = conn
                            unread_count = len(self.users[username]["messages"])
                            conn.send(self.create_msg(cmd, body = f"Login successful! You have {unread_count} messages", to = username))

                elif cmd == "create":

                    password = parts.get("password", "")

                    if username in self.users:
                        conn.send(self.create_msg(cmd, body = "This username already exists", err = True))
                    else:
                        self.users[username] = {"password_hash": self.hash_password(password), "messages": []}
                        conn.send(self.create_msg(cmd, body = "Account has been created!", to = username))

                elif cmd == "list":
                    # List accounts matching a specified wildcard or use * to view all accounts.
                    wildcard = parts.get("body", "*")
                    matching_users = fnmatch.filter(list(self.users.keys()), wildcard)
                    matching_str = ",".join(matching_users)
                    conn.send(self.create_msg(cmd, body = matching_str))

                elif cmd == "send":
                    recipient = parts.get("to")
                    message = parts.get("body")

                    if recipient not in self.users:
                        conn.send(self.create_msg(cmd, body = "User not found", err = True))

                    else:
                        if recipient in self.active_users:
                            try:
                                self.active_users[recipient].send(self.create_msg("read", src = username, body = message))
                            except Exception as e:
                                print(f"There was an error sending your message to {recipient}: {e}")
                                self.users[recipient]["messages"].append((username, message))

                        else:
                            self.users[recipient]["messages"].append((username, message))
                        conn.send(self.create_msg(cmd, body = "Your message has been sent"))

                elif cmd == "read":
                    # Read undelivered messages

                    if username not in self.users:
                        conn.send(self.create_msg(cmd, body = "User not found", err = True))
                    else:
                        # limit the number of messages to be viewed. Initially, there is no limit.
                        limit = None
                        body_field = parts.get("body", "")
                        if body_field:
                            try:
                                limit = int(body_field)
                            except ValueError:
                                limit = None  

                        user_messages = self.users[username]["messages"]
                        if limit is not None:
                            messages_to_read = user_messages[:limit]
                            remaining_messages = user_messages[limit:]
                        else:
                            messages_to_read = user_messages
                            remaining_messages = []

                        for (sender, msg_text) in messages_to_read:
                            conn.send(self.create_msg("read", src = sender, body = msg_text))
                        self.users[username]["messages"] = remaining_messages

                elif cmd == "delete_msg":
                    # I don't know if this part works yet tbh 
                    if username not in self.users:
                        conn.send(self.create_msg(cmd, body = "User not found", err = True))

                    else:
                        raw_indices = parts.get("body", "")
                        indices = []
                        if isinstance(raw_indices, list):
                            indices = raw_indices

                        else:
                            try:
                                indices = [int(x.strip()) for x in raw_indices.split(",") if x.strip().isdigit()]
                            except Exception as e:
                                conn.send(self.create_msg(cmd, body = "Invalid indices", err = True))
                                continue
                        current_msgs = self.users[username]["messages"]

                        # create a new list that doesn't have the deleted messages
                        new_msgs = [msg for idx, msg in enumerate(current_msgs) if idx not in indices]
                        self.users[username]["messages"] = new_msgs
                        conn.send(self.create_msg(cmd, body="Specified messages deleted"))

                elif cmd == "delete":
                    # del an account IFF the user exists AND there are no undelivered messages
                    if username not in self.users:
                        conn.send(self.create_msg(cmd, body = "The user does not exist", err = True))
                    elif len(self.users[username]["messages"]) > 0:
                        conn.send(self.create_msg(cmd, body = "Undelivered messages stil exist", err = True))

                    else:
                        del self.users[username]
                        if username in self.active_users:
                            del self.active_users[username]
                       # conn.send(self.create_msg(cmd, body = "Account has been successfully deleted!"))

                elif cmd == "logoff":
                    if username in self.active_users:
                        del self.active_users[username]

                   # conn.send(self.create_msg(cmd, body = "User has logged off"))

                elif cmd == "close":
                    print(f"{addr} has been successfully disconnected!")
                    break

                else:
                    conn.send(self.create_msg("error", body="Unknown command", err=True))

        except Exception as e:
            print(f"Exception handling client {addr}: {e}")

        finally:
            conn.close()
            print(f"{addr} has been disconnected and the connection was closed.")

if __name__ == "__main__":
    server = ChatServer(host = 'localhost', port = 12345)
    try:
        server.start()
    except KeyboardInterrupt:
        print("The server is shutting down. Bye!")
        server.stop()
