import React, { useEffect, useState } from 'react';
import ScoreBoard from './ScoreBoard';

type GameProps = {
  uuid: string;
  game_session_uuid: string;
};

//////////////////////////// examples //////////////////////////////////////////
const players = [
  { id: '1', name: 'Alice', score: 12 },
  { id: '2', name: 'Bob', score: 15 },
  { id: '3', name: 'You', score: 10 },
  { id: '4', name: 'Jane', score: 10 },
  { id: '200', name: 'Jim', score: 8 },
  { id: '5', name: 'Tim', score: 9 },
];
const currentPlayerId = '3';
////////////////////////////////////////////////////////////////////////////////

const DenyAndConquerGame: React.FC<GameProps> = ({ uuid, game_session_uuid }) => {
  const GRID_SIZE = 8;
  const TOTAL_SQUARES = GRID_SIZE * GRID_SIZE;
  const [color, setColor] = useState(["#FAB972", "#FFA500"]);
  const [mouseDownIndex, setMouseDownIndex] = useState<number | null>(null);
  const [mouseDownTime, setMouseDownTime] = useState<number | null>(null);
  const [gameSocket, setGameSocket] = useState<WebSocket | null>(null);
  const [gameEnd, setGameEnd] = useState(false);

  // Intialize the state of each square on the board
  const [squareStates, setSquareStates] = useState<string[]>(
    Array(TOTAL_SQUARES).fill("#ffffff")
  );

  const handleMouseDown = (index: number): void => {
    if (squareStates[index] !== "#ffffff") return;

    setMouseDownTime(Date.now());
    setMouseDownIndex(index); 

    const newStates = [...squareStates];
    newStates[index] = color[0];
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

  const handleMouseUp = () => {
    if (mouseDownIndex === null) return;
    const duration = Date.now() - (mouseDownTime ?? 0);
    const index = mouseDownIndex;
    const newStates = [...squareStates];
    setMouseDownTime(null);
    setMouseDownIndex(null)

    // If held down more than 1 second, mark as complete, else fail
    if (duration > 1000){
      newStates[index] = color[1];
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
      newStates[index] = "#ffffff";
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
  const getColor = (colour:string) => {
    if (colour == 'blue') return ["#00FFFF", "#0000FF"];
    else if (colour == 'green') return["#CCFFCC", "#008000"];
    else if (colour == 'red') return["#F88379", "#EE4B2B"];
    else if (colour == 'orange') return["#FAB972", "#FFA500"];
    else if (colour == 'purple') return["#D8BFD8", "#800080"];
    else if (colour == 'pink') return["#FFB6C1", "#FF1493"];
    else if (colour == 'cyan') return["#E0FFFF", "#00CED1"];
    return ["#ffffff", "#cccccc"];
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
          setColor(getColor(data.colour))
        } 
        else if (data.command == "pen_up_broadcast"){
          let index = data.index;
          let color = getColor(data.colour);
          // Other players' claim failed
          if (!data.status){
            setSquareStates(prev => {
              const updated = [...prev];  
              updated[index] = "#ffffff";          
              return updated;
            })}
          // Other players' claim success 
          else {
            setSquareStates(prev => {
              const updated = [...prev];  
              updated[index] = color[1];          
              return updated;
            })
          }
        }
        else if (data.command == "pen_down_broadcast"){
          let index = data.index;
          let color = getColor(data.colour);
          setSquareStates(prev => {
            const updated = [...prev];  
            updated[index] = color[0];          
            return updated;
          });
        }
        else if (data.command == "game_win"){
          setGameEnd(true)
        }
      } catch {
        console.log('Non-JSON message:', event.data);
      }
    };
  }, []);  

  return (
    <div>
      <h2>Deny and Conquer - Game Board</h2>

      {!gameEnd &&
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
          {squareStates.map((_, index) => (
            <div
              key={index}
              style={{
                border: '1px solid black',
                height: '40px',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                cursor: 'pointer',
                backgroundColor: squareStates[index],
              }}
              onMouseDown={() => handleMouseDown(index)}
              onMouseUp={() => handleMouseUp()}
            >
            </div>
          ))}
        </div>
      </div>}

      {gameEnd &&
      <div>
      <h2>Scoreboard</h2>
        <ScoreBoard uuid={uuid} players={players} currentPlayerId={currentPlayerId}/>
      </div>}

    </div>
  );
};

export default DenyAndConquerGame;
