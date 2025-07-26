import json
import time
from collections import OrderedDict

from server import ServerState, WebSocketInterface


class MatchmakerState(ServerState):
    def __init__(self, lobby_size: int, heartbeat_timeout: int):
        super().__init__()
        self.matchmaking_queue: OrderedDict[str, dict] = OrderedDict()
        self.lobby_size = lobby_size
        self.heartbeat_timeout = heartbeat_timeout

    def enqueue_player(self, player_id: str, ws: WebSocketInterface) -> None:
        with self.lock:
            self.matchmaking_queue[player_id] = {
                "last_heartbeat": time.time(),
                "ws": ws,
            }

    def dequeue_player(self) -> tuple[str, dict] | None:
        with self.lock:
            if self.matchmaking_queue:
                return self.matchmaking_queue.popitem(last=False)
            return None

    def remove_player(self, player_id: str) -> None:
        with self.lock:
            if player_id in self.matchmaking_queue:
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


def matchmaker_request_handler(
    ws: WebSocketInterface,
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

            server_state.enqueue_player(player_id, ws)
            queue_length = server_state.get_queue_length()
            reply = {
                "command": "enqueue",
                "status": "success",
                "queue_length": queue_length,
            }
            reply_json = json.dumps(reply)
            ws.send(reply_json)
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
            reply_json = json.dumps(reply)
            ws.send(reply_json)
            return True

        elif command == "remove_from_queue":
            if not server_state.is_player_in_queue(player_id):
                raise ValueError("remove_from_queue", "Player not in queue")

            reply = {
                "command": "remove_from_queue",
                "status": "success",
            }
            reply_json = json.dumps(reply)
            ws.send(reply_json)
            server_state.remove_player(player_id)
            return False

        else:
            reply = {
                "command": "generic_error",
                "status": "error",
                "error": "Unknown command",
            }
            reply_json = json.dumps(reply)
            ws.send(reply_json)
            return True

    except json.JSONDecodeError:
        reply = {
            "command": "generic_error",
            "status": "error",
            "error": "Invalid JSON format",
        }
        reply_json = json.dumps(reply)
        ws.send(reply_json)
        return True

    except ValueError as e:
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
                "error": str(e),
            }
        reply_json = json.dumps(reply)
        ws.send(reply_json)
        return True
