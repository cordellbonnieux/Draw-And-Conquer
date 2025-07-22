import React, { useRef, useEffect, useState } from "react"
import { sendCommand } from '../wsClient';

export default function ReadyButton(): React.JSX.Element {
    // TODO ask server for info
    const { v4: uuidv4 } = require('uuid');
    const [ready, setReady] = useState<boolean>(false)
    const [uuid] = useState(() => uuidv4());

    function toggleReady() {
        // TODO tell server when ready is toggled
        
        if (!ready){
            sendCommand(uuid, "enqueue", "")
            setReady(true)
        } else {
            sendCommand(uuid, "dequeue", "")
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