import json
import socket
import time
from collections import OrderedDict

from server import ServerState
import uuid


class MatchmakerState(ServerState):
    def __init__(self, lobby_size: int):
        super().__init__()
        self.matchmaking_queue: OrderedDict[str, dict] = OrderedDict()
        self.lobby_size = lobby_size

    def enqueue_player(self, player_id: str, conn: socket.socket) -> None:
        with self.lock:
            self.matchmaking_queue[player_id] = {
                "last_heartbeat": time.time(),
                "connection": conn,
            }

    def dequeue_player(self) -> tuple[str, dict] | None:
        with self.lock:
            return self.matchmaking_queue.popitem(last=False)

    def remove_player(self, player_id: str) -> None:
        with self.lock:
            del self.matchmaking_queue[player_id]

    def heartbeat_player(self, player_id: str) -> None:
        with self.lock:
            self.matchmaking_queue[player_id]["last_heartbeat"] = time.time()

    def is_player_in_queue(self, player_id: str) -> bool:
        with self.lock:
            return player_id in self.matchmaking_queue

    def get_queue_length(self) -> int:
        with self.lock:
            return len(self.matchmaking_queue)


def request_handler(
    conn: socket.socket,
    _addr: tuple[str, int],
    data: str,
    server_state: MatchmakerState,
) -> bool:
    try:
        request: dict = json.loads(data)

        player_id = request.get("uuid", None)
        if not player_id:
            raise ValueError("Missing player UUID")

        command = request.get("command")
        if not command:
            raise ValueError("Missing command")

        if command == "enqueue":
            if server_state.is_player_in_queue(player_id):
                raise ValueError("enqueue", "Player already in queue")

            server_state.enqueue_player(player_id, conn)
            queue_length = server_state.get_queue_length()
            reply = {
                "command": "enqueue",
                "status": "success",
                "queue_length": queue_length,
            }
            reply = json.dumps(reply)
            conn.sendall(reply.encode("utf-8"))
            return True

        elif command == "queue_heartbeat":
            if not server_state.is_player_in_queue(player_id):
                raise ValueError("queue_heartbeat", "Player not in queue")

            server_state.heartbeat_player(player_id)
            queue_length = server_state.get_queue_length()
            reply = {
                "command": "queue_heartbeat",
                "status": "success",
                "queue_length": queue_length,
            }
            reply = json.dumps(reply)
            conn.sendall(reply.encode("utf-8"))
            return True

        elif command == "remove_from_queue":
            if not server_state.is_player_in_queue(player_id):
                raise ValueError("remove_from_queue", "Player not in queue")

            reply = {
                "command": "remove_from_queue",
                "status": "success",
            }
            reply = json.dumps(reply)
            conn.sendall(reply.encode("utf-8"))
            server_state.remove_player(player_id)
            return False

        else:
            reply = {
                "command": "generic_error",
                "status": "error",
                "error": "Unknown command",
            }
            reply = json.dumps(reply)
            conn.sendall(reply.encode("utf-8"))
            return True

    except json.JSONDecodeError:
        reply = {
            "command": "generic_error",
            "status": "error",
            "error": "Invalid JSON format",
        }
        reply = json.dumps(reply)
        conn.sendall(reply.encode("utf-8"))
        return True

    except ValueError as e:
        error_message = str(e)

        if len(e.args) == 2 and all(isinstance(a, str) for a in e.args):
            command, error_detail = e.args
            reply = {
                "command": command,
                "status": "error",
                "error": error_detail,
            }
        else:
            reply = {
                "command": "generic_error",
                "status": "error",
                "error": error_message,
            }
        reply = json.dumps(reply)
        conn.sendall(reply.encode("utf-8"))
        return True


def queue_watchdog(server_state: MatchmakerState) -> None:
    while True:
        time.sleep(3)

        current_time = time.time()

        with server_state.lock:
            current_queue = list(server_state.matchmaking_queue.items())
            for player_id, player_data in current_queue:
                if current_time - player_data["last_heartbeat"] > 30:
                    try:
                        reply = {
                            "command": "queue_heartbeat",
                            "status": "error",
                            "error": "Heartbeat timeout",
                        }
                        reply = json.dumps(reply)
                        player_data["connection"].sendall(reply.encode("utf-8"))
                        player_data["connection"].close()
                    except Exception:
                        pass

                    server_state.remove_player(player_id)

        with server_state.lock:
            while len(server_state.matchmaking_queue) >= server_state.lobby_size:
                game_session = str(uuid.uuid4())
                for _ in range(server_state.lobby_size):
                    player_id, player_data = server_state.dequeue_player()
                    conn = player_data["connection"]
                    reply = {
                        "command": "game_start",
                        "status": "success",
                        "game_session": game_session,
                    }
                    reply = json.dumps(reply)
                    conn.sendall(reply.encode("utf-8"))
                    conn.close()


# mm_state = MatchmakerState(lobby_size=3)
# mm_server = TCPServer(
#     host="0.0.0.0", port=9437, handler=request_handler, state=mm_state
# )
# mm_server.start()
# watchdog_thread = threading.Thread(target=queue_watchdog, args=(mm_state,), daemon=True)
# watchdog_thread.start()
