# Chat Application - Documentation

## Prerequisites
Ensure you have the following installed:
- Python 3.9+
- Required dependencies:
  ```bash
  pip install coverage pytest
  ```

## Running the Server
The server must be started first before clients can connect.

### Start the Server
1. Open a terminal.
2. Run the following command:
   ```bash
   python server.py
   ```
3. If successful, the output should indicate that the server is listening:
   ```
   [LISTENING] Server is listening on 127.0.0.1:56789
   ```

## Running the Command-Line Client
Once the server is running, start a client

### Start the Client
1. Open a new terminal.
2. Run:
   ```bash
   python client.py
   ```
3. When prompted, enter the server IP address:
   ```
   Enter host IP address: localhost
   ```
   Press **Enter** to use the default `localhost`.
4. Follow the on-screen options to:
   - Login
   - Create an account
   - Send messages
   - Read messages
   - List accounts
   - Delete messages
   - Log off

## Running the GUI (Graphical User Interface)
A Tkinter-based GUI is available for interaction.

### Start the GUI Client
1. Open a terminal.
2. Run:
   ```bash
   python gui.py
   ```
3. The graphical chat interface will open, where you can:
   - Login / Create an account
   - Send messages
   - View conversations
   - View accounts
   - Delete messages
   - Log off / Exit

## Running Tests & Code Coverage
### Run All Unit Tests
To ensure everything works correctly:
```bash
python -m unittest discover tests -v
```


## Troubleshooting
### Connection Refused Error
**Issue:** The client fails to connect to the server.

**Fix:** Ensure the server is running before starting the client.

### Address Already in Use Error
**Issue:** Port `56789` is already occupied.

**Fix:** Kill the existing process:
```bash
kill -9 $(lsof -t -i :56789)
```
Then restart the server.

### GUI Won't Open
**Issue:** `tkinter` module is missing.

**Fix:** Install Tkinter:
```bash
sudo apt install python3-tk  # Ubuntu
brew install python-tk        # macOS
```

## Notes
- Always start the server first before running a client.
- Use `localhost` as the server IP unless testing on another machine.
- Run tests before deployment to ensure functionality.

