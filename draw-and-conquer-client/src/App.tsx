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
const HOST: String = process.env.REACT_APP_HOST ? process.env.REACT_APP_HOST : "localhost"
const PORT: String = process.env.REACT_APP_PORT ? process.env.REACT_APP_PORT : "9437"

function App(): React.JSX.Element {
  const { v4: uuidv4 } = require('uuid');
  const [uuid] = useState(() => uuidv4());
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [state, setState] = useState<State>(State.QUEUE)
  const [game_session_uuid, setGame_session_uuid] = useState("")

  const body: () => React.JSX.Element = () => {
    if (state === State.QUEUE) return <Queue uuid={uuid} socket={socket} />

    if (state === State.GAME) return <DenyAndConquerGame  uuid={uuid} game_session_uuid={game_session_uuid}/>

    if (state === State.SCOREBOARD) return <ScoreBoard uuid={uuid} players={players} currentPlayerId={currentPlayerId}/>

    if (state === State.WAIT) return <div>TODO WAIT</div>
    
    else return <div>Something went wrong!</div>
  }

  function setAppState(state: String): void {
    if (state === 'QUEUE')
      setState(State.QUEUE)
    else if (state === 'SCOREBOARD')
      setState(State.SCOREBOARD)
    else if (state === 'WAIT')
      setState(State.WAIT)
  }

  function parseServerCommands(cmd: String): void {
  }

  useEffect(() => {
    if (!socket) {
      const ws = new WebSocket('ws://' + HOST + ':' + PORT);

      ws.onmessage = (event: MessageEvent) => {

        const data = JSON.parse(event.data)

        console.log('server says: ', data)

        if (data.state) setAppState(data.state)

        if (data.command == 'game_start'){ 
          setState(State.GAME)
          setGame_session_uuid(data.game_session_uuid)
        }
      }


      ws.onerror = (error: Event) => {
        console.error('Websocket Error: ', error)
      }

      setSocket(ws);
    }
  }, [socket])

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
