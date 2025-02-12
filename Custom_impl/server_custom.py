# server_custom.py
import socket
import struct
import fnmatch
import threading
import datetime
import hashlib
from Custom_impl.protocol_custom import (
    HEADER_SIZE, CMD_LOGIN, CMD_CREATE, CMD_SEND, CMD_READ, CMD_DELETE_MSG,
    CMD_VIEW_CONV, CMD_DELETE_ACC, CMD_LOGOFF, CMD_CLOSE, CMD_SEARCH_USERS,
    CMD_READ_ACK, 
    encode_message, decode_message, pack_short_string, pack_long_string,
    unpack_short_string, unpack_long_string
)

# Data stores (in memory)
users = {}        # username -> { "password": <hash>, "messages": [(sender, message), ...] }
active_users = {} # username -> connection object
conversations = {}  # (username1, username2) sorted tuple -> list of message dicts

def get_matching_users(wildcard="*"):
    """Returns a list of usernames matching the given wildcard pattern."""
    return fnmatch.filter(list(users.keys()), wildcard)

def handle_client(conn, addr):
    print(f"Connected: {addr}")
    try:
        while True:
            cmd, payload = decode_message(conn)
            # --- Process each command ---
            if cmd == CMD_LOGIN:
                # Payload: username (short string) + password (short string)
                offset = 0
                username, offset = unpack_short_string(payload, offset)
                password, offset = unpack_short_string(payload, offset)
                if username not in users:
                    response = "Username does not exist"
                    conn.sendall(encode_message(CMD_LOGIN, pack_short_string(response)))
                else:
                    hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
                    if users[username]["password"] != hashed:
                        response = "Incorrect password"
                        conn.sendall(encode_message(CMD_LOGIN, pack_short_string(response)))
                    else:
                        active_users[username] = conn
                        response = f"Login successful. Unread messages: {len(users[username]['messages'])}"
                        conn.sendall(encode_message(CMD_LOGIN, pack_short_string(response)))
            elif cmd == CMD_CREATE:
                # Payload: username (short string) + password (short string)
                offset = 0
                username, offset = unpack_short_string(payload, offset)
                password, offset = unpack_short_string(payload, offset)
                if username in users:
                    response = "Username already exists"
                    conn.sendall(encode_message(CMD_CREATE, pack_short_string(response)))
                else:
                    hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
                    users[username] = {"password": hashed, "messages": []}
                    response = "Account created"
                    conn.sendall(encode_message(CMD_CREATE, pack_short_string(response)))
            elif cmd == CMD_SEND:
                # Payload: sender (short), recipient (short), message (long)
                offset = 0
                sender, offset = unpack_short_string(payload, offset)
                recipient, offset = unpack_short_string(payload, offset)
                message, offset = unpack_long_string(payload, offset)
                # Update conversation history
                conv_key = tuple(sorted([sender, recipient]))
                if conv_key not in conversations:
                    conversations[conv_key] = []
                timestamp = datetime.datetime.now().isoformat()
                conversations[conv_key].append({"sender": sender, "message": message, "timestamp": timestamp})
                if recipient not in users:
                    response = "Recipient not found"
                    conn.sendall(encode_message(CMD_SEND, pack_short_string(response)))
                else:
                    if recipient in active_users:
                        try:
                            # Push the message immediately using CMD_READ as a response format
                            payload_resp = pack_short_string(sender) + pack_long_string(message)
                            active_users[recipient].sendall(encode_message(CMD_READ, payload_resp))
                        except Exception as e:
                            users[recipient]["messages"].append((sender, message))
                    else:
                        users[recipient]["messages"].append((sender, message))
                    response = "Message sent"
                    conn.sendall(encode_message(CMD_SEND, pack_short_string(response)))

            elif cmd == CMD_READ:
                # Extract username
                offset = 0
                username, offset = unpack_short_string(payload, offset)

                limit = struct.unpack_from("!B", payload, offset)[0] if offset < len(payload) else 0
                msgs = users.get(username, {}).get("messages", [])

                if limit > 0:
                    msgs_to_send = msgs[:limit]
                    users[username]["messages"] = msgs[limit:]
                else:
                    msgs_to_send = msgs
                    users[username]["messages"] = []

                if not msgs_to_send:
                    # If no messages, send explicit "NO_MESSAGES" signal
                    conn.sendall(encode_message(CMD_READ, pack_long_string("NO_MESSAGES")))
                else:
                    for sender, msg_text in msgs_to_send:
                        payload_resp = pack_short_string(sender) + pack_long_string(msg_text)
                        conn.sendall(encode_message(CMD_READ, payload_resp))

                    # Send a termination signal at the end
                    conn.sendall(encode_message(CMD_READ, pack_long_string("END_OF_MESSAGES")))

                # 👇 WAIT FOR CLIENT TO ACKNOWLEDGE READING COMPLETION
                cmd, _ = decode_message(conn)  # This waits for an acknowledgment
                if cmd != CMD_READ:
                    print(f"Unexpected acknowledgment: {cmd}")  # Debugging



            elif cmd == CMD_VIEW_CONV:
                # Payload: username (short) + other_user (short)
                offset = 0
                username, offset = unpack_short_string(payload, offset)
                other_user, offset = unpack_short_string(payload, offset)
                if other_user not in users:
                    response = "User not found"
                    conn.sendall(encode_message(CMD_VIEW_CONV, pack_short_string(response)))
                else:
                    conv_key = tuple(sorted([username, other_user]))
                    conv = conversations.get(conv_key, [])
                    # For simplicity, convert conversation history to a string
                    response = str(conv)
                    conn.sendall(encode_message(CMD_VIEW_CONV, pack_long_string(response)))
            elif cmd == CMD_DELETE_MSG:
                # Payload: username (short) + count (1 byte) + indices (each 1 byte)
                offset = 0
                username, offset = unpack_short_string(payload, offset)
                count = struct.unpack_from("!B", payload, offset)[0]
                offset += 1
                indices = []
                for i in range(count):
                    idx = struct.unpack_from("!B", payload, offset)[0]
                    offset += 1
                    indices.append(idx)
                current_msgs = users.get(username, {}).get("messages", [])
                new_msgs = [msg for i, msg in enumerate(current_msgs) if i not in indices]
                if username in users:
                    users[username]["messages"] = new_msgs
                response = "Specified messages deleted"
                conn.sendall(encode_message(CMD_DELETE_MSG, pack_short_string(response)))
            elif cmd == CMD_SEARCH_USERS:
                # Extract wildcard pattern from payload
                offset = 0
                wildcard, offset = unpack_short_string(payload, offset)

                # Get matching usernames using fnmatch
                matching_users = get_matching_users(wildcard)

                # Convert the list to a string response
                response = ",".join(matching_users) if matching_users else "No matching users"

                # Send response back to client
                conn.sendall(encode_message(CMD_SEARCH_USERS, pack_long_string(response)))
            elif cmd == CMD_DELETE_ACC:
                # Payload: username (short)
                offset = 0
                username, offset = unpack_short_string(payload, offset)
                if username not in users:
                    response = "User does not exist"
                    conn.sendall(encode_message(CMD_DELETE_ACC, pack_short_string(response)))
                elif len(users[username]["messages"]) > 0:
                    response = "Undelivered messages exist"
                    conn.sendall(encode_message(CMD_DELETE_ACC, pack_short_string(response)))
                else:
                    del users[username]
                    if username in active_users:
                        del active_users[username]
                    response = "Account deleted"
                    conn.sendall(encode_message(CMD_DELETE_ACC, pack_short_string(response)))
            elif cmd == CMD_LOGOFF:
                # Payload: username (short)
                offset = 0
                username, offset = unpack_short_string(payload, offset)
                if username in active_users:
                    del active_users[username]
                response = "User logged off"
                conn.sendall(encode_message(CMD_LOGOFF, pack_short_string(response)))
            elif cmd == CMD_CLOSE:
                print(f"Closing connection: {addr}")
                break
            else:
                response = "Unknown command"
                conn.sendall(encode_message(0, pack_short_string(response)))
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        conn.close()
        print(f"Connection closed: {addr}")

def main():
    HOST = "0.0.0.0"
    PORT = 56789
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((HOST, PORT))
    server_sock.listen()
    print(f"Server listening on {HOST}:{PORT}")
    try:
        while True:
            conn, addr = server_sock.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        server_sock.close()

if __name__ == "__main__":
    main()
