# server/data_store.py

import fnmatch
from collections import OrderedDict

# In-memory storage of user data
# Maps: username -> { "password_hash": <str>, "messages": [ {sender: str, text: str, read: bool} ] }
users = OrderedDict()
active_users = {}

def get_matching_users(wildcard="*"):
    """ Returns a list of usernames matching the given wildcard pattern. """
    return fnmatch.filter(list(users.keys()), wildcard)

def store_message(sender, recipient, message):
    """ Stores a new message for the recipient, initially as unread. """
    if recipient in users:
        users[recipient]["messages"].append({"sender": sender, "text": message, "read": False})

def get_unread_messages(username, limit=None):
    """ Retrieves unread messages and marks them as read. """
    if username not in users:
        return []

    unread_messages = [msg for msg in users[username]["messages"] if not msg["read"]]

    if limit is not None:
        unread_messages = unread_messages[:limit]  # Limit the number of messages

    # Mark messages as read
    for msg in unread_messages:
        msg["read"] = True

    return unread_messages

def get_conversation(username, other_user):
    """ Retrieves the full conversation and marks unread messages from the other user as read. """
    if username not in users:
        return []

    conversation = [msg for msg in users[username]["messages"] if msg["sender"] == other_user or username]

    # Mark messages from the other user as read
    for msg in conversation:
        if msg["sender"] == other_user:
            msg["read"] = True

    return conversation

def get_unread_message_count(username):
    """ Returns the number of unread messages for a user. """
    if username not in users:
        return 0
    return sum(1 for msg in users[username]["messages"] if not msg["read"])
