import json
import random
import os.path
import logging

import sanic
import websockets


from bogoapp import bogo_manager
from bogoapp import tools
from bogoapp import settings
from bogoapp import db
from bogoapp import html


logger = logging.getLogger("WebSocketManager")


def make_sanic(name):
    app = sanic.Sanic(name)
    app.config["LOGO"] = settings.LOGO
    app.static("main.js", "./main.js")
    return app


def make_bogo_manager():
    min_stop = settings.MINIMUM_SEQUENCE_STOP
    max_stop = settings.MAXIMUM_SEQUENCE_STOP
    sort_limit = getattr(settings, "SORT_LIMIT", 0)
    unsorted_lists = tools.unsorted_lists(min_stop, max_stop, sort_limit)

    speed_resolution = getattr(settings, "SPEED_RESOLUTION", 1)

    random_module = random.Random()
    random_module.seed(settings.RANDOM_SEED)

    dns = settings.ODBC_DNS
    schema = settings.SQL_SCHEMA_PATH
    database = db.Database(dns, schema)
    if not os.path.exists(settings.DATABASE_PATH):
        database.init()

    return bogo_manager.BogoManager(
            unsorted_lists, speed_resolution
            database, random_module)


def make_websocket_app(sanic_app):

    class WebSocketManager:

        def __init__(self):
            self.spectators = 0

        @sanic_app.websocket("/feed")
        async def feed(self, request, ws):
            logger.info("init ws feed")
            self.spectators += 1
            try:
                while True:
                    await ws.send(json.dumps([self.spectators]))
                    await ws.recv()
            except websockets.exceptions.ConnectionClosed:
                self.spectators = max(0, self.spectators-1)

    return WebSocketManager()


def make_jinja_app():
    return html.JinjaWrapper()



