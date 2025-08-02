import json
import logging
import time
from collections import OrderedDict
from typing import Dict, Optional, Tuple

from server import ServerState, WebSocketInterface

logger = logging.getLogger(__name__)


class MatchmakerState(ServerState):
    """
    Manages the matchmaking queue and player state with separate storage for each attribute.
    """

    def __init__(self, lobby_size: int, heartbeat_timeout: int):
        """
        Initialize matchmaker state with separate dictionaries for player data.

        Args:
            lobby_size (int): Number of players required for each game
            heartbeat_timeout (int): Timeout in seconds for player heartbeats
        """
        super().__init__()

        self.matchmaking_queue: OrderedDict[str, bool] = OrderedDict()
        self.player_last_heartbeat: Dict[str, float] = {}
        self.player_names: Dict[str, str] = {}
        self.player_websockets: Dict[str, WebSocketInterface] = {}

        self.lobby_size = lobby_size
        self.heartbeat_timeout = heartbeat_timeout

    def enqueue_player(
        self, player_id: str, player_name: str, ws: WebSocketInterface
    ) -> None:
        """
        Add a player to the matchmaking queue.

        Args:
            player_id (str): Unique identifier for the player
            player_name (str): Display name for the player
            ws (WebSocketInterface): WebSocket connection for the player
        """
        with self.lock:
            # Add to queue for ordering
            self.matchmaking_queue[player_id] = True

            # Store player data in separate dictionaries
            self.player_last_heartbeat[player_id] = time.time()
            self.player_names[player_id] = player_name
            self.player_websockets[player_id] = ws

            queue_length = len(self.matchmaking_queue)
            logger.info(
                "Player %s (%s) joined queue, queue length: %d",
                player_id,
                player_name,
                queue_length,
            )

    def dequeue_player(self) -> Optional[Tuple[str, str, WebSocketInterface]]:
        """
        Remove and return the next player from the queue.

        Returns:
            Optional[Tuple[str, str, WebSocketInterface]]: Player ID, name, and WebSocket if available
        """
        with self.lock:
            if self.matchmaking_queue:
                player_id = next(iter(self.matchmaking_queue))

                player_name = self.player_names[player_id]
                player_ws = self.player_websockets[player_id]

                del self.matchmaking_queue[player_id]
                del self.player_last_heartbeat[player_id]
                del self.player_names[player_id]
                del self.player_websockets[player_id]

                logger.debug(
                    "Dequeued player %s, queue length: %d",
                    player_id,
                    len(self.matchmaking_queue),
                )
                return (player_id, player_name, player_ws)

            logger.debug("Dequeue failed: empty queue")
            return None

    def remove_player(self, player_id: str) -> None:
        """
        Remove a specific player from the queue and all associated data.

        Args:
            player_id (str): Unique identifier for the player to remove
        """
        with self.lock:
            was_in_queue = player_id in self.matchmaking_queue
            self.matchmaking_queue.pop(player_id, None)
            self.player_last_heartbeat.pop(player_id, None)
            self.player_names.pop(player_id, None)
            self.player_websockets.pop(player_id, None)

            if was_in_queue:
                logger.info(
                    "Removed player %s, queue length: %d",
                    player_id,
                    len(self.matchmaking_queue),
                )
            else:
                logger.debug("Remove failed, player %s not in queue", player_id)

    def heartbeat_player(self, player_id: str) -> None:
        """
        Update the last heartbeat time for a player.

        Args:
            player_id (str): Unique identifier for the player
        """
        with self.lock:
            if player_id in self.matchmaking_queue:
                self.player_last_heartbeat[player_id] = time.time()
                logger.debug("Heartbeat from player %s", player_id)
            else:
                logger.warning("Heartbeat from player %s not in queue", player_id)

    def is_player_in_queue(self, player_id: str) -> bool:
        """
        Check if a player is currently in the queue.

        Args:
            player_id (str): Unique identifier for the player

        Returns:
            bool: True if player is in queue, False otherwise
        """
        with self.lock:
            return player_id in self.matchmaking_queue

    def get_queue_length(self) -> int:
        """
        Get the current number of players in the queue.

        Returns:
            int: Current number of players in the matchmaking queue
        """
        with self.lock:
            return len(self.matchmaking_queue)


def matchmaker_request_handler(
    ws: WebSocketInterface,
    addr: Tuple[str, int],
    data: str,
    server_state: MatchmakerState,
) -> None:
    """
    Handle WebSocket requests for the matchmaker server.

    Args:
        ws (WebSocketInterface): WebSocket connection for the player
        addr (Tuple[str, int]): Client address
        data (str): Incoming message data in JSON format
        server_state (MatchmakerState): Shared state for the matchmaker server
    """
    try:
        request: Dict = json.loads(data)

        player_id = request.get("uuid")
        if not player_id:
            logger.warning("Request missing player UUID from %s", addr)
            raise ValueError("Missing player UUID")

        command = request.get("command")
        if not command:
            logger.warning("Request missing command from %s", addr)
            raise ValueError("Missing command")

        # Handle different commands
        if command == "enqueue":
            if server_state.is_player_in_queue(player_id):
                logger.warning("Enqueue from player %s already in queue", player_id)
                raise ValueError("Player already in queue")

            player_name = request.get("name")
            if not player_name:
                logger.warning("Enqueue request missing player name from %s", player_id)
                raise ValueError("Missing player name")

            server_state.enqueue_player(player_id, player_name, ws)
            queue_length = server_state.get_queue_length()
            reply = {
                "status": "success",
                "queue_length": queue_length,
            }
            ws.send(json.dumps(reply))

        elif command == "queue_heartbeat":
            if not server_state.is_player_in_queue(player_id):
                logger.warning("Heartbeat from player %s not in queue", player_id)
                raise ValueError("Player not in queue")

            server_state.heartbeat_player(player_id)
            queue_length = server_state.get_queue_length()
            reply = {
                "status": "success",
                "queue_length": queue_length,
            }
            ws.send(json.dumps(reply))
            logger.debug("Heartbeat response to player %s", player_id)

        elif command == "remove_from_queue":
            if not server_state.is_player_in_queue(player_id):
                logger.warning("Remove request from player %s not in queue", player_id)
                raise ValueError("Player not in queue")

            reply = {
                "status": "success",
            }
            ws.send(json.dumps(reply))
            server_state.remove_player(player_id)
            logger.debug(
                "Player %s removed from queue, queue length: %d",
                player_id,
                server_state.get_queue_length(),
            )

        else:
            logger.warning("Unknown command '%s' from player %s", command, player_id)
            raise ValueError("Unknown command")

    except json.JSONDecodeError:
        logger.error("Invalid JSON format from %s", addr)
        reply = {
            "status": "error",
            "error": "Invalid JSON format",
        }
        ws.send(json.dumps(reply))

    except ValueError as e:
        reply = {
            "status": "error",
            "error": str(e),
        }
        ws.send(json.dumps(reply))
