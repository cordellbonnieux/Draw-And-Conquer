import json
import threading
import time
import argparse
import asyncio
import websockets


from server import TCPServer, UDPServer


def request_handler(text: str) -> str:
    print(text)
    try:
        message = json.loads(text)
    except json.JSONDecodeError:
        message = {"error": "Invalid JSON format"}

    return json.dumps(message)


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="Host to bind",
    )
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Port number",
    )
    return parser.parse_args()

'''
def main():
    args = parse_args()
    host = args.host
    port = args.port

    tcp = TCPServer(host, port, request_handler)
    tcp_thread = threading.Thread(target=tcp.start, daemon=True)
    tcp_thread.start()

    udp = UDPServer(host, port, request_handler)
    udp_thread = threading.Thread(target=udp.start, daemon=True)
    udp_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
'''
async def new_websocket(websocket):
    async for message in websocket:
        await websocket.send(message)

async def main():
    args = parse_args()
    host = args.host
    port = args.port
    async with websockets.serve(new_websocket, host, port) as server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())

