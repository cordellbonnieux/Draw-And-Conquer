import React, { useRef, useEffect, useState } from "react"

export default function PlayerQueueDisplay(): React.JSX.Element {
    // TODO ask server for info
    const [playerCount, setPlayerCount] = useState<number>(1)
    const [playerReadyCount, setPlayerReadyCount] = useState<number>(0)
    return (<div id="PlayerQueueDisplay">
        <h2>
            {playerReadyCount} of {playerCount} players are ready.
        </h2>
    </div>)
}