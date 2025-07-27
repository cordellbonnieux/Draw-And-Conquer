import argparse
import json
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
        "--color-selection-timeout",
        type=int,
        default=30,
        help="Color selection timeout in seconds",
    )
    parser.add_argument(
        "--echo-port",
        type=int,
        default=None,
        help="Port number for echo server (testing only)",
    )
    return parser.parse_args()


def echo_back(
    ws: WebSocketInterface,
    _addr: Tuple[str, int],
    data: str,
    _server_state: ServerState,
) -> None:
    try:
        _ = json.loads(data)
        ws.send(data)
    except json.JSONDecodeError:
        reply = {"error": "Invalid JSON format"}
        ws.send(json.dumps(reply))


def start_echo_server(args) -> None:
    """
    Start a simple echo server for testing.
    """
    echo_server = TCPServer(args.host, args.echo_port, echo_back, ServerState())
    echo_thread = threading.Thread(target=echo_server.start, daemon=True)
    echo_thread.start()
    print(f"Echo server started on {args.host}:{args.echo_port}")


def start_servers(args) -> None:
    """
    Start the matchmaker and game servers with watchdogs.
    """
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

    # Start servers in separate threads
    matchmaker_thread = threading.Thread(target=matchmaker_server.start, daemon=True)
    game_thread = threading.Thread(target=game_server.start, daemon=True)

    matchmaker_thread.start()
    game_thread.start()

    # Start watchdog processes
    queue_watchdog_instance = QueueWatchdog(
        matchmaker_state, game_state, args.num_tiles, args.color_selection_timeout
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

    print(f"Matchmaker server started on {args.host}:{args.matchmaker_port}")
    print(f"Game server started on {args.host}:{args.games_server_port}")


def main():
    args = parse_args()

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
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down servers...")


if __name__ == "__main__":
    main()
