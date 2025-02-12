# server/protocol_json.py

import json

def create_msg(cmd, src="", to="", body="", err=False):
    """
    Creates a JSON-encoded message with a trailing newline.
    """
    msg = {
        "cmd": cmd,
        "from": src,
        "to": to,
        "body": body,
        "error": err
    }
    return (json.dumps(msg) + "\n").encode()
