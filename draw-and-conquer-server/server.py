import base64
import hashlib
import socket
import threading
from typing import Callable, Optional, Tuple

# RFC 6455 WebSocket magic string for handshake
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class ServerState:
    """
    Base class for server state management with thread-safe locking.
    """

    def __init__(self):
        """
        Initialize server state with thread lock.
        """
        self.lock = threading.Lock()


class WebSocketInterface:
    """
    Manages WebSocket communication with clients according to RFC 6455.

    Handles the WebSocket handshake, frame parsing, and message transmission.
    """

    def __init__(self, conn: socket.socket):
        """
        Initialize WebSocket interface.

        Args:
            conn (socket.socket): The TCP socket connection to wrap
        """
        self.conn = conn

    def handshake(self) -> bool:
        """
        Perform WebSocket handshake according to RFC 6455.

        Returns:
            bool: True if handshake successful, False otherwise
        """
        try:
            data = self.conn.recv(4096).decode("utf-8")
            if "Upgrade: websocket" not in data:
                return False

            # Extract Sec-WebSocket-Key from headers
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

            # Generate accept key using RFC 6455 algorithm
            accept_key = base64.b64encode(
                hashlib.sha1((key + WS_MAGIC).encode()).digest()
            ).decode()

            # Send WebSocket handshake response
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
            )
            self.conn.sendall(response.encode())
            return True
        except (ConnectionError, OSError, BrokenPipeError):
            return False

    def receive(self) -> Optional[str]:
        """
        Receive and decode a WebSocket frame.

        Returns:
            Optional[str]: Decoded message string, or None if connection closed/error
        """
        try:
            data = self.conn.recv(4096)
            if len(data) < 2:
                return None

            # Parse WebSocket frame header
            opcode = data[0] & 0x0F
            if opcode == 0x08:
                return None

            payload_len = data[1] & 0x7F
            mask_start = 2

            # Handle extended payload lengths (RFC 6455 sections 5.2)
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

            # Verify we have complete frame
            if len(data) < mask_start + 4 + payload_len:
                return None

            # Extract masking key and payload
            masks = data[mask_start : mask_start + 4]
            payload = data[mask_start + 4 : mask_start + 4 + payload_len]

            # Unmask payload according to RFC 6455 section 5.3
            decoded = bytes([payload[i] ^ masks[i % 4] for i in range(len(payload))])
            return decoded.decode("utf-8")
        except (ConnectionError, OSError, BrokenPipeError):
            return None

    def send(self, message: str) -> None:
        """
        Encode and send a WebSocket frame.

        Args:
            message (str): The message to send to the client
        """
        try:
            # Text frame opcode (0x81 = FIN bit + text frame)
            header = bytearray([0x81])
            payload = message.encode("utf-8")
            payload_len = len(payload)

            # Add payload length according to RFC 6455 section 5.2
            if payload_len <= 125:
                header.append(payload_len)
            elif payload_len <= 65535:
                header.extend([126, (payload_len >> 8) & 0xFF, payload_len & 0xFF])
            else:
                header.extend(
                    [127] + [(payload_len >> (8 * (7 - i))) & 0xFF for i in range(8)]
                )

            self.conn.sendall(header + payload)
        except (ConnectionError, OSError, BrokenPipeError):
            pass

    def close(self) -> None:
        """
        Close the WebSocket connection.
        """
        try:
            # Send close frame according to RFC 6455 section 5.5.1
            close_frame = bytearray([0x88, 0x00])
            self.conn.sendall(close_frame)
            self.conn.close()
        except (ConnectionError, OSError, BrokenPipeError):
            pass


class TCPServer:
    """
    Multi-threaded TCP server with WebSocket support.

    Accepts incoming connections and spawns threads to handle each client
    
    Socket Handling: Creates and manages TCP socket connections, spawning
    separate threads for each client connection to handle concurrent requests.
    
    Shared Object Handling: Passes a shared ServerState object to each request
    handler to allow thread-safe access to shared server state.
    """

    def __init__(
        self,
        host: str,
        port: int,
        request_handler: Callable,
        server_state: ServerState,
    ):
        """
        Initialize TCP server.

        Args:
            host (str): Host address to bind to
            port (int): Port number to listen on
            request_handler (Callable): Function to handle client requests
            server_state (ServerState): Shared server state object
        """
        self.host = host
        self.port = port
        self.request_handler = request_handler
        self.server_state = server_state

    def _handle_connection(
        self,
        conn: socket.socket,
        addr: Tuple[str, int],
        server_state: Optional[ServerState] = None,
    ) -> None:
        """
        Handle a single client connection.
        
        This method runs in a separate thread for each client connection and:
        1. Wraps the TCP socket in a WebSocketInterface
        2. Performs WebSocket handshake
        3. Continuously receives and processes messages from the client
        4. Passes messages to the request handler with shared state
    
        Args:
            conn (socket.socket): Client connection socket
            addr (Tuple[str, int]): Client address tuple (host, port)
            server_state (Optional[ServerState]): Server state for request handler
        """
        try:
            with conn:
                ws = WebSocketInterface(conn)
                if ws.handshake():
                    # WebSocket connection established, handle messages
                    while True:
                        message = ws.receive()
                        if not message:
                            break
                        self.request_handler(ws, addr, message, server_state)
                else:
                    # WebSocket handshake failed
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
            pass

    def start(self) -> None:
        """
        Start the TCP server and listen for connections.
        
        This method creates the server socket and enters the main server loop:
        1. Creates a TCP socket and binds it to the specified host/port
        2. Sets socket options for address reuse
        3. Listens for incoming connections
        4. Accepts connections and spawns threads to handle each client
        5. Continues listening until interrupted
        """
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
