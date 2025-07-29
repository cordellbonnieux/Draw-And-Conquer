import React from "react"

type ReadyButtonProps = {
    ready: boolean,
    toggleReady: Function
}

export default function ReadyButton({ready, toggleReady}: ReadyButtonProps): React.JSX.Element {
    return (<div id="ReadyButton" style={{display: 'flex', gap: '1rem'}}>
        <p>{ready ? "✅" : "❌"}</p>
        <button onClick={() => toggleReady()}>
            {ready ? "READY" : "NOT READY"}
        </button>
    </div>)
}