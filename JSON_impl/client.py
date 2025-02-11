import socket
import json
import threading
import time
import sys
import os
import datetime

# Maximum message buffer size to prevent giant messages
MSGLEN = 409600

# python def to throw stderr messages
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def create_msg(cmd, src= "", to ="", body ="", extra_fields = None):
    msg = {
        "cmd": cmd,
        "from": src,
        "to": to,
        "body": body
    }

    if extra_fields and isinstance(extra_fields, dict):
        msg.update(extra_fields)

    return (json.dumps(msg) + "\n").encode()

class ChatClient:
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((server_host, server_port))
        self.username = None
        self.login_err = False

    def login(self, username, password):
        if self.username is None:
            msg = create_msg("login", src = username, extra_fields = {"password": password})
            self.sock.sendall(msg)

        else:
            eprint("You already logged in!")

    def create_account(self, username, password):
        msg = create_msg("create", src = username, extra_fields = {"password": password})
        self.sock.sendall(msg)

    def send_message(self, recipient, message):
        if not self.username:
            eprint("Error. Please log in or create an account first")
        else:
            self.sock.sendall(create_msg("send", src = self.username, to = recipient, body = message))

    def list_accounts(self, wildcard):
        self.sock.sendall(create_msg("list", src = self.username, body = wildcard))

    def receive_messages(self, limit = ""):
        self.sock.sendall(create_msg("read", src = self.username, body = str(limit)))

    def delete_messages(self, indices):
        if isinstance(indices, list):
            indices_str = ",".join(str(i) for i in indices)
        else:
            indices_str = str(indices)
        self.sock.sendall(create_msg("delete_msg", src = self.username, body = indices_str))

    def delete_account(self):
        self.sock.sendall(create_msg("delete", src = self.username))

    def log_off(self):
        self.sock.sendall(create_msg("logout", src = self.username))
        self.username = None

    def close(self):
        self.sock.sendall(create_msg("close", src = self.username))
        self.sock.close()

# Interactive system (currently only in terminal)

def handle_user():

    # keep giving user options of what they want to do until they quit
    while True:

        if not client.username:
            print("\nAvailable commands:")
            print("1. Login")
            print("2. Create an account")
            print("3. Exit")
            choice = input("Enter a number (1-3): ")

            if choice == "1":
                username = input("Please enter your username: ")
                password = input("Please enter your password: ")
                client.login(username, password)

                # wait a short bit for login response
                while not client.username:
                    if client.login_err:
                        client.login_err = False
                        break
                    time.sleep(0.1)

            elif choice == "2":
                username = input("Please create a username: ")
                password = input("Please create a password: ")
                client.create_account(username, password)

            elif choice == "3":
                client.close()
                os._exit(0)

            else:
                print("Error. Please enter a valid input (1-3).")

        else:
            print("\nAvailable commands:")
            print("1. Send a message")
            print("2. View unread messages")
            print("3. List accounts")
            print("4. Delete messages")
            print("5. Delete account")
            print("6. Log out")

            choice = input("Enter a number (1-6): ")

            if choice == "1":
                recipient = input("Who would you like to send a message to?: ")
                message = input("Enter the message you would like to send: ")
                print(datetime.datetime.now())
                client.send_message(recipient, message)

            elif choice == "2":
                limit = input("Please enter the number of messages you would like to read (leave blank to view all unread messages): ")
                client.receive_messages(limit)

            elif choice == "3":
                wildcard = input("Please enter a wildcard (optional, default '*'): ")
                client.list_accounts(wildcard)

            elif choice == "4":
                indices = input("Please enter the message indices you would like to delete (comma separated): ")
                client.delete_messages(indices)

            elif choice == "5":
                client.delete_account()

            elif choice == "6":
                client.log_off()
            else:
                print("Error. Please enter a valid input (1-6).")

def handle_message():
    buffer = ""

    while True:
        try:
            data = client.sock.recv(MSGLEN).decode()
        except Exception as e:
            eprint("Error receiving data:", e)
            break

        if not data:
            break
        buffer += data

        # Process complete messages delimited by newline
        while "\n" in buffer:
            msg_str, buffer = buffer.split("\n", 1)
            if not msg_str:
                continue
            try:
                msg = json.loads(msg_str)
            except json.JSONDecodeError:
                eprint("Received invalid JSON")
                continue

            cmd = msg.get("cmd", "")

            if cmd == "login":
                if msg.get("error", False):
                    client.login_err = True
                    print("Login failed: {}. Please try again.".format(msg.get("body", "")))
                else:
                    print("Log in successful! Welcome. {}".format(msg.get("body", "")))
                    client.username = msg.get("to", "")

            elif cmd == "read":
                print("{} sent: {}".format(msg.get("from", ""), msg.get("body", "")))
                print(datetime.datetime.now())

            elif cmd == "create":
                if msg.get("error", False):
                   print("Account creation failed: {}. Please try again.".format(msg.get("body", "")))
                else:
                    print("Account created successfully. {}".format(msg.get("body", "")))

            elif cmd == "delete":
                if msg.get("error", False):
                    print("Account deletion failed: {}. Please try again.".format(msg.get("body", "")))
                else:
                    print("Your account has been successfully deleted.")
                    client.username = None

            elif cmd == "delete_msg":
                if msg.get("error", False):
                    print("Failed to delete messages: {}. Please try again.".format(msg.get("body", "")))
                else:
                    print("Specified messages deleted successfully.")

            elif cmd == "list":
                print("Matching accounts:")
                print(msg.get("body", ""))

            elif cmd == "send":
                if msg.get("error", False):
                    print("Message send failure: {}. Please try again.".format(msg.get("body", "")))
                else:
                    print(msg.get("body", ""))

            elif cmd == "logout":
                print(msg.get("body", "Successfully logged out"))
            else:
                print("Received:", msg)
    client.sock.close()


PORT = 12345
host_ip = input("Please enter the host's IP address or localhost: ")
client = ChatClient(host_ip, PORT)

# Run the user interface and message-handling threads
threading.Thread(target=handle_user, daemon=True).start()
threading.Thread(target=handle_message, daemon=True).start()

# Prevent the main thread from exiting
while True:
    time.sleep(1)