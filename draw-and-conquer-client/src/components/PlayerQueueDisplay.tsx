import React, { useRef, useEffect, useState } from "react"

type PlayerQueueDisplayProps = {
    playerName: string,
    queueLength: Number
}

export default function PlayerQueueDisplay({ playerName, queueLength }: PlayerQueueDisplayProps): React.JSX.Element {
    return (<div id="PlayerQueueDisplay">
        <h2>
            Welcome, {playerName}!
        </h2>
        <h3>
            {queueLength ? queueLength.toString() + 'players are ready to play' : 'Click the button to queue for a game'} 
        </h3>
    </div>)
}