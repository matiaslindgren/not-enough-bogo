import os.path
import sqlite3
import flask
import tasks
import math
import random
import ast
import datetime
import logging
from celery.utils.log import get_task_logger


BROKER_URL = 'amqp://guest:guest@localhost:5672//'
DATABASE_NAME = 'app.db'
RANDOM_SEED = 1148599
random.seed(RANDOM_SEED)

flask_app = flask.Flask(__name__)
flask_app.config.update(
    DATABASE=os.path.join(flask_app.root_path, DATABASE_NAME),
    CELERY_BROKER_URL=BROKER_URL,
    CELERY_RESULT_BACKEND=BROKER_URL
)
celery = tasks.make_celery(flask_app)

celery_logger = get_task_logger(__name__)
celery_logger.setLevel(logging.DEBUG)



APP_CONTEXT_DATABASE_NAME = "_" + DATABASE_NAME.replace(".", "_")
DATABASE_SCHEMA = "schema.sql"


@flask_app.route("/")
def main(name=None):
    return flask.render_template('main.html', name=name)


@flask_app.route("/history")
def history():
    # return flask.render_template('history.html', name=name)
    return "TODO"


@celery.task()
def sort_until_done(integers):
    import time
    time.sleep(5)
    return sorted(integers)


def connect_db():
    connection = sqlite3.connect(flask_app.config['DATABASE'])
    connection.row_factory = sqlite3.Row
    return connection


def get_db():
    if not hasattr(flask.g, APP_CONTEXT_DATABASE_NAME):
        setattr(flask.g, APP_CONTEXT_DATABASE_NAME, connect_db())
    return getattr(flask.g, APP_CONTEXT_DATABASE_NAME)


@flask_app.teardown_appcontext
def close_db(error):
    if hasattr(flask.g, APP_CONTEXT_DATABASE_NAME):
        getattr(flask.g, APP_CONTEXT_DATABASE_NAME).close()


def init_db():
    db = get_db()
    with flask_app.open_resource(DATABASE_SCHEMA, mode='r') as schema:
        db.cursor().executescript(schema.read())
    db.commit()


@flask_app.cli.command('initdb')
def initdb_command():
    print("Initializing database, existing tables will be dropped.")
    if input("Are you sure? (Y)\n").lower() == "y":
        init_db()
        print("Database initialized")
    else:
        print("Cancelled")


def get_previous_state_from_db():
    db = get_db()
    query = "select sequence, random_state from backups order by id desc"
    return db.execute(query).fetchone()


def backup_sorting_state(sequence):
    db = get_db()
    query = "insert into backups (sequence, random_state, saved) values (?, ?, ?)"
    backup_data = (
        repr(sequence),
        repr(random.getstate()),
        datetime.date.today().isoformat()
    )
    db.execute(query, backup_data)
    db.commit()


def next_list(n):
    return list(range(1, n+1))


def powers_of_ten(start=1, end=7):
    return map(lambda n: 10**n, range(start, end))


def restart_from_previous_known_state():
    row = get_previous_state_from_db()
    sequence, random_module_state = tuple(map(ast.literal_eval, row))

    random.seed(RANDOM_SEED)
    random.setstate(random_module_state)
    bogo(sequence)


def bogo(sequence=None):
    prev_ten_exponent = int(math.log10(len(sequence))) if sequence else 1
    is_restarting = sequence is not None

    for length in powers_of_ten(prev_ten_exponent, 7):
        if is_restarting:
            is_restarting = False
        else:
            sequence = next_list(length)

        result = sort_until_done.delay(sequence)
        result.wait()


if __name__ == "__main__":
    if not celery.current_task:
        restart_from_previous_known_state()

