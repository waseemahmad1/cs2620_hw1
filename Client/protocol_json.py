# client/protocol_json.py

import json

def create_msg(cmd, src="", to="", body="", extra_fields=None):
    msg = {
        "cmd": cmd,
        "from": src,
        "to": to,
        "body": body
    }
    if extra_fields and isinstance(extra_fields, dict):
        msg.update(extra_fields)
    return (json.dumps(msg) + "\n").encode()
