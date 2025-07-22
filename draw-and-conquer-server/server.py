import socket
import threading
from typing import Callable


class ServerState:
    def __init__(self):
        self.lock = threading.Lock()


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
                while True:
                    data = conn.recv(65535)
                    if not data:
                        break

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