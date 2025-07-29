import React, { useRef, useEffect, useState } from "react"

type PlayerQueueDisplayProps = {
    playerName: string
}

export default function PlayerQueueDisplay({ playerName }: PlayerQueueDisplayProps): React.JSX.Element {
    // TODO ask server for info
    const [playerCount, setPlayerCount] = useState<number>(1)
    const [playerReadyCount, setPlayerReadyCount] = useState<number>(0)
    return (<div id="PlayerQueueDisplay">
        <h2>
            Welcome, {playerName}!
        </h2>
        <h3>
            {playerReadyCount} of {playerCount} players are ready.
        </h3>
    </div>)
}