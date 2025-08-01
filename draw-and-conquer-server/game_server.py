import json
import time
from typing import Dict, List, Optional, Set, Tuple

from server import ServerState, WebSocketInterface


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
            return self.player_colours[player_id]

        if not self.available_colours:
            raise ValueError("No colours available")

        colour = self.available_colours.pop(0)
        self.player_colours[player_id] = colour
        self.colours_requested.add(player_id)
        self.last_colour_request[player_id] = time.time()
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
        self.player_websockets[player_id] = ws

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
        return inactive_players

    def remove_player(self, player_id: str) -> None:
        """
        Remove a player from the game session.

        Args:
            player_id (str): Unique identifier for the player to remove
        """
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
        for tile in tiles_to_unlock:
            del self.tile_locks[tile]

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
            return False
        self.tile_locks[tile_index] = player_id
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
            return False

        del self.tile_locks[tile_index]

        if claim:
            self.tile_owners[tile_index] = player_id

            # Check for win condition
            player_tiles = sum(
                1 for owner in self.tile_owners.values() if owner == player_id
            )
            if player_tiles >= self.tiles_to_win:
                self.game_ended = True
                self.winner = player_id

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
    _addr: Tuple[str, int],
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
            raise ValueError("Missing game session UUID")
        if not player_id:
            raise ValueError("Missing player UUID")
        if not command:
            raise ValueError("Missing command")

        # Verify player belongs to game session
        if not server_state.is_player_in_session(game_session_uuid, player_id):
            raise ValueError("Player not in game session")

        session = server_state.get_game_session(game_session_uuid)
        if not session:
            raise ValueError("Game session not found")

        # Register websocket for this player
        session.register_websocket(player_id, ws)

        if session.game_ended:
            raise ValueError("Game has already ended")

        # Handle different commands
        if command == "pen_colour_request":
            colour = session.assign_colour(player_id)
            reply = {
                "command": "pen_colour_response",
                "status": "success",
                "colour": colour,
            }
            ws.send(json.dumps(reply))

            # Check if all players have colours assigned
            if session.all_colours_assigned():
                # Prepare player infos for all players
                players_info = {}
                for player_id in session.player_ids:
                    players_info[player_id] = {
                        "colour": session.player_colours[player_id],
                        "name": session.player_names[player_id],
                    }

                # Broadcast current players to all
                current_players_message = {
                    "command": "current_players",
                    "players": players_info,
                }
                session.broadcast_message(current_players_message)
                session.game_started = True

        elif command == "pen_down":
            tile_index = request.get("index")
            if tile_index is None:
                raise ValueError("Missing tile index")

            if not session.lock_tile(tile_index, player_id):
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

        elif command in ["pen_up_tile_claimed", "pen_up_tile_not_claimed"]:
            tile_index = request.get("index")
            if tile_index is None:
                raise ValueError("Missing tile index")

            claim_tile = command == "pen_up_tile_claimed"
            if not session.unlock_tile(tile_index, player_id, claim=claim_tile):
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

            # Check for win condition
            if session.game_ended:
                game_win_message = {
                    "command": "game_win",
                    "winner_uuid": session.winner,
                    "winner_name": session.player_names[session.winner],
                    "winner_colour": session.player_colours[session.winner],
                }
                session.broadcast_message(game_win_message)

        else:
            raise ValueError("Unknown command")

    except json.JSONDecodeError:
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
