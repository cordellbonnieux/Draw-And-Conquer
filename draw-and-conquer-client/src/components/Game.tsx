import React, { useState } from 'react'

type GameProps = {
  uuid: String,
  ws: WebSocket | null,
  game_session_uuid: String,
  number_of_players: Number,
  player_colour: Array<string>,
  squareStates: Array<string>,
  updateSquares: (squares: Array<string>) => void
}

const DenyAndConquerGame: React.FC<GameProps> = ({ uuid, ws, game_session_uuid, number_of_players, player_colour, squareStates, updateSquares }) => {
  const [mouseDownIndex, setMouseDownIndex] = useState<number | null>(null)
  const [mouseDownTime, setMouseDownTime] = useState<number | null>(null)

  const handleMouseDown = (index: number): void => {
    if (squareStates[index] !== '#ffffff') return

    setMouseDownTime(Date.now())
    setMouseDownIndex(index)

    const newStates = [...squareStates]
    newStates[index] = player_colour[0]

    //Update Board
    updateSquares(newStates);

    ws?.send(JSON.stringify({
      uuid,
      command: 'pen_down',
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
    updateSquares(newStates)
  }

  return (
    <div>
      <h2>Deny and Conquer - Game Board</h2>
      {<div>
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
            />
          ))}
        </div>
      </div>}
    </div>
  )
}

export default DenyAndConquerGame
