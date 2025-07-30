import React, { useEffect, useState } from 'react'
import ScoreBoard from './ScoreBoard'

type GameProps = {
  uuid: String,
  ws: WebSocket | null,
  game_session_uuid: String,
  number_of_players: Number,
  player_colour: Array<string>,
  player_dic: Object,
  squares: Array<string>
}



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

const DenyAndConquerGame: React.FC<GameProps> = ({ uuid, ws, game_session_uuid, number_of_players, player_colour, player_dic, squares }) => {
  const [mouseDownIndex, setMouseDownIndex] = useState<number | null>(null);
  const [mouseDownTime, setMouseDownTime] = useState<number | null>(null);
  const [gameEnd, setGameEnd] = useState(false);

  // Intialize the state of each square on the board
  const [squareStates, setSquareStates] = useState<string[]>(squares)

  const handleMouseDown = (index: number): void => {
    if (squareStates[index] !== '#ffffff') return

    setMouseDownTime(Date.now())
    setMouseDownIndex(index)

    const newStates = [...squareStates]
    newStates[index] = player_colour[0]

    //Update Board
    setSquareStates(newStates);

    ws?.send(JSON.stringify({
      uuid,
      command: 'pend_down',
      index,
      game_session_uuid
    }))
  }

  const handleMouseUp = () => {
    if (mouseDownIndex === null) return
    const duration = Date.now() - (mouseDownTime ?? 0)
    const index = mouseDownIndex
    const newStates = [...squareStates]
    setMouseDownTime(null)
    setMouseDownIndex(null)

    // If held down more than 1 second, mark as complete, else fail
    if (duration > 1000) {
      newStates[index] = player_colour[1]
      ws?.send(JSON.stringify({
        uuid,
        command: 'pen_up_tile_claimed',
        index,
        game_session_uuid,
      }))

    } else {
      newStates[index] = '#ffffff'
      ws?.send(JSON.stringify({
        uuid,
        command: 'pen_up_tile_not_claimed',
        index,
        game_session_uuid,
      }))
    }
    //Update Board
    setSquareStates(newStates);
  }

  return (
    <div>
      <h2>Deny and Conquer - Game Board</h2>

      {!gameEnd &&
      <div>
        {/* Draw Game Board */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${number_of_players.valueOf()}, 1fr)`,
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
        <ScoreBoard uuid={uuid} players={player_dic} currentPlayerId={currentPlayerId}/>
      </div>}

    </div>
  );
};

export default DenyAndConquerGame;
