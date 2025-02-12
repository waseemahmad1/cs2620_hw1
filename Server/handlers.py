from .protocol_json import create_msg
from Server.data_store import users, active_users, get_matching_users, get_unread_messages, get_conversation, store_message, get_unread_message_count
import json

def handle_login(server, conn, parts):
    cmd = parts.get("cmd")
    username = parts.get("from")
    password = parts.get("password", "")

    if username not in users:
        conn.send(create_msg(cmd, body="Invalid or incorrect username", err=True))
        return

    stored_hash = users[username]["password_hash"]
    if stored_hash != server.hash_password(password):
        conn.send(create_msg(cmd, body="Invalid or incorrect password", err=True))
        return

    if username in active_users:
        conn.send(create_msg(cmd, body="You are already logged in!", err=True))
        return

    # Correctly fetch unread message count
    unread_count = get_unread_message_count(username)

    active_users[username] = conn
    conn.send(create_msg(cmd, body=f"Login successful! You have {unread_count} unread messages", to=username))
            
def handle_delete(server, conn, parts):
    cmd = parts.get("cmd")
    username = parts.get("from")

    if username not in users:
        conn.send(create_msg(cmd, body="The user does not exist", err=True))
        return

    # Remove messages sent by this user from all other users
    for recipient in users:
        users[recipient]["messages"] = [msg for msg in users[recipient]["messages"] if msg["sender"] != username]

    # Delete the user account
    del users[username]

    # Remove from active users if logged in
    if username in active_users:
        del active_users[username]

    conn.send(create_msg(cmd, body="Account has been successfully deleted."))
    # log out after deleting account

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
    """ Fetches unread messages (with a user-specified limit) and marks them as read. """
    cmd = parts.get("cmd")
    username = parts.get("from")

    if username not in users:
        conn.send(create_msg(cmd, body="User not found", err=True))
        return

    limit = parts.get("body", "")
    try:
        limit = int(limit) if limit else None
    except ValueError:
        limit = None

    unread_messages = get_unread_messages(username, limit)

    if not unread_messages:
        conn.send(create_msg(cmd, body="No unread messages"))
    else:
        for msg in unread_messages:
            conn.send(create_msg("read", src=msg["sender"], body=msg["text"]))


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
        return

    # Store the message with a "read" status
    store_message(username, recipient, message)

    if recipient in active_users:
        try:
            active_users[recipient].send(create_msg("read", src=username, body=message))
        except Exception as e:
            print(f"Error sending message to {recipient}: {e}")

    conn.send(create_msg(cmd, body="Your message has been sent"))

def handle_view_conv(server, conn, parts):
    """ Fetches full conversation history and marks unread messages as read. """
    cmd = parts.get("cmd")
    username = parts.get("from")
    other_user = parts.get("to", "")

    if other_user not in users:
        conn.send(create_msg(cmd, body="User not found", err=True))
        return

    conversation = get_conversation(username, other_user)

    if not conversation:
        conn.send(create_msg(cmd, body="No conversation history found"))
    else:
        convo_str = "\n".join(f"{msg['sender']}: {msg['text']}" for msg in conversation)
        conn.send(create_msg("view_conv", to=other_user, body=convo_str))

