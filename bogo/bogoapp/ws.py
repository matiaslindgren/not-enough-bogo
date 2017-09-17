import json
import logging
import websockets

logger = logging.getLogger("WebSocketManager")

class WebSocketManager:

    def __init__(self, get_current_state):
        self.spectators = 0
        self.get_current_state = get_current_state

    async def feed(self, request, ws):
        logger.debug("Open feed")
        self.spectators += 1
        try:
            while True:
                data = json.dumps((self.spectators, *self.get_current_state()))
                await ws.send(data)
                await ws.recv()
        except websockets.exceptions.ConnectionClosed:
            self.spectators = max(0, self.spectators-1)
        finally:
            logger.debug("Close feed")
