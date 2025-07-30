import React, { useEffect, useState } from 'react'
import './App.css'
import TitleBar from './components/TitleBar'
import DenyAndConquerGame from './components/Game'
import ScoreBoard from './components/ScoreBoard'
import Queue from './components/Queue'

// App UI state
enum State {QUEUE, GAME, SCOREBOARD, WAIT}

// Environment variables - dictates servers & ports
const MATCH_MAKING_HOST: String = process.env.REACT_APP_MATCH_MAKING_HOST ? process.env.REACT_APP_MATCH_MAKING_HOST : 'localhost'
const MATCH_MAKING_PORT: String = process.env.REACT_APP_MATCH_MAKING_PORT ? process.env.REACT_APP_MATCH_MAKING_PORT : '9437'
const GAME_HOST: String = process.env.REACT_APP_GAME_HOST ? process.env.REACT_APP_GAME_HOST : 'localhost'
const GAME_PORT: String = process.env.REACT_APP_GAME_PORT ? process.env.REACT_APP_GAME_PORT : '9438'

/**
 * Application 
 * Top level component, handles all server responses and cascades data down to children;
 * Application state is also controlled from here
 */
function App(): React.JSX.Element {
  const { v4: uuidv4 } = require('uuid');
  const [uuid] = useState(() => uuidv4());
  const [matchMakingSocket, setMatchMakingSocket] = useState<WebSocket | null>(null)
  const [gameSocket, setGameSocket] = useState<WebSocket | null>(null)
  const [state, setState] = useState<State>(State.QUEUE)

  /**
   * Contains the current game's state
   * This whole object could be refactored into a new class / data structure
   */
  const [game, setGame] = useState({
    'uuid': '',
    'numberOfPlayers': 0,
    'colour': '',
    'players': {}, // player data structure would be nice to have too
    'squares': new Array<string>()
  })

  /**
   * Populated when a player wins a game, scoreboard is updated with this var
   */
  const [winner, setWinner] = useState({
    'uuid': '',
    'name': '',
    'colour': ''
  })

  /**
   * Determines the App's current view/UI
   */
  const body: () => React.JSX.Element = () => {
    if (state === State.QUEUE) 
      return <Queue uuid={uuid} socket={matchMakingSocket} queueLength={game['numberOfPlayers']} />

    else if (state === State.GAME) 
       return <DenyAndConquerGame uuid={uuid} ws={gameSocket} game_session_uuid={game.uuid} number_of_players={game.numberOfPlayers} player_colour={getColour(game.colour)} player_dic={game.players} squares={game.squares} />

    else if (state === State.SCOREBOARD) 
      return <ScoreBoard uuid={uuid} players={players} currentPlayerId={currentPlayerId} />

    else if (state === State.WAIT) 
      return <div>TODO WAIT</div>
    
    else 
      return <div>Something went wrong!</div>
  }

  /**
   * Handles matchmaking websocket connection with the server
   */
  function matchMakingSocketConnection() {
    const ws = new WebSocket('ws://' + MATCH_MAKING_HOST + ':' + MATCH_MAKING_PORT)

    ws.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data)

      switch (data.command) {
        case 'game_start':
          const arr: string[] = Array(Math.pow(game.numberOfPlayers.valueOf(), 2)).fill('#ffffff')
          setGame({...game, 'uuid': data.game_session_uuid, squares: arr})
          setState(State.GAME) 
          ws.close()
          break
      }

      switch (data.status) {
        case 'success':
          setGame({...game, "numberOfPlayers": data.queue_length})
          break
        case 'error':
          console.error("Server Error Message: ", data.error)
          break
      }
    }

    ws.onerror = (error: Event) => {
      console.error('Websocket Error: ', error)
    }

    setMatchMakingSocket(ws);
  }

  /**
   * Handles game websocket connection with the server
   */
  function gameSocketConnection() {
    const ws = new WebSocket('ws://' + GAME_HOST + ':' + GAME_PORT)

    ws.onopen = () => {
      ws.send(JSON.stringify({
        'game_session_uuid': game.uuid,
        'uuid': uuid,
        'command': 'pen_colour_request'
      }))
    }

    ws.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data)

      switch (data.command) {
        case 'inactive_player':
          setState(State.QUEUE)
          ws.close()
          break
        case 'not_enough_players':
          setState(State.QUEUE)
          ws.close()
          break
        case 'pen_colour_response':
          setGame({...game, 'colour': data.colour})
          break
        case 'current_players':
          setGame({...game, 'players': data.players})
          break
        case 'pen_up_broadcast':
          let a_squares: string[] = game.squares
          if (!data.status)
            a_squares[data.index] = '#ffffff'
          else
            a_squares[data.index] = getColour(data.colour)[1]
          setGame({...game, squares: a_squares})
          break
        case 'pen_down_broadcast':
          let b_squares: string[] = game.squares
          b_squares[data.index] = getColour(data.colour)[0]
          setGame({...game, squares: b_squares})
          break
        case 'game_win':
          setWinner({
            'colour': data.winnder_colour,
            'uuid': data.winnder_uuid,
            'name': data.winnder_name
          })
          setState(State.SCOREBOARD)
          ws.close()
          break
      }
    }

    ws.onerror = (error: Event) => {
      console.error('Websocket Error: ', error)
    }

    setGameSocket(ws)
  }

  useEffect(() => {
    if (state === State.QUEUE && !matchMakingSocket) matchMakingSocketConnection()
    if (state === State.GAME && !gameSocket) gameSocketConnection()
  }, [matchMakingSocket])

  const players = [
    { id: '1', name: 'Alice', score: 12 },
    { id: '2', name: 'Bob', score: 15 },
    { id: '3', name: 'You', score: 10 },
    { id: '4', name: 'Jane', score: 10 },
    { id: '200', name: 'Jim', score: 8 },
    { id: '5', name: 'Tim', score: 9 },
  ];
  const currentPlayerId = '3';

  return (
    <div className="App" style={
      {
        display: 'flex', 
        gap: '1rem', 
        justifyContent: "center", 
        alignItems: "center",
        flexDirection: "column"
      }
    }>
      <TitleBar></TitleBar>
      {body()}
    </div>
  );
}

// Get the background color of a square 
const getColour = (colour: String) => {
  if (colour == 'blue') return ["#00FFFF", "#0000FF"]
  else if (colour == 'green') return ["#CCFFCC", "#008000"]
  else if (colour == 'red') return ["#F88379", "#EE4B2B"]
  else if (colour == 'orange') return ["#FAB972", "#FFA500"]
  else if (colour == 'purple') return ["#D8BFD8", "#800080"]
  else if (colour == 'pink') return ["#FFB6C1", "#FF1493"]
  else if (colour == 'cyan') return ["#E0FFFF", "#00CED1"]
  return ["#ffffff", "#cccccc"]
}

export default App;
