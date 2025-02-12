# client_custom.py
import socket
import struct
import threading
import time
import sys
from protocol_custom import (
    CMD_LOGIN, CMD_CREATE, CMD_SEND, CMD_READ, CMD_DELETE_MSG,
    CMD_VIEW_CONV, CMD_DELETE_ACC, CMD_LOGOFF, CMD_CLOSE,
    encode_message, decode_message, pack_short_string, pack_long_string,
    unpack_short_string, unpack_long_string
)

# --- Helper functions to pack commands ---
def pack_login(username, password):
    return pack_short_string(username) + pack_short_string(password)

def pack_create(username, password):
    return pack_short_string(username) + pack_short_string(password)

def pack_send(sender, recipient, message):
    return pack_short_string(sender) + pack_short_string(recipient) + pack_long_string(message)

def pack_read(username, limit):
    # limit is 1 byte (0 means all)
    return pack_short_string(username) + struct.pack("!B", limit)

def pack_delete_msg(username, indices):
    data = pack_short_string(username)
    data += struct.pack("!B", len(indices))
    for idx in indices:
        data += struct.pack("!B", idx)
    return data

def pack_view_conv(username, other_user):
    return pack_short_string(username) + pack_short_string(other_user)

def pack_delete_acc(username):
    return pack_short_string(username)

def pack_logoff(username):
    return pack_short_string(username)

def pack_close(username):
    return pack_short_string(username)

# --- ChatClient class ---
class ChatClient:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.username = None

    def login(self, username, password):
        self.sock.sendall(encode_message(CMD_LOGIN, pack_login(username, password)))
        cmd, payload = decode_message(self.sock)
        response, _ = unpack_short_string(payload, 0)
        if "successful" in response:
            self.username = username
        print("Login response:", response)

    def create_account(self, username, password):
        self.sock.sendall(encode_message(CMD_CREATE, pack_create(username, password)))
        cmd, payload = decode_message(self.sock)
        response, _ = unpack_short_string(payload, 0)
        print("Create account response:", response)

    def send_message(self, recipient, message):
        if self.username is None:
            print("Please login first.")
            return
        self.sock.sendall(encode_message(CMD_SEND, pack_send(self.username, recipient, message)))
        cmd, payload = decode_message(self.sock)
        response, _ = unpack_short_string(payload, 0)
        print("Send message response:", response)

    def read_messages(self, limit=0):
        if self.username is None:
            print("Please login first.")
            return
        self.sock.sendall(encode_message(CMD_READ, pack_read(self.username, limit)))
        print("Reading messages:")
        try:
            # We'll read messages until a non-CMD_READ response is encountered.
            while True:
                cmd, payload = decode_message(self.sock)
                if cmd != CMD_READ:
                    # Not a read response—push it back or break.
                    break
                sender, offset = unpack_short_string(payload, 0)
                message, offset = unpack_long_string(payload, offset)
                print(f"From {sender}: {message}")
        except Exception as e:
            pass

    def delete_messages(self, indices):
        if self.username is None:
            print("Please login first.")
            return
        self.sock.sendall(encode_message(CMD_DELETE_MSG, pack_delete_msg(self.username, indices)))
        cmd, payload = decode_message(self.sock)
        response, _ = unpack_short_string(payload, 0)
        print("Delete message response:", response)

    def view_conversation(self, other_user):
        if self.username is None:
            print("Please login first.")
            return
        self.sock.sendall(encode_message(CMD_VIEW_CONV, pack_view_conv(self.username, other_user)))
        cmd, payload = decode_message(self.sock)
        if cmd == CMD_VIEW_CONV:
            conv, _ = unpack_long_string(payload, 0)
            print("Conversation:", conv)
        else:
            response, _ = unpack_short_string(payload, 0)
            print("View conversation response:", response)

    def delete_account(self):
        if self.username is None:
            print("Please login first.")
            return
        self.sock.sendall(encode_message(CMD_DELETE_ACC, pack_delete_acc(self.username)))
        cmd, payload = decode_message(self.sock)
        response, _ = unpack_short_string(payload, 0)
        print("Delete account response:", response)
        self.username = None

    def log_off(self):
        if self.username is None:
            print("Not logged in.")
            return
        self.sock.sendall(encode_message(CMD_LOGOFF, pack_logoff(self.username)))
        cmd, payload = decode_message(self.sock)
        response, _ = unpack_short_string(payload, 0)
        print("Logoff response:", response)
        self.username = None

    def close(self):
        uname = self.username if self.username else ""
        self.sock.sendall(encode_message(CMD_CLOSE, pack_close(uname)))
        self.sock.close()

def client_main():
    host = input("Enter server host: ")
    port = int(input("Enter server port: "))
    client = ChatClient(host, port)
    while True:
        print("\nMenu:")
        print("1. Create account")
        print("2. Login")
        print("3. Send message")
        print("4. Read messages")
        print("5. Delete messages")
        print("6. View conversation")
        print("7. Delete account")
        print("8. Log off")
        print("9. Close")
        choice = input("Choose an option: ")
        if choice == "1":
            username = input("Enter username: ")
            password = input("Enter password: ")
            client.create_account(username, password)
        elif choice == "2":
            username = input("Enter username: ")
            password = input("Enter password: ")
            client.login(username, password)
        elif choice == "3":
            recipient = input("Enter recipient username: ")
            message = input("Enter message: ")
            client.send_message(recipient, message)
        elif choice == "4":
            limit = input("Enter number of messages to read (0 for all): ")
            try:
                limit = int(limit)
            except:
                limit = 0
            client.read_messages(limit)
        elif choice == "5":
            indices = input("Enter indices to delete (comma separated): ")
            indices = [int(x.strip()) for x in indices.split(",") if x.strip().isdigit()]
            client.delete_messages(indices)
        elif choice == "6":
            other_user = input("Enter username to view conversation with: ")
            client.view_conversation(other_user)
        elif choice == "7":
            client.delete_account()
        elif choice == "8":
            client.log_off()
        elif choice == "9":
            client.close()
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    client_main()
