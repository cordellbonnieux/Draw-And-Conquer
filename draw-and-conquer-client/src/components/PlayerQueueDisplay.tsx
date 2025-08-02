import React, { useRef, useEffect, useState } from "react"

type PlayerQueueDisplayProps = {
    playerName: string,
    queueLength: Number,
    ready: boolean
}

export default function PlayerQueueDisplay({ playerName, queueLength, ready }: PlayerQueueDisplayProps): React.JSX.Element {
    const [searchingText, setSearchingText] = useState('Searching for other players')

    useEffect(() => {
        setTimeout(() => {
            if (searchingText.includes('...'))
                setSearchingText('Searching for other players   ')
            else if(searchingText.includes('..'))
                setSearchingText('Searching for other players...')
            else if (searchingText.includes('.'))
                setSearchingText('Searching for other players.. ')
            else
                setSearchingText('Searching for other players.  ')
        }, 500)
    })

    return (<div id="PlayerQueueDisplay" style={{'width': '450px', 'height': 'auto'}}>
        <h2 style={{'width': '450px', 'position': 'fixed', 'textAlign': 'center'}}>
            Welcome, {ready ? searchingText : playerName}
        </h2>
        <div style={{'display': 'block', 'height': '32px'}}/>
        <h3 style={{'marginTop': '32px'}}>
            {queueLength ? queueLength.toString() + ' players are ready to play' : 'Click the button to queue for a game'} 
        </h3>
    </div>)
}