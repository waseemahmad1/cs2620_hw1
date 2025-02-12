import unittest
from unittest.mock import patch
from client import ChatClient

class TestChatClient(unittest.TestCase):
    def setUp(self):
        """Setup the client to connect to the test server with mocked input."""
        with patch("builtins.input", return_value="127.0.0.1"):
            self.client = ChatClient("127.0.0.1", 56789)

    def tearDown(self):
        """Close client connection"""
        self.client.close()

    def test_create_account(self):
        """Test account creation from client side"""
        self.client.create_account("test_user", "1234")
        # Normally, we'd check server response but the function doesn't return anything.
        # Add assertions here if you modify `create_account()` to return success/failure.

    def test_login(self):
        """Test user login"""
        self.client.login("test_user", "1234")
        # Again, check response if the method is updated to return results.

    def test_send_message(self):
        """Test sending a message"""
        self.client.send_message("receiver", "Hello from client!")
        # Validate response when `send_message` provides feedback.

    def test_list_accounts(self):
        """Test listing accounts"""
        self.client.list_accounts("*")
        # Consider capturing output if `list_accounts()` is updated.

    def test_read_messages(self):
        """Test reading messages"""
        self.client.read_messages()
        # If messages are printed, capture output with `unittest.mock.patch('sys.stdout')`.

if __name__ == "__main__":
    unittest.main()
