import React, { useEffect, useState, useRef } from 'react'
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
export default function App(): React.JSX.Element {
  const { v4: uuidv4 } = require('uuid');
  const [uuid] = useState(() => uuidv4());
  const matchMakingSocketRef = useRef<WebSocket | null>(null);
  const gameSocketRef = useRef<WebSocket | null>(null);
  const [state, setState] = useState<State>(State.QUEUE)

  /**
   * Contains the current game's state
   * This whole object could be refactored into a new class / data structure
   */
  const [game, setGame] = useState({
    'uuid': '',
    'numberOfPlayers': 0,
    'colour': '',
    'players': {}, // player data structure would be nice to have too, right now it stores exactly as it comes in from the server
    'squares': new Array<string>()
  })

  /**
   * Populated when a player wins a game, scoreboard is updated with this var
   * TODO pop this prop in SscoreBoard component
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
      return <Queue uuid={uuid} socket={matchMakingSocketRef.current} queueLength={game['numberOfPlayers']} />

    else if (state === State.GAME) 
       return <DenyAndConquerGame uuid={uuid} ws={gameSocketRef.current} game_session_uuid={game.uuid} number_of_players={game.numberOfPlayers} 
       player_colour={getColour(game.colour)} squareStates={game.squares} 
       updateSquares={(newSquares) => setGame(prev => ({ ...prev, squares: newSquares }))}/>

    else if (state === State.SCOREBOARD) 
      return <ScoreBoard uuid={uuid} players={players} currentPlayerId={currentPlayerId} /> // winner var goes in here

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
    matchMakingSocketRef.current = ws;

    ws.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data)

      switch (data.command) {
        case 'game_start':
          const arr: string[] = Array(Math.pow(game.numberOfPlayers.valueOf(), 2)).fill('#ffffff')
          setGame({...game, 'uuid': data.game_session_uuid, squares: arr})
          setState(State.GAME) 
          ws.close()
          break
        case 'heartbeat_timeout':
          console.log('heartbeat timed out!')
          break
      }

      switch (data.status) {
        case 'success':
          console.log('heartbeat received')
          setGame({...game, "numberOfPlayers": data.queue_length})
          matchMakerHeartBeat()
          break
        case 'error':
          console.error("Server Error Message: ", data.error)
          break
      }
    }

    ws.onerror = (error: Event) => {
      console.error('Websocket Error: ', error)
    }
  }

  /**
   * Handles game websocket connection with the server
   */
  function gameSocketConnection() {
    const ws = new WebSocket('ws://' + GAME_HOST + ':' + GAME_PORT)
    gameSocketRef.current = ws;

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
          setGame(prev => ({ ...prev, colour: data.colour }))
          break
        case 'current_players':
          setGame(prev => ({ ...prev, players: data.players, numberOfPlayers: Object.keys(data.players).length }))
          break
        case 'pen_up_broadcast':
          setGame(prev => {
            const squares = [...prev.squares];
            squares[data.index] = data.status == "pen_up_tile_claimed" ? getColour(data.colour)[1] : '#ffffff';
            return { ...prev, squares };
          });
          break
        case 'pen_down_broadcast':
          setGame(prev => {
            const squares = [...prev.squares];
            squares[data.index] = getColour(data.colour)[0];
            return { ...prev, squares };
          });
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
  }
  // update number of squares when numberOfPlayers change
  useEffect(() => {
    setGame(prev => ({ ...prev,
      squares:  Array(Math.pow(prev.numberOfPlayers.valueOf(), 2)).fill('#ffffff')
    }));
  }, [game.numberOfPlayers])

  function matchMakerHeartBeat(): void {
    if (state === State.QUEUE) {
      setTimeout(() => {
        console.log('heartbeat sent')
        matchMakingSocketRef.current?.send(JSON.stringify({
          uuid,
          'command': 'queue_heartbeat'
        }))
      }, 10000)
    }
  }

  useEffect(() => {
    if (state === State.QUEUE && !matchMakingSocketRef.current) matchMakingSocketConnection()
    if (state === State.GAME && !gameSocketRef.current) gameSocketConnection()
  }, [state, matchMakingSocketRef.current])

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