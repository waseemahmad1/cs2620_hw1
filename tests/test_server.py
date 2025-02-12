import unittest
import json
import socket
import threading
from server import ChatServer

class TestChatServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Start the server in a separate thread before running tests"""
        cls.server = ChatServer(host='127.0.0.1', port=56789)
        cls.server_thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        """Shutdown the server after tests"""
        cls.server.stop()
    
    def setUp(self):
        """Connect a client to the server"""
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect(('127.0.0.1', 56789))

    def tearDown(self):
        """Close client connection"""
        self.client.close()

    def send_and_receive(self, message):
        """Helper function to send a message and receive a response"""
        self.client.sendall(message)
        return self.client.recv(409600).decode()

    def test_create_account(self):
        """Test creating a new user account"""
        unique_user = f"test_user_{int(time.time())}"  # Unique username using timestamp
        msg = json.dumps({"cmd": "create", "from": unique_user, "password": "1234"}) + "\n"
        response = self.send_and_receive(msg.encode())
        self.assertIn("Account created", response)

    def test_login(self):
        """Test user login"""
        self.test_create_account()  # Ensure user exists
        msg = json.dumps({"cmd": "login", "from": "test_user", "password": "1234"}) + "\n"
        response = self.send_and_receive(msg.encode())
        self.assertIn("Login successful", response)

    def test_list_accounts(self):
        """Test listing user accounts"""
        msg = json.dumps({"cmd": "list", "from": "test_user", "body": "*"}) + "\n"
        response = self.send_and_receive(msg.encode())
        self.assertIn("test_user", response)

    def test_send_message(self):
        """Test sending a message to another user"""
        self.test_create_account()
        msg = json.dumps({"cmd": "send", "from": "test_user", "to": "receiver", "body": "Hello!"}) + "\n"
        response = self.send_and_receive(msg.encode())
        self.assertIn("Message sent", response)

    def test_read_messages(self):
        """Test reading messages"""
        self.test_send_message()
        msg = json.dumps({"cmd": "read", "from": "receiver"}) + "\n"
        response = self.send_and_receive(msg.encode())
        self.assertIn("Hello!", response)

if __name__ == "__main__":
    unittest.main()
