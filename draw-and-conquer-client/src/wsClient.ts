const socket = new WebSocket('ws://205.250.26.138/140')

export function sendCommand(type: string, data: any = {}) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      const message = { type, ...data };
      socket.send(JSON.stringify(message));
      console.log('Sent command:', message);
    } else {
      console.warn('Socket not ready');
    }
}