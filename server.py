import socket
import json
import fnmatch
import threading
import hashlib
import datetime
from collections import OrderedDict

class ChatServer:
    MSGLEN = 409600

    def create_msg(self, cmd, src="", to="", body="", err=False):
       
        msg = {
            "cmd": cmd,
            "from": src,
            "to": to,
            "body": body,
            "error": err
        }
        return (json.dumps(msg) + "\n").encode()

    def __init__(self, host='localhost', port=12345):
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = port
        self.users = OrderedDict()     # Maps username to {"password_hash": ..., "messages": [msg_entry, ...]}
        self.active_users = {}         # Maps username to connection objects
        self.conversations = {}        # Maps (user1, user2) sorted tuple to list of message entries
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0', port))
        self.running = True
        self.next_msg_id = 1           # New: global counter for message IDs


    def start(self):
        self.server.listen()
        print(f"[LISTENING] Server is listening on {self.host}:{self.port}")
        while self.running:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
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
        return

    def hash_password(self, password):
    
        return hashlib.sha256(password.encode()).hexdigest()

    def handle_client(self, conn, addr):
        print(f"[NEW CONNECTION] {addr} connected.")
        try:
            for raw_msg in self.read_messages(conn):
                if not raw_msg:
                    continue
                try:
                    parts = json.loads(raw_msg)
                except json.JSONDecodeError:
                    conn.send(self.create_msg("error", body="Invalid JSON", err=True))
                    continue

                cmd = parts.get("cmd")
                username = parts.get("from")

                if cmd == "login":
                    password = parts.get("password", "")
                    if username not in self.users:
                        conn.send(self.create_msg(cmd, body="Username does not exist", err=True))
                    else:
                        stored_hash = self.users[username]["password_hash"]
                        if stored_hash != self.hash_password(password):
                            conn.send(self.create_msg(cmd, body="Incorrect password", err=True))
                        elif username in self.active_users:
                            conn.send(self.create_msg(cmd, body="Already logged in elsewhere", err=True))
                        else:
                            self.active_users[username] = conn
                            unread_count = len(self.users[username]["messages"])
                            conn.send(self.create_msg(cmd, body=f"Login successful. Unread messages: {unread_count}", to=username))

                elif cmd == "create":
                    password = parts.get("password", "")
                    if username in self.users:
                        conn.send(self.create_msg(cmd, body="Username already exists", err=True))
                    else:
                        self.users[username] = {"password_hash": self.hash_password(password), "messages": []}
                        conn.send(self.create_msg(cmd, body="Account created", to=username))

                elif cmd == "list":
                    wildcard = parts.get("body", "*")
                    matching_users = fnmatch.filter(list(self.users.keys()), wildcard)
                    matching_str = ",".join(matching_users)
                    conn.send(self.create_msg(cmd, body=matching_str))

                elif cmd == "send":
                    recipient = parts.get("to")
                    message = parts.get("body")
                    timestamp = datetime.datetime.now().isoformat()
                    conv_key = tuple(sorted([username, recipient]))
                    if conv_key not in self.conversations:
                        self.conversations[conv_key] = []
                    # Create a message entry with a unique id.
                    msg_id = self.next_msg_id
                    self.next_msg_id += 1
                    message_entry = {
                        "id": msg_id,
                        "sender": username,
                        "message": message,
                        "timestamp": timestamp
                    }
                    self.conversations[conv_key].append(message_entry)

                    if recipient not in self.users:
                        conn.send(self.create_msg(cmd, body="Recipient not found", err=True))
                    else:
                        if recipient in self.active_users:
                            try:
                                # Push the message immediately using a different command ("chat")
                                payload = json.dumps([message_entry])
                                self.active_users[recipient].send(self.create_msg("chat", src=username, body=payload))
                            except Exception as e:
                                print(f"Error sending to active user {recipient}: {e}")
                                self.users[recipient]["messages"].append(message_entry)
                        else:
                            self.users[recipient]["messages"].append(message_entry)
                        conn.send(self.create_msg(cmd, body="Message sent"))



                elif cmd == "read":
                    if username not in self.users:
                        conn.send(self.create_msg(cmd, body="User not found", err=True))
                    else:
                        limit = None
                        body_field = parts.get("body", "")
                        if body_field:
                            try:
                                limit = int(body_field)
                            except ValueError:
                                limit = None
                        user_messages = self.users[username]["messages"]
                        if limit is not None and limit > 0:
                            messages_to_view = user_messages[:limit]
                            self.users[username]["messages"] = user_messages[limit:]
                        else:
                            messages_to_view = user_messages
                            self.users[username]["messages"] = []
                        # Build a list of messages (with their unique IDs) to return.
                        msgs_with_index = []
                        for msg_entry in messages_to_view:
                            msgs_with_index.append({
                                "id": msg_entry["id"],
                                "sender": msg_entry["sender"],
                                "message": msg_entry["message"]
                            })
                        composite_body = json.dumps(msgs_with_index, indent=2)
                        conn.send(self.create_msg(cmd, body=composite_body))

                elif cmd == "delete_msg":
                    if username not in self.users:
                        conn.send(self.create_msg(cmd, body="User not found", err=True))
                    else:
                        raw_ids = parts.get("body", "")
                        try:
                            ids_to_delete = [int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()]
                        except Exception as e:
                            conn.send(self.create_msg(cmd, body="Invalid message IDs", err=True))
                            continue
                        # Remove from unread messages.
                        current_unread = self.users[username]["messages"]
                        self.users[username]["messages"] = [msg for msg in current_unread if msg["id"] not in ids_to_delete]
                        # Remove from conversation histories.
                        for conv_key in self.conversations:
                            if username in conv_key:
                                conv = self.conversations[conv_key]
                                self.conversations[conv_key] = [msg for msg in conv if msg["id"] not in ids_to_delete]
                        conn.send(self.create_msg(cmd, body="Specified messages deleted"))

                elif cmd == "view_conv":
                    other_user = parts.get("to", "")
                    if other_user not in self.users:
                        conn.send(self.create_msg(cmd, body="User not found", err=True))
                    else:
                        conv_key = tuple(sorted([username, other_user]))
                        conversation = self.conversations.get(conv_key, [])
                        # Mark unread messages from 'other_user' as read for this user:
                        if username in self.users:
                            current_unread = self.users[username]["messages"]
                            self.users[username]["messages"] = [msg for msg in current_unread if msg["sender"] != other_user]
                        if not conversation:
                            conn.send(self.create_msg(cmd, body="No conversation history found"))
                        else:
                            # Build conversation history with the message IDs.
                            conv_with_index = []
                            for msg_entry in conversation:
                                conv_with_index.append({
                                    "id": msg_entry["id"],
                                    "sender": msg_entry["sender"],
                                    "message": msg_entry["message"],
                                    "timestamp": msg_entry["timestamp"]
                                })
                            conv_str = json.dumps(conv_with_index, indent=2)
                            conn.send(self.create_msg(cmd, to=other_user, body=conv_str))

                elif cmd == "delete":
                    if username not in self.users:
                        conn.send(self.create_msg(cmd, body="User does not exist", err=True))
                    else:
                        # Delete the user's account from the user database.
                        del self.users[username]
                        if username in self.active_users:
                            del self.active_users[username]
                        # Remove any conversation histories involving this username.
                        for conv_key in list(self.conversations.keys()):
                            if username in conv_key:
                                del self.conversations[conv_key]
                        conn.send(self.create_msg(cmd, body="Account deleted"))

                elif cmd == "logoff":
                    if username in self.active_users:
                        del self.active_users[username]
                    conn.send(self.create_msg(cmd, body="User logged off"))

                elif cmd == "close":
                    print(f"[DISCONNECT] {addr} disconnected.")
                    break
                else:
                    conn.send(self.create_msg("error", body="Unknown command", err=True))
        except Exception as e:
            print(f"[ERROR] Exception handling client {addr}: {e}")
        finally:
            conn.close()
            print(f"[DISCONNECT] {addr} connection closed.")

if __name__ == "__main__":
    server = ChatServer(host='localhost', port=56789)
    try:
        server.start()
    except KeyboardInterrupt:
        print("[SHUTDOWN] Server is shutting down.")
        server.stop()
