import React, { useEffect, useState } from 'react';

enum SquareState { 
  WHITE,              
  IN_PROCESS ,        
  COMPLETE,              
  OPPONENT_IN_PROCESS,
  OPPONENT_TAKEN      
};

type GameProps = {
  uuid: string;
  game_session_uuid: string;
};

const DenyAndConquerGame: React.FC<GameProps> = ({ uuid, game_session_uuid }) => {
  const GRID_SIZE = 8;
  const TOTAL_SQUARES = GRID_SIZE * GRID_SIZE;
  const [color, setColor] = useState(["#FAB972", "#FFA500"]);
  const [opponentColor, setOpponentColor] = useState(["#FFA500", "#FAB972"]);
  const [mouseDownTime, setMouseDownTime] = useState<number | null>(null);
  const [gameSocket, setGameSocket] = useState<WebSocket | null>(null);

  // Intialize the state of each square on the board
  const [squareStates, setSquareStates] = useState<SquareState[]>(
    Array(TOTAL_SQUARES).fill(SquareState.WHITE)
  );

  const handleMouseDown = (index: number): void => {
    if (squareStates[index] !== SquareState.WHITE) return;

    setMouseDownTime(Date.now());

    const newStates = [...squareStates];
    newStates[index] = SquareState.IN_PROCESS;
    //Update Board
    setSquareStates(newStates);

    if (gameSocket?.readyState === WebSocket.OPEN) {
      gameSocket.send(JSON.stringify({
        uuid,
        command: "pen_down",
        index,
        game_session_uuid,
      }));
    } else {
      console.warn("Socket not ready. Current state:", gameSocket?.readyState);
    }    
  };

  const handleMouseUp = (index: number) => {
    const duration = Date.now() - (mouseDownTime ?? 0);
    setMouseDownTime(null);

    let newStatus;
    const newStates = [...squareStates];
    // If held down more than 1 second, mark as complete, else fail
    if (duration > 1000){
      newStates[index] = SquareState.COMPLETE;
      if (gameSocket?.readyState === WebSocket.OPEN) {
        gameSocket.send(JSON.stringify({
          uuid,
          command: "pen_up_tile_claimed",
          index,
          game_session_uuid,
        }));
      } else {
        console.warn("Socket not ready. Current state:", gameSocket?.readyState);
      } 
    } else {
      newStates[index] = SquareState.WHITE;
      if (gameSocket?.readyState === WebSocket.OPEN) {
        gameSocket.send(JSON.stringify({
          uuid,
          command: "pen_up_tile_not_claimed",
          index,
          game_session_uuid,
        }));
      } else {
        console.warn("Socket not ready. Current state:", gameSocket?.readyState);
      } 
    }
    //Update Board
    setSquareStates(newStates);
  };

  // Get the background color of a square 
  const getBackgroundColor = (state: SquareState): string => {
    switch (state) {
      case SquareState.WHITE:
        return '#ffffff';
      case SquareState.IN_PROCESS:
        return color[0]; 
      case SquareState.COMPLETE:
        return color[1]; 
      case SquareState.OPPONENT_IN_PROCESS:
        return opponentColor[0];  
      case SquareState.OPPONENT_TAKEN:
        return opponentColor[1];  
    }
  };

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:9438");
    setGameSocket(socket);

    // Assign color for the current player
    socket.onopen = () => {
      socket.send(JSON.stringify({
        uuid: uuid,
        command: "pen_colour_request",
        game_session_uuid,
      }));
    };
  
    socket.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        console.log('server says: ', data);

        if (data.command == "pen_colour_response"){
          if (data.colour == 'blue') setColor(["#00FFFF", "#0000FF"]);
          else if (data.colour == 'green') setColor(["#CCFFCC", "#008000"]);
          else if (data.colour == 'red') setColor(["#F88379", "#EE4B2B"]);
          else if (data.colour == 'orange') setColor(["#FAB972", "#FFA500"]);
        }
      } catch {
        console.log('Non-JSON message:', event.data);
      }
    };
  }, []);  

  return (
    <div>
      <h2>Deny and Conquer - Game Board</h2>

      <div>
        {/* Draw Game Board */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${GRID_SIZE}, 1fr)`,
            gap: '4px',
            width: '400px',
            margin: 'auto',
          }}
        >
          {squareStates.map((state, index) => (
            <div
              key={index}
              style={{
                border: '1px solid black',
                height: '40px',
                backgroundColor: getBackgroundColor(state),
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                cursor: 'pointer',
              }}
              onMouseDown={() => handleMouseDown(index)}
              onMouseUp={() => handleMouseUp(index)}
            >
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DenyAndConquerGame;
