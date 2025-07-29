import React, { useEffect, useState } from 'react'
import './App.css'
import TitleBar from './components/TitleBar'
import DenyAndConquerGame from './components/Game'
import ScoreBoard from './components/ScoreBoard'
import Queue from './components/Queue'
enum State {
  QUEUE,
  GAME,
  SCOREBOARD,
  WAIT
}
const MATCH_MAKING_HOST: String = process.env.REACT_APP_MATCH_MAKING_HOST ? process.env.REACT_APP_MATCH_MAKING_HOST : 'localhost'
const MATCH_MAKING_PORT: String = process.env.REACT_APP_MATCH_MAKING_PORT ? process.env.REACT_APP_MATCH_MAKING_PORT : '9437'
const GAME_HOST: String = process.env.REACT_APP_GAME_HOST ? process.env.REACT_APP_GAME_HOST : 'localhost'
const GAME_PORT: String = process.env.REACT_APP_GAME_PORT ? process.env.REACT_APP_GAME_PORT : '9438'

function App(): React.JSX.Element {
  const { v4: uuidv4 } = require('uuid');
  const [uuid] = useState(() => uuidv4());
  const [matchMakingSocket, setMatchMakingSocket] = useState<WebSocket | null>(null)
  const [gameSocket, setGameSocket] = useState<WebSocket | null>(null)
  const [state, setState] = useState<State>(State.QUEUE)
  const [game_session_uuid, setGame_session_uuid] = useState('')
  const [game, setGame] = useState({
    // This whole object could be refactored into a new class / data structure
    'numberOfPlayers': 0,
    'colour': '',
    'players': [] // player data structure would be nice to have too
  })

  const body: () => React.JSX.Element = () => {
    if (state === State.QUEUE) return <Queue uuid={uuid} socket={matchMakingSocket} queueLength={game['numberOfPlayers']} />

    else if (state === State.GAME) return <DenyAndConquerGame uuid={uuid} game_session_uuid={game_session_uuid} />

    else if (state === State.SCOREBOARD) return <ScoreBoard uuid={uuid} players={players} currentPlayerId={currentPlayerId} />

    else if (state === State.WAIT) return <div>TODO WAIT</div>
    
    else return <div>Something went wrong!</div>
  }

  function matchMakingSocketConnection() {
    const ws = new WebSocket('ws://' + MATCH_MAKING_HOST + ':' + MATCH_MAKING_PORT)

    ws.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data)
      switch (data.command) {
        case 'game_start':
          setState(State.GAME)
          setGame_session_uuid(data.game_session_uuid)
          ws.close()
          break
        case 'enqueue':
        default:
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

  function gameSocketConnection() {
    const ws = new WebSocket('ws://' + GAME_HOST + ':' + GAME_PORT)

    ws.onopen = () => {
      ws.send(JSON.stringify({
        'game_session_uuid': game_session_uuid,
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
          setGame({
            ...game,
            'players': [] // TODO here
          })
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

export default App;
