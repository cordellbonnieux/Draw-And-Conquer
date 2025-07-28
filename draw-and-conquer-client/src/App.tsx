import React, { useEffect, useState } from 'react';
import logo from './logo.svg';
import './App.css';
import TitleBar from './components/TitleBar';
import PlayerQueueDisplay from './components/PlayerQueueDisplay';
import ReadyButton from './components/ReadyButton';
import DenyAndConquerGame from './components/Game';
import ScoreBoard from './components/ScoreBoard';
enum State {
  QUEUE,
  GAME,
  SCOREBOARD,
  WAIT
}

function App(): React.JSX.Element {
  const { v4: uuidv4 } = require('uuid');
  const [uuid] = useState(() => uuidv4());
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [state, setState] = useState<State>(State.QUEUE)
  const [game_session_uuid, setGame_session_uuid] = useState("")

  const body: () => React.JSX.Element = () => {
    if (state == State.QUEUE)
      return <div>
        <PlayerQueueDisplay></PlayerQueueDisplay>
        <ReadyButton uuid={uuid} socket={socket}></ReadyButton>
      </div>

    else if (state == State.GAME)
      return <div>TODO GAME
        <DenyAndConquerGame  uuid={uuid} game_session_uuid={game_session_uuid}/>
      </div>

    else if (state == State.SCOREBOARD)
      return (<div> 
        <h2>Scoreboard</h2>
        <ScoreBoard uuid={uuid} players={players} currentPlayerId={currentPlayerId}/>
      </div>) 

    else if (state == State.WAIT)
      return <div>TODO WAIT</div>
    
    else
      return <div>Something went wrong!</div>
  }

  useEffect(() => {
    if (!socket) {
      const ws = new WebSocket('ws://localhost:9437');

      ws.onopen = () => {
        ws.send(JSON.stringify({"message": "hello server"}))
        console.log('sent the server a message')
      }

      ws.onmessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data)
        console.log('server says: ', data)
        if (data.state == 'QUEUE')
          setState(State.QUEUE)
        else if (data.command == 'game_start'){ 
          setState(State.GAME)
          setGame_session_uuid(data.game_session_uuid)
        }
        else if (data.state == 'SCOREBOARD')
          setState(State.SCOREBOARD)
        else if (data.state == 'WAIT')
          setState(State.WAIT)
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
