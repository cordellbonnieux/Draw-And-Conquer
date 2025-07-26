import base64
import hashlib
import socket
import threading
from typing import Callable

# RFC 6455
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class ServerState:
    def __init__(self):
        self.lock = threading.Lock()


# Used to manage Websocket communication with client
class WebSocketInterface:
    def __init__(self, conn: socket.socket):
        self.conn = conn

    # establish connection
    def handshake(self) -> bool:
        data = self.conn.recv(4096).decode("utf-8")
        if "Upgrade: websocket" not in data:  # not websocket, close connection
            return False

        # Sec-WebSocket-Key
        key = next(
            (
                line.split(":")[1].strip()
                for line in data.splitlines()
                if line.startswith("Sec-WebSocket-Key")
            ),
            None,
        )
        if not key:
            return False

        # Response key using magic string
        accept_key = base64.b64encode(
            hashlib.sha1((key + WS_MAGIC).encode()).digest()
        ).decode()

        # Add key & send response
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
        )
        self.conn.sendall(response.encode())
        return True

    # receive and translate
    def receive(self) -> str:
        try:
            data = self.conn.recv(4096)
            if len(data) < 2:
                return None

            # Parse frame
            opcode = data[0] & 0x0F
            if opcode == 0x08:  # close frame
                return None

            payload_len = data[1] & 0x7F
            mask_start = 2

            # Handle extended payload lengths
            if payload_len == 126:
                if len(data) < 4:
                    return None
                payload_len = int.from_bytes(data[2:4], "big")
                mask_start = 4
            elif payload_len == 127:
                if len(data) < 10:
                    return None
                payload_len = int.from_bytes(data[2:10], "big")
                mask_start = 10

            # Check if we have enough data for masks and payload
            if len(data) < mask_start + 4 + payload_len:
                return None

            masks = data[mask_start : mask_start + 4]
            payload = data[mask_start + 4 : mask_start + 4 + payload_len]
            decoded = bytes([payload[i] ^ masks[i % 4] for i in range(len(payload))])
            return decoded.decode("utf-8")
        except (ConnectionError, OSError, BrokenPipeError):
            return None

    # translate and send
    def send(self, message: str) -> None:
        header = bytearray([0x81])
        payload = message.encode("utf-8")
        payload_len = len(payload)

        if payload_len <= 125:
            header.append(payload_len)
        elif payload_len <= 65535:
            header.extend([126, (payload_len >> 8) & 0xFF, payload_len & 0xFF])
        else:
            header.extend(
                [127] + [(payload_len >> (8 * (7 - i))) & 0xFF for i in range(8)]
            )

        self.conn.sendall(header + payload)

    # close websocket and tcp connection
    def close(self) -> None:
        try:
            # RFC 6455
            close_frame = bytearray([0x88, 0x00])
            self.conn.sendall(close_frame)
            self.conn.close()
        except (ConnectionError, OSError, BrokenPipeError):
            # Connection already closed or broken
            pass


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
                if ws.handshake():
                    while True:
                        message = ws.receive()
                        if not message:
                            break

                        keep_connection = self.request_handler(
                            ws, addr, message, server_state
                        )
                        if not keep_connection:
                            ws.close()
                            break
                else:
                    # RFC 6455
                    error_response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Connection: close\r\n"
                        "Content-Type: text/plain\r\n"
                        "Content-Length: 26\r\n"
                        "\r\n"
                        "WebSocket handshake failed"
                    )
                    conn.sendall(error_response.encode())
                    ws.close()
        except (ConnectionError, OSError, BrokenPipeError):
            # Connection already closed or broken
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
