import React, { useState, useMemo } from 'react'

type GameProps = {
  uuid: String,
  ws: WebSocket | null,
  game_session_uuid: String,
  number_of_players: Number,
  player_colour: Array<string>,
  squareStates: Array<string>,
  updateSquares: (squares: Array<string>) => void,
  players: Array<{id: string, name: string, colour: string}>,
  currentPlayerId: string
}

const DenyAndConquerGame: React.FC<GameProps> = ({ uuid, ws, game_session_uuid, number_of_players, player_colour, squareStates, updateSquares, players, currentPlayerId }) => {
  const [mouseDownIndex, setMouseDownIndex] = useState<number | null>(null)
  const [mouseDownTime, setMouseDownTime] = useState<number | null>(null)
  const [heldIndex, setHeldIndex] = useState<number | null>(null)

  // Get the claimed color for a player (the darker color) - using exact same mapping as getColour function in App.tsx
  const getPlayerClaimedColor = (playerColour: string) => {
    if (playerColour === 'blue') return "#0000FF"
    else if (playerColour === 'green') return "#008000"
    else if (playerColour === 'red') return "#EE4B2B"
    else if (playerColour === 'orange') return "#FFA500"
    else if (playerColour === 'purple') return "#800080"
    else if (playerColour === 'pink') return "#FF1493"
    else if (playerColour === 'cyan') return "#00CED1"
    return "#cccccc"
  }

  // Calculate scores for each player based on claimed squares
  const scores = useMemo(() => {
    const scoreMap: {[key: string]: number} = {}
    
    // Initialize scores for all players
    players.forEach(player => {
      scoreMap[player.id] = 0
    })
    
    // Count claimed squares for each player
    squareStates.forEach((squareColor, index) => {
      if (squareColor !== '#ffffff') {
        // Find which player this color belongs to
        const player = players.find(p => {
          const claimedColor = getPlayerClaimedColor(p.colour)
          return squareColor === claimedColor
        })
        if (player) {
          scoreMap[player.id]++
        }
      }
    })
    
    return scoreMap
  }, [squareStates, players])

  // Calculate score needed to win
  const scoreToWin = Math.floor((number_of_players.valueOf() ** 2) / number_of_players.valueOf()) + 1

  const handleMouseDown = (index: number): void => {
    if (squareStates[index] !== '#ffffff') return

    setMouseDownTime(Date.now())
    setMouseDownIndex(index)
    setHeldIndex(index)

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
    setHeldIndex(null)

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
      
      {/* Score Requirement Display */}
      <div style={{ marginBottom: '1rem' }}>
        <h3 style={{ marginBottom: '0.5rem', color: '#333' }}>Score to win: {scoreToWin} cells</h3>
      </div>

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
                filter: heldIndex === index ? 'brightness(80%)' : 'brightness(100%)',
                transition: 'filter 1s linear',
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
