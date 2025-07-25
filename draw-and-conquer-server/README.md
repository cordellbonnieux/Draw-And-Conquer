# Backend server

## Start up

```shell
python main.py --host 127.0.0.1 --matchmaker-port 9437 --game-server-port 9438 --lobby-size 3 --heartbeat-timeout 30
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
    "uuid": "player-uuid",
    "command": "queue_heartbeat",
    "status": "success",
    "queue_length": 2,
}
{
    "uuid": "player-uuid",
    "command": "queue_heartbeat",
    "status": "error",
    "error": "abcdefg",
}
// Server -> Client Heartbeat Timeout
{
    "uuid": "player-uuid",
    "command": "queue_heartbeat",
    "status": "error",
    "error": "Heartbeat timeout, removed from queue",
}
```

If the queue length is greater than n, queue server will start a game server and notify the players in the queue with a game session UUID. heartbeat will stop.

```json
// Server -> Client Game Start Notification
{
    "uuid": "player-uuid",
    "command": "game_start",
    "status": "success",
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
    "uuid": "player-uuid",
    "command": "remove_from_queue",
    "status": "success",
}
{
    "uuid": "player-uuid",
    "command": "remove_from_queue",
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
    "game_session_uuid": "game-session-uuid",   
    "uuid": "player-uuid",
    "command": "pen_colour_response",
    "status": "success",
    "colour": "red",
}
{
    "game_session_uuid": "game-session-uuid",   
    "uuid": "player-uuid",
    "command": "pen_colour_response",
    "status": "error",
    "error": "abcdefg",
}
```

After all players have requested their pen colours, the game server will notify all players of the current players in the game session.

```json
// Server -> Client Current Players Notification
{
    "game_session_uuid": "game-session-uuid",
    "uuid": "player-uuid",
    "command": "current_players",
    "status": "success",
    "colours": {
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

If player goes one minute without sending any pen colour request, they will be considered inactive and removed from the game session. Their connection will be closed. If less than m players in the game session after the removal, the game session will be prematurely ended and all players will be notified.

```json
// Server -> Client Inactive Player Notification
{
    "game_session_uuid": "game-session-uuid",
    "uuid": "player-uuid",
    "command": "not-enough_players",
    "status": "success",
}
```

The players that experienced the premature end may requeue for a priority queue. The priority queue will be available for a limited time. The client will only need to send a normal enqueue request, the server will recognize the UUID and place the player in the priority queue.

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
    "game_session_uuid": "game-session-uuid",   
    "uuid": "player-uuid",
    "command": "pen_down_response",
    "status": "success",
}
{
    "game_session_uuid": "game-session-uuid",   
    "uuid": "player-uuid",
    "command": "pen_down_response",
    "status": "error",
    "error": "abcdefg",
}
```

The server will then notify all other players in the game session of the pen down request, if the request was successful.

```json
// Server -> Client Pen Down Broadcast
{
    "game_session_uuid": "game-session-uuid",   
    "uuid": "other-player-uuid",
    "command": "pen_down_broadcast",
    "status": "success",
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
    "game_session_uuid": "game-session-uuid",   
    "uuid": "player-uuid",
    "command": "pen_up_tile_claimed",
    // "command": "pen_up_tile_not_claimed",
    "status": "success",
}
{
    "game_session_uuid": "game-session-uuid",   
    "uuid": "player-uuid",
    "command": "pen_up_tile_claimed",
    // "command": "pen_up_tile_not_claimed",
    "status": "error",
    "error": "abcdefg",
}
```

The server will then notify all other players in the game session of the pen up request, if the request was successful.

```json
// Server -> Client Pen Up Broadcast
{
    "game_session_uuid": "game-session-uuid",
    "uuid": "other-player-uuid",
    "command": "pen_up_broadcast",
    "status": "success",
    "index": 0,
    "colour": "red",
}
```
