import unittest
from client import ChatClient

class TestChatClient(unittest.TestCase):
    def setUp(self):
        """Setup the client to connect to the test server"""
        self.client = ChatClient("127.0.0.1", 56789)

    def tearDown(self):
        """Close client connection"""
        self.client.close()

    def test_create_account(self):
        """Test account creation from client side"""
        self.client.create_account("test_user", "1234")

    def test_login(self):
        """Test user login"""
        self.client.login("test_user", "1234")

    def test_send_message(self):
        """Test sending a message"""
        self.client.send_message("receiver", "Hello from client!")

    def test_list_accounts(self):
        """Test listing accounts"""
        self.client.list_accounts("*")

    def test_read_messages(self):
        """Test reading messages"""
        self.client.read_messages()

if __name__ == "__main__":
    unittest.main()
