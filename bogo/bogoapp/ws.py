import json
import logging
import websockets

logger = logging.getLogger("WebSocketManager")

class WebSocketManager:

    def __init__(self):
        self.spectators = 0

    async def feed(self, request, ws):
        logger.debug("Open feed")
        self.spectators += 1
        try:
            while True:
                await ws.send(json.dumps([self.spectators]))
                await ws.recv()
        except websockets.exceptions.ConnectionClosed:
            self.spectators = max(0, self.spectators-1)
            raise
        finally:
            logger.debug("Close feed")
