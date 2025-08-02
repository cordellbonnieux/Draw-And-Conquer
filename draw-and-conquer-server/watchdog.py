import json
import logging
import time
import uuid
from typing import List

from game_server import GameServerState, GameSession
from matchmaker import MatchmakerState

logger = logging.getLogger(__name__)


class QueueWatchdog:
    """
    Monitors the matchmaking queue for timeouts and creates games when enough players are ready.
    """

    def __init__(
        self,
        matchmaker_state: MatchmakerState,
        game_state: GameServerState,
        num_tiles: int,
        colour_selection_timeout: int,
    ):
        """
        Initialize the queue watchdog.

        Args:
            matchmaker_state (MatchmakerState): The matchmaker state to monitor
            game_state (GameServerState): The game server state for creating sessions
        """
        self.matchmaker_state = matchmaker_state
        self.game_state = game_state
        self.num_tiles = num_tiles
        self.colour_selection_timeout = colour_selection_timeout

    def run(self) -> None:
        """
        Main monitoring loop that runs continuously.
        """
        while True:
            time.sleep(1)
            current_time = time.time()
            self._remove_inactive_players(current_time)
            self._create_games()

    def _remove_inactive_players(self, current_time: float) -> None:
        """
        Remove players who haven't sent heartbeats within the timeout period.

        Args:
            current_time (float): Current timestamp for timeout calculations
        """
        timed_out_players = []

        # Find timed out players
        with self.matchmaker_state.lock:
            for player_id in list(self.matchmaker_state.matchmaking_queue.keys()):
                last_heartbeat = self.matchmaker_state.player_last_heartbeat.get(
                    player_id
                )
                time_since_heartbeat = current_time - last_heartbeat

                if time_since_heartbeat > self.matchmaker_state.heartbeat_timeout:
                    player_ws = self.matchmaker_state.player_websockets.get(player_id)
                    timed_out_players.append((player_id, player_ws))
                    logger.warning(
                        "Player %s timed out for %ds",
                        player_id,
                        time_since_heartbeat,
                    )

        # Notify and remove timed out players
        for player_id, player_ws in timed_out_players:
            try:
                timeout_reply = {
                    "command": "heartbeat_timeout",
                }
                player_ws.send(json.dumps(timeout_reply))
                player_ws.close()
                logger.debug("Timeout notice sent to player %s", player_id)
            except (ConnectionError, OSError, BrokenPipeError):
                logger.debug("Timeout notice failed: player %s", player_id)

            self.matchmaker_state.remove_player(player_id)

    def _create_games(self) -> None:
        """
        Create new game sessions when enough players are available.
        """
        while True:
            # Check if we have enough players for a new game
            with self.matchmaker_state.lock:
                queue_size = len(self.matchmaker_state.matchmaking_queue)
                if queue_size < self.matchmaker_state.lobby_size:
                    break

            # Create a new game session
            game_session_uuid = str(uuid.uuid4())

            # Collect players for the game
            player_ids = []
            player_names = []
            player_wss = []
            for _ in range(self.matchmaker_state.lobby_size):
                player_id, player_name, player_ws = (
                    self.matchmaker_state.dequeue_player()
                )
                if player_id:
                    player_ids.append(player_id)
                    player_names.append(player_name)
                    player_wss.append(player_ws)

            # Verify we have the correct number of players
            if len(player_ids) == self.matchmaker_state.lobby_size:
                logger.info(
                    "Session %s: Game created with players %s",
                    game_session_uuid,
                    player_ids,
                )

                player_names = {
                    player_id: player_name
                    for player_id, player_name in zip(player_ids, player_names)
                }

                # Create game session in game server state
                self.game_state.create_game_session(
                    game_session_uuid,
                    player_ids,
                    player_names,
                    self.num_tiles,
                    self.colour_selection_timeout,
                )

                # Notify players that the game has started
                for i, player_ws in enumerate(player_wss):
                    try:
                        game_start_reply = {
                            "command": "game_start",
                            "game_session_uuid": game_session_uuid,
                            "lobby_size": self.matchmaker_state.lobby_size,
                            "board_size": self.num_tiles,
                            "colour_selection_timeout": self.colour_selection_timeout,
                        }
                        player_ws.send(json.dumps(game_start_reply))
                        logger.debug(
                            "Game start notice sent to player %s", player_ids[i]
                        )
                    except (ConnectionError, OSError, BrokenPipeError):
                        logger.warning(
                            "Game start notice failed: player %s", player_ids[i]
                        )


class GameSessionWatchdog:
    """
    Monitors game sessions for inactive players during the colour selection phase.

    Args:
        game_state (GameServerState): The game server state to monitor
    """

    def __init__(self, game_state: GameServerState):
        """
        Initialize the game session watchdog.

        Args:
            game_state (GameServerState): The game server state to monitor
        """
        self.game_state = game_state

    def run(self) -> None:
        """
        Main monitoring loop that runs continuously.
        """
        while True:
            time.sleep(1)

            # Get current game sessions to check
            sessions_to_check = []
            with self.game_state.lock:
                sessions_to_check = list(self.game_state.game_sessions.items())

            for game_session_uuid, session in sessions_to_check:
                # Only monitor sessions that haven't started yet
                if session.game_started:
                    continue

                # Check for inactive players
                inactive_players = session.get_inactive_players()

                if inactive_players:
                    # Remove inactive players and handle consequences
                    self._remove_inactive_players(session, inactive_players)

                if not session.has_enough_players(2):
                    self._end_game_insufficient_players(game_session_uuid, session)

    def _remove_inactive_players(
        self, session: GameSession, inactive_players: List[str]
    ) -> None:
        """
        Handle removal of inactive players and check if game can continue.

        Args:
            session (GameSession): The game session object
            inactive_players (List[str]): List of inactive player IDs
        """
        logger.info(
            "Session %s: Removing %d inactive players: %s",
            session.game_session_uuid,
            len(inactive_players),
            inactive_players,
        )

        # Notify and remove inactive players
        for player_id in inactive_players:
            if player_id in session.player_websockets:
                try:
                    inactive_message = {
                        "command": "inactive_player",
                    }
                    session.player_websockets[player_id].send(
                        json.dumps(inactive_message)
                    )
                    session.player_websockets[player_id].close()
                    logger.debug("Inactive notice sent to player %s", player_id)
                except (ConnectionError, OSError, BrokenPipeError):
                    logger.debug("Inactive notice failed: player %s", player_id)

            session.remove_player(player_id)

    def _end_game_insufficient_players(
        self, game_session_uuid: str, session: GameSession
    ) -> None:
        """
        End a game session due to insufficient players.

        Args:
            game_session_uuid (str): UUID of the game session to end
            session (GameSession): The game session object to end
        """
        logger.info(
            "Session %s: Ending game, insufficient players",
            game_session_uuid,
        )

        not_enough_players_message = {
            "command": "not_enough_players",
        }

        # Notify remaining players
        for player_id, player_ws in session.player_websockets.items():
            try:
                player_ws.send(json.dumps(not_enough_players_message))
                player_ws.close()
                logger.debug("Insufficient players notice sent to player %s", player_id)
            except (ConnectionError, OSError, BrokenPipeError):
                logger.debug("Insufficient players notice failed: player %s", player_id)

        # Remove the game session
        self.game_state.remove_game_session(game_session_uuid)
