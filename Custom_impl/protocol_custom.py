# protocol_custom.py
import struct

# --- Protocol constants and header format ---
HEADER_FORMAT = "!BH"  # 1 byte command, 2 bytes payload length (unsigned short)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Command codes
CMD_LOGIN       = 1
CMD_CREATE      = 2
CMD_SEND        = 3
CMD_READ        = 4
CMD_DELETE_MSG  = 5
CMD_VIEW_CONV   = 6
CMD_DELETE_ACC  = 7
CMD_LOGOFF      = 8
CMD_CLOSE       = 9
CMD_SEARCH_USERS = 10
CMD_READ_ACK = 11  # Acknowledgment for finished reading


# --- Helper functions for strings ---
def pack_short_string(s):
    """Packs a string with a 1-byte length prefix (max 255 bytes)."""
    b = s.encode('utf-8')
    if len(b) > 255:
        raise ValueError("String too long for short string")
    return struct.pack("!B", len(b)) + b

def unpack_short_string(data, offset):
    """Unpacks a short string from data starting at offset."""
    length = struct.unpack_from("!B", data, offset)[0]
    offset += 1
    s = data[offset:offset+length].decode('utf-8')
    offset += length
    return s, offset

def pack_long_string(s):
    """Packs a string with a 2-byte length prefix (max 65535 bytes)."""
    b = s.encode('utf-8')
    if len(b) > 65535:
        raise ValueError("String too long for long string")
    return struct.pack("!H", len(b)) + b

def unpack_long_string(data, offset):
    """Unpacks a long string from data starting at offset."""
    length = struct.unpack_from("!H", data, offset)[0]
    offset += 2
    s = data[offset:offset+length].decode('utf-8')
    offset += length
    return s, offset

# --- Message encoding/decoding ---
def encode_message(cmd, payload_bytes):
    """
    Encodes a message using a fixed header.
    Header consists of:
      - 1 byte: command code (unsigned char)
      - 2 bytes: payload length (unsigned short, network byte order)
    """
    header = struct.pack(HEADER_FORMAT, cmd, len(payload_bytes))
    return header + payload_bytes

def decode_message(sock):
    """
    Reads exactly one full message from the socket.
    Returns a tuple (cmd, payload_bytes).
    Raises an Exception if the connection is closed prematurely.
    """
    # Read the header
    header = b""
    while len(header) < HEADER_SIZE:
        chunk = sock.recv(HEADER_SIZE - len(header))
        if not chunk:
            raise Exception("Connection closed while reading header")
        header += chunk
    cmd, payload_length = struct.unpack(HEADER_FORMAT, header)
    
    # Read the payload
    payload = b""
    while len(payload) < payload_length:
        chunk = sock.recv(payload_length - len(payload))
        if not chunk:
            raise Exception("Connection closed while reading payload")
        payload += chunk
    return cmd, payload
