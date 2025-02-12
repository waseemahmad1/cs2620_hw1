from .protocol_json import create_msg
from .data_store import users, active_users, get_matching_users
import json

def handle_login(server, conn, parts):
    cmd = parts.get("cmd")
    username = parts.get("from")
    password = parts.get("password", "")

    if username not in users:
        conn.send(create_msg(cmd, body="Invalid or incorrect username", err=True))
    else:
        stored_hash = users[username]["password_hash"]
        if stored_hash != server.hash_password(password):
            conn.send(create_msg(cmd, body="Invalid or incorrect password", err=True))
        elif username in active_users:
            conn.send(create_msg(cmd, body="You are already logged in!", err=True))
        else:
            active_users[username] = conn
            unread_count = len(users[username]["messages"])
            conn.send(create_msg(cmd, body=f"Login successful! You have {unread_count} messages", to=username))
            
def handle_delete(server, conn, parts):
    cmd = parts.get("cmd")
    username = parts.get("from")

    if username not in users:
        conn.send(create_msg(cmd, body="The user does not exist", err=True))
    elif len(users[username]["messages"]) > 0:
        conn.send(create_msg(cmd, body="Undelivered messages still exist", err=True))
    else:
        del users[username]
        if username in active_users:
            del active_users[username]
        # You could send a response if desired, or leave it silent
        # conn.send(create_msg(cmd, body="Account has been successfully deleted!"))

def handle_logoff(server, conn, parts):
    cmd = parts.get("cmd")
    username = parts.get("from")

    if username in active_users:
        del active_users[username]
    # Optionally send a response
    # conn.send(create_msg(cmd, body="User has logged off"))


def handle_delete_msg(server, conn, parts):
    cmd = parts.get("cmd")
    username = parts.get("from")

    if username not in users:
        conn.send(create_msg(cmd, body="User not found", err=True))
        return

    raw_indices = parts.get("body", "")
    indices = []
    if isinstance(raw_indices, list):
        indices = raw_indices
    else:
        try:
            indices = [int(x.strip()) for x in raw_indices.split(",") if x.strip().isdigit()]
        except Exception:
            conn.send(create_msg(cmd, body="Invalid indices", err=True))
            return

    current_msgs = users[username]["messages"]
    new_msgs = [msg for idx, msg in enumerate(current_msgs) if idx not in indices]
    users[username]["messages"] = new_msgs
    conn.send(create_msg(cmd, body="Specified messages deleted"))

def handle_read(server, conn, parts):
    cmd = parts.get("cmd")
    username = parts.get("from")

    if username not in users:
        conn.send(create_msg(cmd, body="User not found", err=True))
    else:
        body_field = parts.get("body", "")
        limit = None
        if body_field:
            try:
                limit = int(body_field)
            except ValueError:
                limit = None

        user_messages = users[username]["messages"]
        if limit is not None:
            messages_to_read = user_messages[:limit]
            remaining_messages = user_messages[limit:]
        else:
            messages_to_read = user_messages
            remaining_messages = []

        for (sender, msg_text) in messages_to_read:
            conn.send(create_msg("read", src=sender, body=msg_text))
        users[username]["messages"] = remaining_messages

def handle_create(server, conn, parts):
    cmd = parts.get("cmd")
    username = parts.get("from")
    password = parts.get("password", "")

    if username in users:
        conn.send(create_msg(cmd, body="This username already exists", err=True))
    else:
        users[username] = {
            "password_hash": server.hash_password(password),
            "messages": []
        }
        conn.send(create_msg(cmd, body="Account has been created!", to=username))

def handle_list(server, conn, parts):
    cmd = parts.get("cmd")
    wildcard = parts.get("body", "*")
    matching_users = get_matching_users(wildcard)
    matching_str = ",".join(matching_users)
    conn.send(create_msg(cmd, body=matching_str))

def handle_send(server, conn, parts):
    cmd = parts.get("cmd")
    username = parts.get("from")
    recipient = parts.get("to")
    message = parts.get("body")

    if recipient not in users:
        conn.send(create_msg(cmd, body="User not found", err=True))
    else:
        # Store conversation history
        conv_key = tuple(sorted([username, recipient]))
        if conv_key not in server.conversations:
            server.conversations[conv_key] = []
        server.conversations[conv_key].append({"from": username, "to": recipient, "message": message})

        if recipient in active_users:
            try:
                active_users[recipient].send(create_msg("read", src=username, body=message))
            except Exception as e:
                print(f"There was an error sending your message to {recipient}: {e}")
                users[recipient]["messages"].append((username, message))
        else:
            users[recipient]["messages"].append((username, message))

        conn.send(create_msg(cmd, body="Your message has been sent"))

def handle_view_conv(server, conn, parts):
    cmd = parts.get("cmd")
    username = parts.get("from")
    other_user = parts.get("to", "")

    if other_user not in users:
        conn.send(create_msg(cmd, body="User not found", err=True))
        return

    conv_key = tuple(sorted([username, other_user]))
    conversation = server.conversations.get(conv_key, [])

    if not conversation:
        conn.send(create_msg(cmd, body="No conversation history found"))
    else:
        conv_str = json.dumps(conversation, indent=2)
        conn.send(create_msg(cmd, to=other_user, body=conv_str))

