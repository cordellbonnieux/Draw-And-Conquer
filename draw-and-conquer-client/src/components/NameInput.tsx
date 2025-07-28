import React, { useState } from "react";

type NameInputProps = {
    onNameSubmit: (name: string) => void;
    isVisible: boolean;
};

export default function NameInput({ onNameSubmit, isVisible }: NameInputProps): React.JSX.Element {
    const [name, setName] = useState<string>("");

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (name.trim()) {
            onNameSubmit(name.trim());
        }
    };

    if (!isVisible) {
        return <div></div>;
    }

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
            padding: '2rem',
            border: '2px solid #ccc',
            borderRadius: '8px',
            backgroundColor: '#f9f9f9'
        }}>
            <h3>Enter Your Name</h3>
            <form onSubmit={handleSubmit} style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
                alignItems: 'center'
            }}>
                <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter your name..."
                    style={{
                        padding: '0.5rem',
                        fontSize: '1rem',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                        width: '200px'
                    }}
                    autoFocus
                />
                <button 
                    type="submit"
                    disabled={!name.trim()}
                    style={{
                        padding: '0.5rem 1rem',
                        fontSize: '1rem',
                        backgroundColor: name.trim() ? '#007bff' : '#ccc',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: name.trim() ? 'pointer' : 'not-allowed'
                    }}
                >
                    Continue
                </button>
            </form>
        </div>
    );
}