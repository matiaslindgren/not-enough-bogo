import flask
import os.path
import logging
import celery.utils.log as celery_log
import redis
import bogo.config as config
import bogo.tasks as tasks


def make_flask(name):
    flask_app = flask.Flask(
        name,
        template_folder="../templates",
        static_folder="../static"
    )
    flask_app.config.update(
        DATABASE=os.path.join(flask_app.root_path, config.DATABASE_NAME),
        CELERY_BROKER_URL=config.BROKER_URL,
        DATABASE_SCHEMA=os.path.join(flask_app.root_path, config.SCHEMA_NAME)
    )
    return flask_app


def make_celery_logger(name):
    celery_logger = celery_log.get_task_logger(name)
    celery_logger.setLevel(logging.DEBUG)
    return celery_logger


def make_redis():
    return redis.StrictRedis(host="localhost", port=config.REDIS_PORT)


def make_app(name):
    flask_app = make_flask(name)
    celery_app = tasks.make_celery(flask_app)
    celery_logger = make_celery_logger(name)
    redis_app = make_redis()
    return flask_app, celery_app, celery_logger, redis_app
