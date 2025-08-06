import argparse
import json
import logging
import threading
import time
from typing import Tuple

from game_server import GameServerState, game_server_request_handler
from matchmaker import MatchmakerState, matchmaker_request_handler
from server import ServerState, TCPServer, WebSocketInterface
from watchdog import GameSessionWatchdog, QueueWatchdog


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="Host to bind servers to",
    )
    parser.add_argument(
        "--matchmaker-port",
        type=int,
        default=9437,
        help="Port number for matchmaker server",
    )
    parser.add_argument(
        "--games-server-port",
        type=int,
        default=9438,
        help="Port number for game server",
    )
    parser.add_argument(
        "--lobby-size",
        type=int,
        default=3,
        help="Number of players each game session should have",
    )
    parser.add_argument(
        "--heartbeat-timeout",
        type=int,
        default=30,
        help="Heartbeat timeout in seconds",
    )
    parser.add_argument(
        "--num-tiles",
        type=int,
        default=64,
        help="Number of tiles in the game",
    )
    parser.add_argument(
        "--colour-selection-timeout",
        type=int,
        default=60,
        help="Colour selection timeout in seconds",
    )
    parser.add_argument(
        "--echo-port",
        type=int,
        default=None,
        help="Port number for echo server (testing only)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level",
    )
    return parser.parse_args()


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure logging for the application.

    Args:
        log_level (str): The logging level to use (DEBUG, INFO, WARNING, ERROR)
    """
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handler to root logger
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)

    logging.info("Logging level: %s", log_level)


def echo_back(
    ws: WebSocketInterface,
    _addr: Tuple[str, int],
    data: str,
    _server_state: ServerState,
) -> None:
    """
    This function echoes back any JSON message received from a client.
    It's used for testing WebSocket connectivity and protocol implementation.
    
    Socket Handling: Receives JSON messages from client WebSocket connections
    and sends them back unchanged to test the WebSocket protocol implementation.

    Args:
        ws (WebSocketInterface): WebSocket connection to the client
        _addr (Tuple[str, int]): Client address information (unused)
        data (str): Raw JSON message from the client
        _server_state (ServerState): Server state (unused in echo mode)
    """
    try:
        _ = json.loads(data)
        ws.send(data)
    except json.JSONDecodeError:
        reply = {"error": "Invalid JSON format"}
        ws.send(json.dumps(reply))


def start_echo_server(args) -> None:
    """
    Start a simple echo server for testing.
    
    Socket Handling: Creates a TCP server that accepts WebSocket connections
    and echoes back all received messages.
    
    Shared Object Handling: Creates a simple ServerState object for the echo
    server, though it's not used in echo mode.
    """
    logging.info("Starting echo server [%s:%d]", args.host, args.echo_port)

    server_state = ServerState()
    echo_server = TCPServer(
        host=args.host,
        port=args.echo_port,
        request_handler=echo_back,
        server_state=server_state,
    )

    echo_thread = threading.Thread(target=echo_server.start, daemon=True)
    echo_thread.start()

    logging.info("Echo server started")


def start_servers(args) -> None:
    """
    Start the matchmaker and game servers with watchdogs.
    """
    logging.info("Initializing components")

    # Create server states
    matchmaker_state = MatchmakerState(
        lobby_size=args.lobby_size, heartbeat_timeout=args.heartbeat_timeout
    )
    game_state = GameServerState()

    # Create servers
    matchmaker_server = TCPServer(
        host=args.host,
        port=args.matchmaker_port,
        request_handler=matchmaker_request_handler,
        server_state=matchmaker_state,
    )

    game_server = TCPServer(
        host=args.host,
        port=args.games_server_port,
        request_handler=game_server_request_handler,
        server_state=game_state,
    )

    logging.info("Starting servers")
    # Start servers in separate threads
    matchmaker_thread = threading.Thread(target=matchmaker_server.start, daemon=True)
    game_thread = threading.Thread(target=game_server.start, daemon=True)

    matchmaker_thread.start()
    game_thread.start()

    logging.info("Starting watchdogs")
    # Start watchdog processes
    queue_watchdog_instance = QueueWatchdog(
        matchmaker_state, game_state, args.num_tiles, args.colour_selection_timeout
    )
    game_watchdog_instance = GameSessionWatchdog(game_state)

    queue_watchdog_thread = threading.Thread(
        target=queue_watchdog_instance.run, daemon=True
    )
    game_watchdog_thread = threading.Thread(
        target=game_watchdog_instance.run, daemon=True
    )

    queue_watchdog_thread.start()
    game_watchdog_thread.start()


def main():
    """
    Main entry point for the game server application.
    
    Socket Handling: Coordinates the creation and startup of TCP servers
    that accept WebSocket connections from game clients.
    
    Shared Object Handling: Initializes shared state objects that are used
    across multiple threads and processes in the server system.
    """
    args = parse_args()

    configure_logging(args.log_level)

    logging.info("Server starting")
    if args.echo_port:
        if (
            args.echo_port == args.matchmaker_port
            or args.echo_port == args.games_server_port
        ):
            raise ValueError(
                "Echo port must be different from matchmaker and game server ports."
            )
        start_echo_server(args)
    else:
        start_servers(args)

    try:
        logging.info("Server ready")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down")


if __name__ == "__main__":
    main()
