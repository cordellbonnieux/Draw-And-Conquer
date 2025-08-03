# Backend server

## Start up

```shell
python main.py --host 127.0.0.1 --matchmaker-port 9437 --game-server-port 9438 --lobby-size 3 --heartbeat-timeout 30 --num_tiles 64 --colour-selection-timeout 60
```

To start the server in echo mode for testing, use the following command:

```shell
python main.py --host 127.0.0.1 --echo-port 9436
```

## Matchmaker

Matchmaking server is always standby on port 9437 for players to enqueue. When player enqueues, they must provide a UUID and a name. The name is not used in the matchmaking process, but it is used to identify the player in the game session.

```json
// Client -> Server Enqueue Request
{
    "uuid": "player-uuid",
    "command": "enqueue",
    "name": "player-name"
}
// Server -> Client Enqueue Response
{
    "status": "success",
    "queue_length": 2,
}
{
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
    "status": "success",
    "queue_length": 2,
}
{
    "status": "error",
    "error": "abcdefg",
}
// Server -> Client Heartbeat Timeout
{
    "command": "heartbeat_timeout"
}
```

If the queue length is greater than n, queue server will start a game server and notify the players in the queue with a game session UUID. heartbeat will stop.

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
    "status": "success"
}
{
    "status": "error",
    "error": "abcdefg",
}
```

## Game Server

After player is notified, they will communicate with the game server using the game session UUID and their UUID. If the game server determines the game session or the player dose not belong to the game session, it will return an error.

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
```

After each successful tile claimed, the server will check if the player has claimed enough tiles to win the game. floor(num_tiles / num_players) + 1 tiles are required to win the game. If a player has won the game, the server will notify all players in the game session.

```json
// Server -> Client Game Win Notification
{
    "command": "game_win",
    "scoreboard": [
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
