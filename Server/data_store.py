# server/data_store.py

import fnmatch
from collections import OrderedDict

# In-memory storage of user data
# Maps: username -> { "password_hash": <str>, "messages": [ (sender, msgText), ... ] }
users = OrderedDict()

# Tracks currently logged-in users: username -> connection object (socket)
active_users = {}


def get_matching_users(wildcard="*"):
    """
    Returns a list of usernames matching the given wildcard pattern.
    """
    return fnmatch.filter(list(users.keys()), wildcard)
