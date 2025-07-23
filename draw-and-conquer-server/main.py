import argparse
import json
import socket
import threading
import time

from matchmaker import MatchmakerState, matchmaker_request_handler
from queue_watchdog import queue_watchdog
from server import ServerState, TCPServer


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="Host to bind",
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
        help="Port number for games server",
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
        "--echo-port",
        type=int,
        default=None,
        help="Port number for echo server, used for testing",
    )
    return parser.parse_args()


def echo_back(
    sock: socket.socket,
    _addr: tuple[str, int],
    data: str,
    _server_state: ServerState,
) -> None:
    try:
        _ = json.loads(data)

        sock.sendall(data.encode("utf-8"))
    except json.JSONDecodeError:
        reply = {"error": "Invalid JSON format"}
        reply = json.dumps(reply)

        sock.sendall(reply.encode("utf-8"))


def main():
    args = parse_args()

    if args.echo_port:
        if (
            args.echo_port == args.matchmaker_port
            or args.echo_port == args.games_server_port
        ):
            raise ValueError(
                "Echo port must be different from matchmaker and games server ports."
            )

        tcp = TCPServer(args.host, args.echo_port, echo_back, ServerState())
        tcp_thread = threading.Thread(target=tcp.start, daemon=True)
        tcp_thread.start()
    else:
        mm_state = MatchmakerState(
            lobby_size=args.lobby_size, heartbeat_timeout=args.heartbeat_timeout
        )
        mm_server = TCPServer(
            host=args.host,
            port=args.matchmaker_port,
            request_handler=matchmaker_request_handler,
            server_state=mm_state,
        )
        mm_server.start()

        watchdog_thread = threading.Thread(
            target=queue_watchdog, args=(mm_state,), daemon=True
        )
        watchdog_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
