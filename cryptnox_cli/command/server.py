# -*- coding: utf-8 -*-
"""
Module containing command for starting the server
"""
import json
import selectors
import types
import socket

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
        self._start(self.data.host, self.data.port)

        return 0

    def _start(self, host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        sock.listen()
        print(f"Listening on {(host, port)}")
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
        data = types.SimpleNamespace(addr=addr, outb=b"")
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)

    def _service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            data.outb += self._receive(sock, data.addr)

        if mask & selectors.EVENT_WRITE and data.outb:
            print(f"Echoing {data.outb!r} to {data.addr}")
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

        try:
            message_length = int(message.decode(Server._ENCODING))
        except ValueError:
            return b''

        raw_data = sock.recv(message_length)
        if not raw_data:
            self._close(sock, address)
            return b''

        return self._process_in_card(raw_data)

    def _process_in_card(self, raw_data: bytes) -> bytes:
        print('Transmitting APDU command to card')
        try:
            command = json.loads(raw_data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return b''

        if not isinstance(command, list) or not all(isinstance(b, int) and 0 <= b <= 255 for b in command):
            return b''

        try:
            response = self.card.connection._reader.send(command)
        except cryptnox_sdk_py.exceptions.CryptnoxException as error:
            print(f'Error with card: {error}')
            return b''

        print('Responding back to server')
        json_response = json.dumps(response).encode(Server._ENCODING)
        msg_length = len(json_response)
        send_length = str(msg_length).encode(Server._ENCODING)
        send_length += (' ' * (Server._HEADER_SIZE - len(send_length))).encode(Server._ENCODING)

        return send_length + json_response
