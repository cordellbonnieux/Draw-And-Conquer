import React, { useEffect, useState } from 'react';
import { sendCommand } from '../wsClient';

enum SquareState { 
  WHITE,              
  IN_PROCESS ,        
  COMPLETE,              
  OPPONENT_IN_PROCESS,
  OPPONENT_TAKEN      
};

const DenyAndConquerGame: React.FC = () => {
  const GRID_SIZE = 8;
  const TOTAL_SQUARES = GRID_SIZE * GRID_SIZE;

  const [color, setColor] = useState(["#FAB972", "#FFA500"]);
  const [opponentColor, setOpponentColor] = useState(["#FFA500", "#FAB972"]);
  const [mouseDownTime, setMouseDownTime] = useState<number | null>(null);

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

    sendCommand("PENDOWN", { index, status: "in-progress" });
  };

  const handleMouseUp = (index: number) => {
    const duration = Date.now() - (mouseDownTime ?? 0);
    setMouseDownTime(null);

    let newStatus;
    const newStates = [...squareStates];
    // If held down more than 1 second, mark as complete, else fail
    if (duration > 1000){
      newStatus = "complete";
      newStates[index] = SquareState.COMPLETE;
    } else {
      newStatus = "failed";
      newStates[index] = SquareState.WHITE;
    }
    //Update Board
    setSquareStates(newStates);

    sendCommand("PENUP", {index, status: newStatus});
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

  // Assign color for the current player
  useEffect(() => {
    const socket = new WebSocket('ws://205.250.26.138/140');
    sendCommand("ASSIGN_COLOR", "");

    socket.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        console.log('server says: ', data);
        if (data.color == 'blue')
          setColor(["#0000FF", "#00FFFF"]);
        else if (data.color == 'green')
          setColor(["#008000", "#CCFFCC"]);
        else if (data.color == 'red')
          setColor(["#EE4B2B", "#F88379"]);
        else if (data.color == 'orange')
          setColor(["#FFA500", "#FAB972"]);
      } catch {
        console.log('Received non-JSON message:', event.data);
      }
    }
  }, []);

  // Listen for other opponents activities and board updates
  useEffect(() => {
    const socket = new WebSocket('ws://205.250.26.138/140');
    sendCommand("UPDATE_BOARD", "");

    socket.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        console.log('server says: ', data.color, data.index);
        if (data.color == 'blue')
          setOpponentColor(["#0000FF", "#00FFFF"]);
        else if (data.color == 'green')
          setOpponentColor(["#008000", "#CCFFCC"]);
        else if (data.color == 'red')
          setOpponentColor(["#EE4B2B", "#F88379"]);
        else if (data.color == 'orange')
          setOpponentColor(["#FFA500", "#FAB972"]);
      } catch {
        console.log('Received non-JSON message:', event.data);
      }
    }
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
