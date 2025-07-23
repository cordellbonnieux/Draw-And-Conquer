import json
import socket
import time
import uuid

from matchmaker import MatchmakerState


def queue_watchdog(server_state: MatchmakerState) -> None:
    while True:
        time.sleep(3)

        current_time = time.time()

        dead_players_data = []
        with server_state.lock:
            current_queue = list(server_state.matchmaking_queue.items())
            for player_id, player_data in current_queue:
                if (
                    current_time - player_data["last_heartbeat"]
                    > server_state.heartbeat_timeout
                ):
                    dead_players_data.append((player_id, player_data))

        for player_id, player_data in dead_players_data:
            try:
                conn: socket.socket = player_data["connection"]

                reply = {
                    "command": "queue_heartbeat",
                    "status": "error",
                    "error": "Heartbeat timeout",
                }
                reply = json.dumps(reply)
                conn.sendall(reply.encode("utf-8"))
                conn.close()
            except (ConnectionError, OSError, BrokenPipeError):
                pass

            server_state.remove_player(player_id)

        while True:
            with server_state.lock:
                if len(server_state.matchmaking_queue) < server_state.lobby_size:
                    break

                game_session = str(uuid.uuid4())

                players_for_game = []
                for _ in range(server_state.lobby_size):
                    player_id, player_data = server_state.dequeue_player()
                    players_for_game.append((player_id, player_data))

            for player_id, player_data in players_for_game:
                try:
                    conn: socket.socket = player_data["connection"]
                    reply = {
                        "command": "game_start",
                        "status": "success",
                        "game_session": game_session,
                    }
                    reply = json.dumps(reply)
                    conn.sendall(reply.encode("utf-8"))
                    conn.close()
                except (ConnectionError, OSError, BrokenPipeError):
                    pass
