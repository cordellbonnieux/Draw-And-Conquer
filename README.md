# Draw And Conquer
## CMPT371 Group 2 Final Project

### Description
This is a browser based multiplayer game, where players compete to fill in squares in a grid by clicking down on them until they change color. Each square can only be clicked on by one player at a time. A player wins when they have colored more squares than anyone else.

### Application Flow

#### Name Input
Before joining the queue, players are prompted to enter their name. The client displays a name input form that:

- Requires a non-empty name before allowing submission
- Provides a clean, modern interface with validation
- Auto-focuses on the input field for better UX
- Shows a "Continue" button that's disabled until a valid name is entered

After entering their name, players see the queue interface with a personalized welcome message.

#### Queue Interface

The queue interface displays:
- A welcome message with the player's name: "Welcome, [PlayerName]!"
- Current queue status: "[X] of [Y] players are ready"
- A ready/not ready toggle button

Matchmaking server is always standby for players to enqueue. When player enqueues, they must provide a UUID and a name. The name is not used in the matchmaking process, but it is used to identify the player in the game session.

```json
// Client -> Server Enqueue Request
{
    "uuid": "player-uuid",
    "command": "enqueue",
    "playerName": "PlayerName"
}
// Server -> Client Enqueue Response
{
    "command": "enqueue",
    "status": "success",
    "queue_length": 2,
}
{
    "command": "enqueue",
    "status": "error",
    "error": "abcdefg",
}
```

On player enqueue, matchmaking server enqueue the UUID and client starts heartbeat the queue length. A player's queue is timeout after 60 seconds of no heartbeat.

```json
// Client -> Server Heartbeat Request
{
    "uuid": "player-uuid",
    "command": "queue_heartbeat",
}
// Server -> Client Heartbeat
{
    "command": "queue_heartbeat",
    "status": "success",
    "queue_length": 2,
}
{
    "command": "queue_heartbeat",
    "status": "error",
    "error": "abcdefg",
}
// Server -> Client Heartbeat Timeout
{
    "command": "queue_heartbeat",
    "status": "error",
    "error": "Heartbeat timeout, removed from queue",
}
```

If the queue length is greater than n, queue server will start a game server, assign different colors for players and notify the players in the queue with a game session UUID. heartbeat will stop.

```json
// Server -> Client Game Start Notification
{
    "command": "game_start",
    "game_session_uuid": "game-session-uuid",
    "lobby_size": 3,
    "board_size": 64,
    "colour_selection_timeout": 60
}
```

Player will then communicate with the game server using the provided game session UUID. Game session UUID make sure the support for multiple game sessions in parallel.

Player can leave the queue before the game starts, which will remove the player from the queue and stops the heartbeat.

```json
// Client -> Server Dequeue Request
{
    "uuid": "player-uuid",
    "command": "remove_from_queue",
}
// Server -> Client Dequeue Response
{
    "command": "remove_from_queue",
    "status": "success",
}
{
    "command": "remove_from_queue",
    "status": "error",
    "error": "abcdefg",
}
```

---

#### Game Board

After player is notified, they will communicate with the game server using the game session UUID and their UUID. If the game server determines the game session or the player dose not belong to the game session, it will return an error.

Upon transition to the game, an n x n board is created on the client, with the corresponding data structure on the server. The variable n is determined by the server on startup, and represents the number of players in a game session; i.e. when there are n players in the queue, a new game is created which generates an n x n board clientside.

- The server creates a data structure representing the grid, each cell contains a CellState: OPEN, USED (by player), CLOSED (by player)
- Each client may only start to draw on an OPEN cell
- When a user draws on a cell, the coords and user name are sent to the server and the cell changes to USED state, keeping track of the player
- If a user lets go of drawing, a transmission to the server is sent, if the cell is over 50% covered its state is changed to CLOSED, else it is OPEN again
- Each action by any user will trigger a retransmission of the current state of the game board to all players

The player will first request a colour for their pen.

```json
// Client -> Server Pen Colour Request
{
    "game_session_uuid": "game-session-uuid",   
    "uuid": "player-uuid",
    "command": "pen_colour_request",
}
// Server -> Client Pen Colour Response
{
    "command": "pen_colour_response",
    "status": "success",
    "colour": "red",
}
{
    "status": "error",
    "error": "abcdefg",
}
```

After all players have requested their pen colours, the game server will notify all players of the current players in the game session.

```json
// Server -> Client Current Players Notification
{
    "command": "current_players",
    "players": {
        "uuid-1": {
            "colour": "red",
            "name": "Player 1",
        },
        "uuid-2": {
            "colour": "blue",
            "name": "Player 2",
        },
        "uuid-3": {
            "colour": "green",
            "name": "Player 3",
        }
    }
}

If player goes one minute without sending any pen colour request, they will be considered inactive and removed from the game session. Their connection will be closed. If less than m players in the game session after the removal, the game session will be prematurely ended and all players will be notified. After the game starts, no further inactivate checks will be performed.

```json
// Server -> Client Inactive Player Notification
{
    "command": "inactive_player",
}
// Server -> Client Not Enough Players Notification
{
    "command": "not_enough_players",
}
```

When the player starts holding the pen, they will send a pen down request to the game server. This request will lock the tile for the player if it is not already locked by another player. If the tile is already locked, the server will return an error.

```json
// Client -> Server Pen Down Request
{
    "game_session_uuid": "game-session-uuid",   
    "uuid": "player-uuid",
    "command": "pen_down",
    "index": 0,
}
// Server -> Client Pen Down Response
{
    "status": "success"
}
{
    "status": "error",
    "error": "abcdefg",
}
```

The server will then notify all other players in the game session of the pen down request, if the request was successful.

```json
// Server -> Client Pen Down Broadcast
{
    "command": "pen_down_broadcast",
    "index": 0,
    "colour": "red",
}
```

When the player stops holding the pen, they will send a pen up request to the game server. This will unlock the tile for the player.

```json
// Client -> Server Pen Up Request
{
    "game_session_uuid": "game-session-uuid",   
    "uuid": "player-uuid",
    "command": "pen_up_tile_claimed",
    // "command": "pen_up_tile_not_claimed",
    "index": 0,
}
// Server -> Client Pen Up Response
{
    "status": "success"
}
{
    "status": "error",
    "error": "abcdefg",
}
```

The server will then notify all other players in the game session of the pen up request, if the request was successful.

```json
// Server -> Client Pen Up Broadcast
{
    "command": "pen_up_broadcast",
    "index": 0,
    "colour": "red",
    "status": "pen_up_tile_claimed", // or "pen_up_tile_not_claimed"
}


##### Winning Conditions

```

After each successful tile claimed, the server will check if the player has claimed enough tiles to win the game. floor(num_tiles / num_players) + 1 tiles are required to win the game. If a player has won the game, the server will notify all players in the game session.

```json
// Server -> Client Game Win Notification
{
    "command": "game_win",
    "players": [
        { "uuid": "uuid-1", "name": "Alice", "score": 12 },
        { "uuid": "uuid-2", "name": "Bob", "score": 15 },
        { "uuid": "uuid-3", "name": "You", "score": 10 }
    ]
}
```

If player sends any request after the game has ended, the server will return an error.

```json
// Server -> Client Game Ended Error
{
    "status": "error",
    "error": "Game has already ended"
}
```

### Unknown Command Error

If the game server receives a command that it does not recognize, it will return an error.

```json
// Server -> Client Unknown Command Error
{
    "status": "error",
    "error": "Unknown command"
}
```
---

### SCOREBOARD

After a game ends, the server sends the final results to all players. The client transitions to the SCOREBOARD state, where the final rankings and scores are displayed.

- The client displays a table (scoreboard) with all players, their scores, and their ranking.
- Scores are displayed in the format `player_score/num_of_players^2` (e.g., "15/64")
- Players with the same score share the same rank (e.g., 1, 2, 2, 4).
- The current player's row is highlighted for easy identification.
- The entire scoreboard is visible, not just the top scores.

**Example Table:**

| Rank | Name   | Score |
|------|--------|-------|
| 1    | Bob    | 15/64 |
| 2    | Alice  | 12/64 |
| 3    | You    | 10/64 |

If two or more players have the same score, they share the same rank, and the next rank is skipped accordingly.

#### Transition

- After viewing the scoreboard, the client may automatically or manually return to the QUEUE state to start a new game
- The server resets its state to QUEUE, ready for new matchmaking
