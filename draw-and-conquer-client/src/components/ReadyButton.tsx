import React, { useRef, useEffect, useState } from "react"
import { sendCommand } from '../wsClient';

type ReadyButtonProps = {
    uuid: string;
    socket: WebSocket | null;
    playerName: string;
};

export default function ReadyButton({ uuid, socket, playerName }: ReadyButtonProps): React.JSX.Element {
    // TODO ask server for info
    const [ready, setReady] = useState<boolean>(false)

    function toggleReady() {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            console.warn("WebSocket not ready");
            return;
        }

        if (!ready) {
            socket.send(JSON.stringify({
                uuid: uuid,
                command: "enqueue",
                name: playerName
            }));
            setReady(true);
        } else {
            socket.send(JSON.stringify({
                uuid: uuid,
                command: "remove_from_queue"
            }));
            setReady(false);
        }
    }

    return (<div id="ReadyButton" style={{display: 'flex', gap: '1rem'}}>
        <p>{ready ? "✅" : "❌"}</p>
        <button onClick={toggleReady}>
            {ready ? "READY" : "NOT READY"}
        </button>
    </div>)
}