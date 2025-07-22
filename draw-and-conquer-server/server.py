import socket
import threading
import uuid
from typing import Callable


class TCPServer:
    def __init__(
        self,
        host: str,
        port: int,
        request_handler: Callable[[str], str],
    ):
        self.host = host
        self.port = port
        self.request_handler = request_handler

        self.clients = {}
        self.lock = threading.Lock()

    def _get_client_id(self) -> str:
        return str(uuid.uuid4())

    def _handle_connection(
        self,
        sock: socket.socket,
        addr: tuple[str, int],
    ) -> None:
        try:
            with self.lock:
                client_id = self._get_client_id()
                self.clients[client_id] = (sock, addr)

            with sock:
                while True:
                    data = sock.recv(65535)
                    if not data:
                        break

                    response = self.request_handler(data.decode("utf-8"))
                    print(response)
                    sock.sendall(response.encode("utf-8"))
        finally:
            with self.lock:
                del self.clients[client_id]

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
                    args=(conn, addr),
                )
                thread.daemon = True
                thread.start()
        finally:
            sock.close()


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