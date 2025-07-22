const socket = new WebSocket('ws://205.250.26.138/140')

export function sendCommand(uuid: string, command: string, data: any = {}) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      const message = { uuid, command, ...data };
      socket.send(JSON.stringify(message));
      console.log('Sent command:', message);
    } else {
      console.warn('Socket not ready');
    }
}