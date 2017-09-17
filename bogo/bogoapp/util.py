import random
import os.path
import logging

import sanic


from bogoapp import bogo_manager
from bogoapp import db
from bogoapp import html
from bogoapp import settings
from bogoapp import tools
from bogoapp import ws

logger = logging.getLogger("util")

def make_sanic(name):
    logger.debug("Create Sanic app %s", name)
    app = sanic.Sanic(name)
    app.config["LOGO"] = settings.LOGO
    app.static("/static", "./static")
    return app


def make_bogo_manager():
    logger.debug("Create BogoManager instance")
    min_stop = settings.MINIMUM_SEQUENCE_STOP
    max_stop = settings.MAXIMUM_SEQUENCE_STOP
    sort_limit = getattr(settings, "SORT_LIMIT", 0)
    unsorted_lists = tools.unsorted_lists(min_stop, max_stop, sort_limit)
    speed_resolution = getattr(settings, "SPEED_RESOLUTION", 1)
    random_module = random.Random()
    random_module.seed(settings.RANDOM_SEED)
    return bogo_manager.BogoManager(unsorted_lists, speed_resolution, random_module)


def make_database_manager():
    logger.debug("Create database manager")
    dns = settings.ODBC_DNS
    schema = settings.SQL_SCHEMA_PATH
    database = db.Database(dns, schema)
    if not os.path.exists(settings.DATABASE_PATH):
        logger.debug("No database found")
        database.init()
    else:
        logger.debug("Found existing database")
    return database


def make_websocket_app(sanic_app):
    logger.debug("Create websockets manager")
    ws_manager = ws.WebSocketManager()
    logger.debug("Attach websocket url for sanic app %s", sanic_app.name)
    ws_manager.feed = sanic_app.websocket("/feed", ws_manager.feed)
    return ws_manager


def make_jinja_app():
    logger.debug("Create template rendering app")
    return html.JinjaWrapper(settings.TEMPLATE_PATH)



