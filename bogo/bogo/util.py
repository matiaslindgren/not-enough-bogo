import flask
import sys
import os.path
import logging
import redis
import bogo.config as config


def make_flask(name):
    flask_app = flask.Flask(
        name,
        template_folder="../templates",
        static_folder="../static"
    )
    flask_app.config.update(
        DATABASE=os.path.join(flask_app.root_path, config.DATABASE_NAME),
        DATABASE_SCHEMA=os.path.join(flask_app.root_path, config.SCHEMA_NAME),
        TEMPLATES_AUTO_RELOAD=config.TEMPLATES_AUTO_RELOAD
    )
    return flask_app


def make_worker_logger(name):
    file_handler = logging.FileHandler(config.WORKER_LOGGER_PATH)
    file_handler.setLevel(logging.DEBUG)
    worker_logger = logging.getLogger(name)
    worker_logger.setLevel(logging.DEBUG)
    worker_logger.addHandler(file_handler)
    return worker_logger


def make_redis():
    return redis.StrictRedis(
        host="localhost",
        port=config.REDIS_PORT,
        db=0,
        decode_responses=config.REDIS_DECODE_RESPONSES
    )
