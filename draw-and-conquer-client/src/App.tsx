import React, { useEffect, useState } from 'react';
import logo from './logo.svg';
import './App.css';
import TitleBar from './components/TitleBar';
import PlayerQueueDisplay from './components/PlayerQueueDisplay';
import ReadyButton from './components/ReadyButton';
import DenyAndConquerGame from './components/Game';
enum State {
  QUEUE,
  GAME,
  SCOREBOARD,
  WAIT
}

function App(): React.JSX.Element {
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
      return <div>TODO SCOREBOARD</div>

    else if (state == State.WAIT)
      return <div>TODO WAIT</div>
    
    else
      return <div>Something went wrong!</div>
  }

  useEffect(() => {
    const socket = new WebSocket('ws://205.250.26.138/140')

    socket.onopen = () => {
      socket.send(JSON.stringify({message: 'hello server'}))
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
  })

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
