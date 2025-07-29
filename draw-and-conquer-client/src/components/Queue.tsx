import React, { useState } from "react"
import NameInput from './NameInput'
import PlayerQueueDisplay from './PlayerQueueDisplay'
import ReadyButton from './ReadyButton'

type QueueProps = {
    uuid: string,
    socket: WebSocket | null
}

export default function Queue(props: QueueProps): React.JSX.Element {
    const [ready, setReady] = useState<boolean>(false)
    const [playerName, setPlayerName] = useState<string>("")
    const [hasEnteredName, setHasEnteredName] = useState<boolean>(false)
    const {uuid, socket} = props

    const handleNameSubmit = (name: string) => {
        setPlayerName(name);
        setHasEnteredName(true)
    }

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

    if (!hasEnteredName) 
        return <NameInput onNameSubmit={handleNameSubmit} isVisible={true} />
    else
        return (<div>
            <PlayerQueueDisplay playerName={playerName} />
            <ReadyButton ready={ready} toggleReady={toggleReady} />
        </div>)
}