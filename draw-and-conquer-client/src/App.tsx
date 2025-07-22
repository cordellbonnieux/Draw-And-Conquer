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
  let socket: WebSocket
  const [state, setState] = useState<State>(State.QUEUE)

  const body: () => React.JSX.Element = () => {
    if (state == State.QUEUE)
      return <div>
        <PlayerQueueDisplay></PlayerQueueDisplay>
        <ReadyButton></ReadyButton>
      </div>

    else if (state == State.GAME)
      return <div>TODO GAME
        <DenyAndConquerGame/>
      </div>

    else if (state == State.SCOREBOARD)
      return (<div> 
        <h2>Scoreboard</h2>
        <ScoreBoard players={players} currentPlayerId={currentPlayerId}/>
      </div>) 

    else if (state == State.WAIT)
      return <div>TODO WAIT</div>
    
    else
      return <div>Something went wrong!</div>
  }

  useEffect(() => {
    /**
     *  This works for connecting to the server via localhost for the sake of development
     * 
     */
    if (!socket) {
      socket = new WebSocket('ws://localhost:9999')

      socket.onopen = () => {
        socket.send(JSON.stringify({"message": "hello server"}))
        console.log('sent the server a message')
      }

      socket.onmessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data)
        console.log('server says: ', data)
        if (data.state == 'QUEUE')
          setState(State.QUEUE)
        else if (data.state == 'GAME')
          setState(State.GAME)
        else if (data.state == 'SCOREBOARD')
          setState(State.SCOREBOARD)
        else if (data.state == 'WAIT')
          setState(State.WAIT)
      }

      socket.onerror = (error: Event) => {
        console.error('Websocket Error: ', error)
      }

      if (socket.readyState === WebSocket.OPEN)
        socket.close()
    }
  })

  const players = [
    { id: '1', name: 'Alice', score: 120 },
    { id: '2', name: 'Bob', score: 150 },
    { id: '3', name: 'You', score: 100 },
    { id: '4', name: 'Jane', score: 100 },
    { id: '200', name: 'Jim', score: 100 },
    { id: '5', name: 'Tim', score: 1100 },
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
