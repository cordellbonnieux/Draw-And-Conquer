# Draw And Conquer
## CMPT371 Group 2 Final Project

### Description
This is a browser based multiplayer game, where players compete to fill in squares in a grid by clicking down on them until they change color. Each square can only be clicked on by one player at a time. A player wins when they have colored more squares than anyone else.

### Application Flow

#### Name Input Flow
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
}
```

Player will then communicate with the game server on port 9438 using the provided game session UUID. Game session UUID make sure the support for multiple game sessions in parallel.

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

### 2. GAME state

#### Description
- Upon transition to this state, create a playerCount by playerCount grid on client.
- The server creates a data structure representing the grid, each cell contains a CellState: OPEN, USED (by player), CLOSED (by player).
- Each client may only start to draw on an OPEN cell.
- When a user draws on a cell, the coords and user name are sent to the server and the cell changes to USED state, keeping track of the player.
- If a user lets go of drawing, a transmission to the server is sent, if the cell is over 50% covered its state is changed to CLOSED, else it is OPEN again.
- Each action by any user will trigger a retransmission of the current state of the game board to all players.

#### Winning Conditions
- **Primary Win Condition**: First player to occupy >= `floor(64/n) + 1` cells wins immediately, where `n` is the number of players
  - 2 players: 33 cells needed to win
  - 3 players: 22 cells needed to win
  - 4 players: 17 cells needed to win
  - 6 players: 12 cells needed to win
  - 8 players: 9 cells needed to win
- **Timeout Win Condition**: If no player reaches the required threshold within the time limit, the player with the highest number of cells occupied wins
- **Game Duration**: Recommended 4-5 minutes per game session
- When a player wins, the server transmits the results to each player, this will trigger the client to change to the SCOREBOARD state and the server will return to QUEUE state.
- If another user connects to a client while the server is in the GAME state, the client will change to a WAITING state and will periodically ping the server for its state, if QUEUE is returned the client will also change to QUEUE state.

#### Game State Data Structure
- Cell States: `OPEN`, `USED`, `CLOSED`
- Each cell contains:
  - `state`: CellState
  - `owner`: Player UUID (if USED or CLOSED)

#### Client/Server Commands

- **UPDATE_BOARD**
  - Request the current game board state and any updates from other players.
  - **Server Response Example:**
    ```json
    {
      "index": 10,
      "status": "complete", // or "in-progress", "failed"
      "color": "blue"
    }
    ```

- **PENDOWN**
  - Notify the server that the player pressed down on a square to attempt scribbling it.
  - **Client Command Example:**
    ```json
    {
      "uuid": "player-uuid",
      "index": number,  // the index of the square (0–63)
      "status": "in-progress"
    }
    ```

- **PENUP**
  - Notify the server that the player released the mouse (pen up) and finished the attempt.
  - **Client Command Example:**
    ```json
    {
      "uuid": "player-uuid",
      "index": number,  // the index of the square
      "status": "complete" // or "failed"
    }
    ```
  - "complete" -> Player held pen down for over 1 second; server can mark square as taken.
  - "failed" -> Player released early; server may ignore or notify others.

---

### 3. SCOREBOARD state

After a game ends, the server sends the final results to all players. The client transitions to the SCOREBOARD state, where the final rankings and scores are displayed.

#### Scoring System

- **Point Calculation**: Each cell occupied by a player earns them 1 point
- **Total Possible Score**: n^2 points
- **Score Display**: Scores are shown as `player_score/(n^2)` (e.g., "15/64" for an 8 player game)

#### Scoreboard Data Structure

The server sends a list of all players and their scores. Each player object contains:
- `id`: Unique identifier for the player (UUID)
- `name`: Player's display name
- `score`: Final score for the game session (number of cells occupied)

**Example Server Response:**
```json
{
  "command": "scoreboard",
  "status": "success",
  "players": [
    { "id": "uuid-1", "name": "Alice", "score": 12 },
    { "id": "uuid-2", "name": "Bob", "score": 15 },
    { "id": "uuid-3", "name": "You", "score": 10 }
  ],
  "currentPlayerId": "uuid-3"
}
```

#### Client Rendering

- The client displays a table (scoreboard) with all players, their scores, and their ranking.
- Scores are displayed in the format `player_score/64` (e.g., "15/64")
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

- After viewing the scoreboard, the client may automatically or manually return to the QUEUE state to start a new game.
- The server resets its state to QUEUE, ready for new matchmaking.
