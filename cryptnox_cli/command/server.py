# -*- coding: utf-8 -*-
"""
Module containing command for starting the server
"""
import json
import selectors
import types
import socket
import secrets
import hmac
import hashlib

import cryptnox_sdk_py

from .command import Command

try:
    import enums
except ImportError:
    from .. import enums


class Server(Command):
    _name = enums.Command.SERVER.value
    _HEADER_SIZE = 64
    _ENCODING = 'utf-8'

    def _execute(self, card: cryptnox_sdk_py.Card) -> int:
        self.sel = selectors.DefaultSelector()
        self.card = card
        # Generate authentication token for this session
        self.auth_token = secrets.token_urlsafe(32)
        self.authenticated_clients = set()
        self._start(self.data.host, self.data.port)

        return 0

    def _start(self, host, port):
        # Security: Bind to localhost by default to prevent external access
        if host == '0.0.0.0' or host == '':
            print("\n" + "=" * 70)
            print("SECURITY WARNING: Binding to all interfaces (0.0.0.0)")
            print("This allows connections from any network interface.")
            print("For security, consider using 127.0.0.1 (localhost only).")
            print("=" * 70)
            response = input("\nType 'ACCEPT' to proceed with 0.0.0.0 or press Enter for localhost: ").strip()
            if response != 'ACCEPT':
                host = '127.0.0.1'
                print(f"Binding to localhost (127.0.0.1) instead.")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen()

        print("\n" + "=" * 70)
        print(f"Server started on {(host, port)}")
        print(f"Authentication Token: {self.auth_token}")
        print("\nClients must send this token in the first message to authenticate.")
        print("Keep this token secure and do not share it over insecure channels.")
        print("=" * 70 + "\n")

        sock.setblocking(False)
        self.sel.register(sock, selectors.EVENT_READ, data=None)

        try:
            self._loop()
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.sel.close()

    def _loop(self):
        while True:
            events = self.sel.select(timeout=0.1)
            self._process_events(events)

    def _process_events(self, events):
        for key, mask in events:
            if key.data is None:
                self._accept_wrapper(key.fileobj)
            else:
                self._service_connection(key, mask)

    def _accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print(f"Accepted connection from {addr}")
        conn.setblocking(False)
        # Track authentication state for this connection
        data = types.SimpleNamespace(addr=addr, outb=b"", authenticated=False)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)

    def _service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            response = self._receive(sock, data.addr)
            if response:
                data.outb += response

        if mask & selectors.EVENT_WRITE and data.outb:
            print(f"Sending response to {data.addr}")
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]

    def _close(self, sock, address):
        print(f"Closing connection to {address}")
        self.sel.unregister(sock)
        sock.close()

    def _receive(self, sock, address) -> bytes:
        print('Receiving command')
        message = sock.recv(Server._HEADER_SIZE)
        if not message:
            self._close(sock, address)
            return b''

        try:
            message_length = int(message.decode(Server._ENCODING))
        except ValueError:
            return b''

        raw_data = sock.recv(message_length)
        if not raw_data:
            self._close(sock, address)
            return b''

        return self._process_in_card(raw_data, sock, address)

    def _process_in_card(self, raw_data: bytes, sock, address) -> bytes:
        """Process incoming data - either authentication or card command."""
        # Get client's authentication state from selector
        try:
            key = self.sel.get_key(sock)
            client_data = key.data
        except KeyError:
            return self._create_error_response("Connection not found")

        # Check if client is authenticated
        if not client_data.authenticated:
            # First message should be authentication token
            try:
                data = json.loads(raw_data)
                if isinstance(data, dict) and 'auth_token' in data:
                    provided_token = data['auth_token']
                    # Use constant-time comparison to prevent timing attacks
                    if hmac.compare_digest(provided_token, self.auth_token):
                        client_data.authenticated = True
                        self.authenticated_clients.add(address)
                        print(f"Client {address} authenticated successfully")
                        return self._create_response({"status": "authenticated"})
                    else:
                        print(f"Authentication failed for {address}: invalid token")
                        return self._create_error_response("Authentication failed")
                else:
                    print(f"Authentication failed for {address}: missing auth_token")
                    return self._create_error_response("Authentication required")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self._create_error_response("Invalid authentication format")

        # Client is authenticated, process card command
        print('Transmitting APDU command to card')
        try:
            command = json.loads(raw_data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._create_error_response("Invalid command format")

        if not isinstance(command, list) or not all(isinstance(b, int) and 0 <= b <= 255 for b in command):
            return self._create_error_response("Invalid APDU command format")

        try:
            response = self.card.connection._reader.send(command)
        except cryptnox_sdk_py.exceptions.CryptnoxException as error:
            print(f'Error with card: {error}')
            return self._create_error_response(f"Card error: {error}")

        print('Responding back to client')
        return self._create_response(response)

    def _create_response(self, data) -> bytes:
        """Create a formatted response message."""
        json_response = json.dumps(data).encode(Server._ENCODING)
        msg_length = len(json_response)
        send_length = str(msg_length).encode(Server._ENCODING)
        send_length += (' ' * (Server._HEADER_SIZE - len(send_length))).encode(Server._ENCODING)
        return send_length + json_response

    def _create_error_response(self, error_message: str) -> bytes:
        """Create a formatted error response message."""
        return self._create_response({"error": error_message})
