# client/chat_client.py

import socket
import json
import sys
import time
import os
import datetime
from .protocol_json import create_msg

MSGLEN = 409600

def eprint(*args, **kwargs):
    """ Prints to stderr. """
    print(*args, file=sys.stderr, **kwargs)

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
            msg = create_msg("login", src=username, extra_fields={"password": password})
            self.sock.sendall(msg)
        else:
            eprint("You are already logged in.")

    def create_account(self, username, password):
        msg = create_msg("create", src=username, extra_fields={"password": password})
        self.sock.sendall(msg)

    def send_message(self, recipient, message):
        if not self.username:
            eprint("Please log in or create an account first")
        else:
            self.sock.sendall(create_msg("send", src=self.username, to=recipient, body=message))

    def list_accounts(self, wildcard="*"):
        self.sock.sendall(create_msg("list", src=self.username, body=wildcard))

    def read_messages(self, limit=""):
        self.sock.sendall(create_msg("read", src=self.username, body=str(limit)))

    def delete_messages(self, indices):
        if isinstance(indices, list):
            indices_str = ",".join(str(i) for i in indices)
        else:
            indices_str = str(indices)
        self.sock.sendall(create_msg("delete_msg", src=self.username, body=indices_str))

    def view_conversation(self, other_user):
        self.sock.sendall(create_msg("view_conv", src=self.username, to=other_user))

    def delete_account(self):
        self.sock.sendall(create_msg("delete", src=self.username))

    def log_off(self):
        self.sock.sendall(create_msg("logoff", src=self.username))
        self.username = None

    def close(self):
        self.sock.sendall(create_msg("close", src=self.username))
        self.sock.close()

    def handle_user(self):
        """ Handles user input via command-line. """
        while True:
            if not self.username:
                print("\nAvailable commands:")
                print("1. Login")
                print("2. Create an account")
                print("3. Exit")
                choice = input("Enter a command number (1-3): ")

                if choice == "1":
                    username = input("Enter your username: ")
                    password = input("Enter your password: ")
                    self.login(username, password)
                    while not self.username:
                        if self.login_err:
                            self.login_err = False
                            break
                        time.sleep(0.1)

                elif choice == "2":
                    username = input("Enter the username to create: ")
                    password = input("Enter your password: ")
                    self.create_account(username, password)

                elif choice == "3":
                    self.close()
                    os._exit(0)

                else:
                    print("Invalid command. Please try again.")

            else:
                print("\nAvailable commands:")
                print("1. Send a message")
                print("2. Read undelivered messages")
                print("3. List accounts")
                print("4. Delete individual messages")
                print("5. Delete account")
                print("6. Log off")
                print("7. View conversation with a user")
                choice = input("Enter a command number (1-7): ")

                if choice == "1":
                    recipient = input("Enter the recipient's username: ")
                    message = input("Enter the message: ")
                    print(datetime.datetime.now())
                    self.send_message(recipient, message)
                elif choice == "2":
                    limit = input("Enter number of messages to read (leave blank for all): ")
                    self.read_messages(limit)
                elif choice == "3":
                    wildcard = input("Enter a matching wildcard (optional, default '*'): ")
                    self.list_accounts(wildcard)
                elif choice == "4":
                    indices = input("Enter message indices to delete (comma separated): ")
                    self.delete_messages(indices)
                elif choice == "5":
                    self.delete_account()
                elif choice == "6":
                    self.log_off()
                elif choice == "7":
                    other_user = input("Enter the username to view conversation with: ")
                    self.view_conversation(other_user)
                else:
                    print("Invalid command. Please try again.")

    def handle_message(self):
        """ Handles incoming messages from the server. """
        buffer = ""
        while True:
            try:
                data = self.sock.recv(MSGLEN).decode()
            except Exception as e:
                eprint("Error receiving data:", e)
                break

            if not data:
                break
            buffer += data

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
                        self.login_err = True
                        print("Failed to login: {}. Please try again.".format(msg.get("body", "")))
                    else:
                        print("Logged in successfully. {}".format(msg.get("body", "")))
                        self.username = msg.get("to", "")

                elif cmd == "read":
                    print("{} sent: {}".format(msg.get("from", ""), msg.get("body", "")))
                    print(datetime.datetime.now())

                elif cmd == "create":
                    print(msg.get("body", "Account creation response"))

                elif cmd == "delete":
                    print(msg.get("body", "Account deletion response"))

                elif cmd == "list":
                    print("Matching accounts:")
                    print(msg.get("body", ""))

                elif cmd == "send":
                    print(msg.get("body", ""))

                elif cmd == "view_conv":
                    print("Conversation with {}:".format(msg.get("to", "")))
                    print(msg.get("body", ""))

                elif cmd == "logoff":
                    print(msg.get("body", "Logged off"))

        self.sock.close()
