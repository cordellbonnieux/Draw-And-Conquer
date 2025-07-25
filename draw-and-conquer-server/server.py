import socket
import base64
import hashlib
import threading
from typing import Callable

import json # temporary import to allow WebSocketInterface to reply

# WebSocket handshake magic string; move to environment variables before deployment
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class ServerState:
    def __init__(self):
        self.lock = threading.Lock()

# Used to manage Websocket communication with client
class WebSocketInterface:
    def __init__(self, conn: socket.socket):
        self.conn = conn
    
    # establish connection
    def _handshake(self) -> bool:
        data = self.conn.recv(4096).decode("utf-8")
        if "Upgrade: websocket" not in data: # not websocket, use tcp only
            return False
        
        #Sec-WebSocket-Key
        key = next(
            (
                line.split(":")[1].strip()
                for line in data.splitlines()
                    if line.startswith("Sec-WebSocket-Key")
             ),
             None
        )
        if not key:
            return False

        #Response key using magic string
        accept_key = base64.b64encode(
            hashlib.sha1((key + WS_MAGIC).encode()).digest()
        ).decode()

        #Add key & send response
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n" 
        )
        self.conn.sendall(response.encode())
        return True

    # receive and translate
    def _receive(self) -> str:
        data = self.conn.recv(4096)
        if len(data) < 2:
            return None

        #Parse frame
        opcode = data[0] & 0x0F
        if opcode == 0x08: #close
            return None

        payload_len = data[1] & 0x7F
        mask_start = 2
        if payload_len == 126:
            mask_start = 4
        elif payload_len == 127:
            mask_start = 10
        
        masks = data[mask_start : mask_start+4]
        payload = data[mask_start+4 : mask_start+4+payload_len]
        decoded = bytes([payload[i] ^ masks[i % 4] for i in range(len(payload))])
        return decoded.decode("utf-8")
    
    # translate and send
    def _send(self, message: str) -> None:
        header = bytearray([0x81])
        payload = message.encode("utf-8")
        payload_len = len(payload)

        if payload_len <= 125:
            header.append(payload_len)
        elif payload_len <= 65535:
            header.extend([126, (payload_len >> 8) & 0xFF, payload_len & 0xFF])
        else:
            header.extend([127] + [(payload_len >> (8 * (7 - i))) & 0xFF for i in range(8)])
        
        self.conn.sendall(header + payload)

class TCPServer:
    def __init__(
        self,
        host: str,
        port: int,
        request_handler: Callable,
        server_state: ServerState,
    ):
        self.host = host
        self.port = port
        self.request_handler = request_handler
        self.server_state = server_state

    def _handle_connection(
        self,
        conn: socket.socket,
        addr: tuple[str, int],
        server_state: ServerState = None,
    ) -> None:
        try:
            with conn:
                ws = WebSocketInterface(conn)
                if ws._handshake():
                    #WebSocket ontop of TCP
                    while True:
                        message = ws._receive()
                        if not message:
                            break
                        # By-passing the request handler for now.
                        # For them to work with websockets, we need them to return json str
                        # then send it back to client using ws._send() like below
                        
                        #reply = self.request_handler(conn, addr, message, server_state)

                        # json import only used in this file for the line below
                        ws._send(json.dumps({'reply-example' : 'hello client!'}))
                else:
                    #TCP connection
                    while True:
                        data = conn.recv(65535)
                        if not data:
                            break
                        print("tcp data only", data.decode("utf-8"))
                        keep_connection = self.request_handler(
                            conn, addr, data.decode("utf-8"), server_state
                        )
                        if not keep_connection:
                            break
        except Exception:
            pass

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(128)

        try:
            while True:
                conn, addr = sock.accept()
                thread = threading.Thread(
                    target=self._handle_connection,
                    args=(conn, addr, self.server_state),
                )
                thread.daemon = True
                thread.start()
        finally:
            sock.close()


# Simple UDP server, unused
class UDPServer:
    def __init__(
        self,
        host: str,
        port: int,
        request_handler: Callable[[str], str],
    ):
        self.host = host
        self.port = port
        self.request_handler = request_handler

        self.lock = threading.Lock()

    def _handle_datagram(
        self,
        sock: socket.socket,
        data: bytes,
        addr: tuple[str, int],
    ) -> None:
        response = self.request_handler(data.decode("utf-8"))
        with self.lock:
            sock.sendto(response.encode("utf-8"), addr)

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))

        try:
            while True:
                data, addr = sock.recvfrom(65535)
                thread = threading.Thread(
                    target=self._handle_datagram, args=(sock, data, addr)
                )
                thread.daemon = True
                thread.start()
        finally:
            sock.close()