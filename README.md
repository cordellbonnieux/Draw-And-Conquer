CMPT371 Group2 Final Project - Draw & Conquer

Application Flow (WIP)

- Client States: QUEUE, GAME, WAIT, SCOREBOARD
- Server States: QUEUE, GAME
- Cell States (Server data structure): OPEN, CLOSED, USED

1. QUEUE state (User connects to client)
- client and server start in the QUEUE state
- client notifies server; server responds with playerCount & playerReadyCount
- each time a user connects, or changes their ready status: playerCount & playerReadyCount are retransmitted to the user. 
- if playerCount & playerReadyCount are equal, client & server change to GAME state

- &nbsp;Druring GAME state:
  - &nbsp;1. READY
  - &nbsp;Notify the server that the player is ready.
  - &nbsp;2. UNREADY
  - &nbsp;Notify the server that the player is unready.


2. GAME state
- upon transition to this state, create a playerCount by playerCount grid on client
- the server creates a datastructure representing the grid, each cell contains a CellState: OPEN, USED (by player), CLOSED (by player)
- each client may only start to draw on an OPEN cell
- when a user draws on a cell, the coords and user name are sent to the server and the cell changes to USED state, keeping track of the player
- if a user lets go of drawing, a transmission to the server is sent, if the cell is over 50% covered its state is changed to CLOSED, else it is OPEN again
- each action by any user will trigger a retransmission of the current state of the game board to all players
- when a player wins, the server transmits the results to each player, this will trigger the client to change to the SCOREBOARD state and the server will return to QUEUE state
- if another user connects to a client while the server is in the GAME state, the client will change to a WAITING state and will periodically ping the server for its state, if QUEUE is returned the client will also change to QUEUE state


- &nbsp;Druring GAME state:
  
  - &nbsp;1. ASSIGN_COLOR
  Request a unique color assignment for this player.
  Expected Server Response:
  {
    "color": "red" // or "blue", "green", "orange"
  }
  
  - &nbsp;2. UPDATE_BOARD
  Request the current game board state and any updates from other players.
  Expected Server Response:
  {
    "index": 10,
    "status": "complete", // or “in-progress”, “failed”
    "color": "blue"  // or "blue", "green", "orange"
  }
  
  - &nbsp;3. PENDOWN
  Notify the server that the player pressed down on a square to attempt scribbling it.
  "PENDOWN", {
    index: number,         // the index of the square (0–63)
    status: "in-progress"  }
  
  - &nbsp;5. PENUP
  Notify the server that the player released the mouse (pen up) and finished the attempt.
  "PENUP", {
    index: number,      // the index of the square
    status: "complete" // or "failed"
  }
  "complete" -> Player held pen down for over 1 second; server can mark square as taken.
  "failed" -> Player released early; server may ignore or notify others.


