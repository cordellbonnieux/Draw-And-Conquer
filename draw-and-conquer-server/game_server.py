import json
import logging
import time
from typing import Dict, List, Optional, Set, Tuple

from server import ServerState, WebSocketInterface

logger = logging.getLogger(__name__)


class GameSession:
    """
    Manages a single game session including players, tiles, and game state.
    """

    def __init__(
        self,
        game_session_uuid: str,
        player_ids: List[str],
        player_names: Dict[str, str],
        num_tiles: int,
        colour_selection_timeout: int,
    ):
        """
        Initialize a new game session.

        Args:
            game_session_uuid (str): Unique identifier for the game session
            player_ids (List[str]): List of player unique identifiers
            player_names (Dict[str, str]): Mapping of player IDs to display names
            num_tiles (int): Total number of tiles in the game
            colour_selection_timeout (int): Timeout for colour selection phase in seconds
        """
        self.game_session_uuid = game_session_uuid
        self.player_ids = player_ids
        self.player_names = player_names
        self.num_tiles = num_tiles
        self.colour_selection_timeout = colour_selection_timeout
        self.tiles_to_win = (num_tiles // len(player_ids)) + 1

        logger.info("Session %s: Game created", game_session_uuid)

        self.available_colours = [
            "red",
            "blue",
            "green",
            "yellow",
            "purple",
            "orange",
            "pink",
            "cyan",
        ]

        self.player_colours: Dict[str, str] = {}
        self.player_websockets: Dict[str, WebSocketInterface] = {}
        self.colours_requested: Set[str] = set()
        self.last_colour_request: Dict[str, float] = {}

        self.tile_owners: Dict[int, str] = {}
        self.tile_locks: Dict[int, str] = {}

        self.game_started = False
        self.game_ended = False
        self.winner: Optional[str] = None

        current_time = time.time()
        for player_id in player_ids:
            self.last_colour_request[player_id] = current_time

    def broadcast_message(
        self,
        message: Dict,
        exclude_player: Optional[str] = None,
    ) -> None:
        """
        Broadcast a message to players in the game session.

        Args:
            message (Dict): Message json to send
            exclude_player (str): Player ID to exclude from broadcast
        """
        for player_id, player_ws in self.player_websockets.items():
            if exclude_player and player_id == exclude_player:
                continue

            try:
                player_ws.send(json.dumps(message))
            except (ConnectionError, OSError, BrokenPipeError):
                pass

    def assign_colour(self, player_id: str) -> str:
        """
        Assign a colour to a player.

        Args:
            player_id (str): Unique identifier for the player

        Returns:
            str: The assigned colour for the player
        """
        if player_id in self.player_colours:
            logger.info(
                "Session %s: Player %s already has colour %s",
                self.game_session_uuid,
                player_id,
                self.player_colours[player_id],
            )
            return self.player_colours[player_id]

        if not self.available_colours:
            logger.error(
                "Session %s: No colours available for player %s",
                self.game_session_uuid,
                player_id,
            )
            raise ValueError("No colours available")

        colour = self.available_colours.pop(0)
        self.player_colours[player_id] = colour
        self.colours_requested.add(player_id)
        self.last_colour_request[player_id] = time.time()

        logger.info(
            "Session %s: Assigned colour %s to player %s",
            self.game_session_uuid,
            colour,
            player_id,
        )
        return colour

    def all_colours_assigned(self) -> bool:
        """
        Check if all players have been assigned colours.

        Returns:
            bool: True if all players have assigned colours, False otherwise
        """
        return len(self.colours_requested) == len(self.player_ids)

    def register_websocket(self, player_id: str, ws: WebSocketInterface) -> None:
        """
        Register a websocket for a player.

        Args:
            player_id (str): Unique identifier for the player
            ws (WebSocketInterface): WebSocket connection for the player
        """
        if (
            player_id not in self.player_websockets
            or self.player_websockets[player_id] != ws
        ):
            self.player_websockets[player_id] = ws
            logger.debug(
                "Session %s: WebSocket registered for player %s",
                self.game_session_uuid,
                player_id,
            )

    def get_inactive_players(self) -> List[str]:
        """
        Get list of players who haven't requested a colour and are inactive.

        Returns:
            List[str]: List of inactive player IDs
        """
        if self.game_started:
            return []

        current_time = time.time()
        inactive_players = []
        for player_id in self.player_ids:
            if player_id not in self.colours_requested:
                time_since_request = current_time - self.last_colour_request[player_id]
                if time_since_request > self.colour_selection_timeout:
                    inactive_players.append(player_id)
                    logger.warning(
                        "Session %s: Player %s inactive (%ds)",
                        self.game_session_uuid,
                        player_id,
                        time_since_request,
                    )

        return inactive_players

    def remove_player(self, player_id: str) -> None:
        """
        Remove a player from the game session.

        Args:
            player_id (str): Unique identifier for the player to remove
        """
        logger.info("Session %s: Removing player %s", self.game_session_uuid, player_id)

        if player_id in self.player_ids:
            self.player_ids.remove(player_id)
        if player_id in self.player_websockets:
            del self.player_websockets[player_id]
        if player_id in self.player_colours:
            del self.player_colours[player_id]
        if player_id in self.colours_requested:
            self.colours_requested.remove(player_id)
        if player_id in self.last_colour_request:
            del self.last_colour_request[player_id]

        # Remove any tile locks held by this player
        tiles_to_unlock = [
            tile for tile, owner in self.tile_locks.items() if owner == player_id
        ]
        if tiles_to_unlock:
            logger.debug(
                "Session %s: Unlocked %d tiles for player %s",
                self.game_session_uuid,
                len(tiles_to_unlock),
                player_id,
            )

        for tile in tiles_to_unlock:
            del self.tile_locks[tile]

        logger.debug(
            "Session %s: Player %s removed (%d remaining)",
            self.game_session_uuid,
            player_id,
            len(self.player_ids),
        )

    def lock_tile(self, tile_index: int, player_id: str) -> bool:
        """
        Lock a tile for a player.

        Args:
            tile_index (int): Index of the tile to lock
            player_id (str): Unique identifier for the player

        Returns:
            bool: True if locking was successful, False otherwise
        """
        if tile_index in self.tile_locks:
            logger.debug(
                "Session %s: Tile %d already locked by player %s, cannot lock for player %s",
                self.game_session_uuid,
                tile_index,
                self.tile_locks[tile_index],
                player_id,
            )
            return False

        self.tile_locks[tile_index] = player_id
        logger.debug(
            "Session %s: Player %s locked tile %d",
            self.game_session_uuid,
            player_id,
            tile_index,
        )
        return True

    def unlock_tile(self, tile_index: int, player_id: str, claim: bool = False) -> bool:
        """
        Unlock a tile. If claim=True, assign ownership to player.

        Args:
            tile_index (int): Index of the tile to unlock
            player_id (str): Unique identifier for the player
            claim (bool): Whether to claim ownership of the tile

        Returns:
            bool: True if unlocking was successful, False otherwise
        """
        if (
            tile_index not in self.tile_locks
            or self.tile_locks[tile_index] != player_id
        ):
            logger.debug(
                "Session %s: Cannot unlock tile %d for player %s, tile not locked by this player",
                self.game_session_uuid,
                tile_index,
                player_id,
            )
            return False

        del self.tile_locks[tile_index]

        if claim:
            self.tile_owners[tile_index] = player_id
            logger.info(
                "Session %s: Player %s claimed tile %d",
                self.game_session_uuid,
                player_id,
                tile_index,
            )

            # Check for win condition
            player_tiles = sum(
                1 for owner in self.tile_owners.values() if owner == player_id
            )

            if player_tiles >= self.tiles_to_win:
                self.game_ended = True
                self.winner = player_id
                logger.info(
                    "Session %s: Player %s wins with %d tiles.",
                    self.game_session_uuid,
                    player_id,
                    player_tiles,
                )
        else:
            logger.debug(
                "Session %s: Player %s unlocked tile %d without claiming",
                self.game_session_uuid,
                player_id,
                tile_index,
            )

        return True

    def has_enough_players(self, min_players: int = 2) -> bool:
        """
        Check if the game session has enough players to continue.

        Args:
            min_players (int): Minimum number of players required

        Returns:
            bool: True if enough players, False otherwise
        """
        return len(self.player_ids) >= min_players


class GameServerState(ServerState):
    """
    Manages multiple game sessions and provides thread-safe access.
    """

    def __init__(self):
        """
        Initialize game server state.
        """
        super().__init__()
        self.game_sessions: Dict[str, GameSession] = {}

    def create_game_session(
        self,
        game_session_uuid: str,
        player_ids: List[str],
        player_names: Dict[str, str],
        num_tiles: int,
        colour_selection_timeout: int,
    ) -> None:
        """
        Create a new game session.

        Args:
            game_session_uuid (str): Unique identifier for the game session
            player_ids (List[str]): List of player unique identifiers
            player_names (Dict[str, str]): Mapping of player IDs to display names
            num_tiles (int): Total number of tiles in the game
            colour_selection_timeout (int): Timeout for colour selection phase in seconds
        """
        with self.lock:
            self.game_sessions[game_session_uuid] = GameSession(
                game_session_uuid,
                player_ids,
                player_names,
                num_tiles,
                colour_selection_timeout,
            )

    def get_game_session(self, game_session_uuid: str) -> Optional[GameSession]:
        """
        Get a game session by UUID.

        Args:
            game_session_uuid (str): Unique identifier for the game session

        Returns:
            Optional[GameSession]: Game session object or None if not found
        """
        with self.lock:
            return self.game_sessions.get(game_session_uuid)

    def remove_game_session(self, game_session_uuid: str) -> None:
        """
        Remove a game session.

        Args:
            game_session_uuid (str): Unique identifier for the game session to remove
        """
        with self.lock:
            if game_session_uuid in self.game_sessions:
                del self.game_sessions[game_session_uuid]
                logger.info("Session %s: Game removed", game_session_uuid)
            else:
                logger.warning(
                    "Attempted to remove non-existent game session %s",
                    game_session_uuid,
                )

    def is_player_in_session(self, game_session_uuid: str, player_id: str) -> bool:
        """
        Check if a player belongs to a game session.

        Args:
            game_session_uuid (str): Unique identifier for the game session
            player_id (str): Unique identifier for the player

        Returns:
            bool: True if player is in session, False otherwise
        """
        session = self.get_game_session(game_session_uuid)
        return session is not None and player_id in session.player_ids


def game_server_request_handler(
    ws: WebSocketInterface,
    addr: Tuple[str, int],
    data: str,
    server_state: GameServerState,
) -> None:
    """
    Handle WebSocket requests for the game server.

    Args:
        ws (WebSocketInterface): WebSocket connection to the client
        _addr (Tuple[str, int]): Client address information
        data (str): Raw JSON message from the client
        server_state (GameServerState): Shared game server state
    """
    try:
        request: Dict = json.loads(data)

        # Extract required fields
        game_session_uuid = request.get("game_session_uuid")
        player_id = request.get("uuid")
        command = request.get("command")

        if not game_session_uuid:
            logger.warning("Request missing game session UUID from %s", addr)
            raise ValueError("Missing game session UUID")
        if not player_id:
            logger.warning("Request missing player UUID from %s", addr)
            raise ValueError("Missing player UUID")
        if not command:
            logger.warning("Request missing command from %s", addr)
            raise ValueError("Missing command")

        # Verify player belongs to game session
        if not server_state.is_player_in_session(game_session_uuid, player_id):
            logger.warning(
                "Player %s not authorized for session %s",
                player_id,
                game_session_uuid,
            )
            raise ValueError("Player not in game session")

        session = server_state.get_game_session(game_session_uuid)
        if not session:
            logger.error(
                "Session %s: Game not found for player %s",
                game_session_uuid,
                player_id,
            )
            raise ValueError("Game session not found")

        # Register websocket for this player
        session.register_websocket(player_id, ws)

        if session.game_ended:
            logger.warning(
                "Session %s: Player %s attempted action on ended game",
                game_session_uuid,
                player_id,
            )
            raise ValueError("Game has already ended")

        logger.info(
            "Session %s: Processing command '%s' for player %s",
            game_session_uuid,
            command,
            player_id,
        )

        # Handle different commands
        if command == "pen_colour_request":
            colour = session.assign_colour(player_id)
            reply = {
                "command": "pen_colour_response",
                "status": "success",
                "colour": colour,
            }
            ws.send(json.dumps(reply))
            logger.debug(
                "Session %s: Colour response %s sent to player %s",
                game_session_uuid,
                colour,
                player_id,
            )

            # Check if all players have colours assigned
            if session.all_colours_assigned():
                logger.info(
                    "Session %s: All players have colours assigned, starting game",
                    game_session_uuid,
                )
                # Prepare player infos for all players
                players_info = {}
                for pid in session.player_ids:
                    players_info[pid] = {
                        "colour": session.player_colours[pid],
                        "name": session.player_names[pid],
                    }

                # Broadcast current players to all
                current_players_message = {
                    "command": "current_players",
                    "players": players_info,
                }
                session.broadcast_message(current_players_message)
                session.game_started = True
                logger.info(
                    "Session %s: Game started with players: %s",
                    game_session_uuid,
                    list(players_info.keys()),
                )

        elif command == "pen_down":
            tile_index = request.get("index")
            if tile_index is None:
                logger.warning(
                    "Session %s: Pen down request missing tile index from player %s",
                    game_session_uuid,
                    player_id,
                )
                raise ValueError("Missing tile index")

            if not session.lock_tile(tile_index, player_id):
                logger.warning(
                    "Session %s: Player %s failed to lock tile %d, already locked",
                    game_session_uuid,
                    player_id,
                    tile_index,
                )
                raise ValueError("Tile already locked")

            # Send response to requesting player
            reply = {
                "status": "success",
            }
            ws.send(json.dumps(reply))

            # Broadcast to other players
            broadcast_message = {
                "command": "pen_down_broadcast",
                "index": tile_index,
                "colour": session.player_colours[player_id],
            }
            session.broadcast_message(broadcast_message, player_id)
            logger.debug(
                "Session %s: Pen down broadcast for tile %d by player %s",
                game_session_uuid,
                tile_index,
                player_id,
            )

        elif command in ["pen_up_tile_claimed", "pen_up_tile_not_claimed"]:
            tile_index = request.get("index")
            if tile_index is None:
                logger.warning(
                    "Session %s: Pen up request missing tile index from player %s",
                    game_session_uuid,
                    player_id,
                )
                raise ValueError("Missing tile index")

            claim_tile = command == "pen_up_tile_claimed"
            if not session.unlock_tile(tile_index, player_id, claim=claim_tile):
                logger.warning(
                    "Session %s: Player %s failed to unlock tile %d, not locked by this player",
                    game_session_uuid,
                    player_id,
                    tile_index,
                )
                raise ValueError("Tile not locked by this player")

            # Send response to requesting player
            reply = {
                "status": "success",
            }
            ws.send(json.dumps(reply))

            # Broadcast to other players
            broadcast_message = {
                "command": "pen_up_broadcast",
                "index": tile_index,
                "colour": session.player_colours[player_id],
                "status": command,
            }
            session.broadcast_message(broadcast_message, player_id)
            logger.debug(
                "Session %s: Pen up broadcast for tile %d by player %s",
                game_session_uuid,
                tile_index,
                player_id,
            )

            # Check for win condition
            if session.game_ended:
                game_win_message = {
                    "command": "game_win",
                    "winner_uuid": session.winner,
                    "winner_name": session.player_names[session.winner],
                    "winner_colour": session.player_colours[session.winner],
                }
                session.broadcast_message(game_win_message)
                logger.info(
                    "Session %s: Game ended! Winner: %s",
                    game_session_uuid,
                    session.winner,
                )

        else:
            logger.warning(
                "Session %s: Unknown command '%s' from player %s",
                game_session_uuid,
                command,
                player_id,
            )
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
