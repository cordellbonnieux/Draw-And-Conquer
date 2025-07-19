import React, { useRef, useEffect, useState } from "react"
import { sendCommand } from '../wsClient';

export default function ReadyButton(): React.JSX.Element {
    // TODO ask server for info
    const [ready, setReady] = useState<boolean>(false)

    function toggleReady() {
        // TODO tell server when ready is toggled
        
        if (!ready){
            sendCommand("READY", "")
            setReady(true)
        } else {
            sendCommand("UNREADY", "")
            setReady(false)
        }
    }

    return (<div id="ReadyButton" style={{display: 'flex', gap: '1rem'}}>
        <p>{ready ? "✅" : "❌"}</p>
        <button onClick={toggleReady}>
            {ready ? "READY" : "NOT READY"}
        </button>
    </div>)
}