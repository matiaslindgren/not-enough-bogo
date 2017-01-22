import flask
import sqlite3
import math
import random
import ast
import datetime
import time

import src.config as config
import src.util as util


random.seed(config.RANDOM_SEED)

flask_app, celery_app, celery_logger = util.make_app(__name__)


iteration_speed = 0.0
def update_iteration_speed(iter_per_second):
    global iteration_speed
    iteration_speed = iter_per_second

def get_iteration_speed():
    return iteration_speed


@flask_app.cli.command("test1")
def test1():
    res = sort_until_done.delay(list(reversed(range(1, 101))))
    res.wait()

@flask_app.route("/")
def main():
    return flask.render_template('main.html')


@flask_app.route("/current_speed.json")
def get_current_iteration_speed():
    print("get_current_iteration_speed at {}".format(get_iteration_speed()))
    return flask.jsonify(current_speed=get_iteration_speed())


@flask_app.route("/history")
def history():
    # return flask.render_template('history.html', name=name)
    return "TODO"


def normalized_messiness(seq):
    """
    Heuristic sortedness measure.
    Works only if list(sorted(seq)) == list(range(1, len(seq)+1)).

    Returns 0 if list(seq) == list(range(1, len(seq)+1)).
    Else returns an integer d > 0, which increases for every
    integer in seq that is further away from its index.
    """
    return int(math.ceil(sum(abs(i + 1 - x) for i, x in enumerate(seq))/len(seq)))


# TODO track iteration speed in some 'rationally global' variable
# TODO break up this to something more sane:
#  - create the state backup before calling this task and pass its id
@celery_app.task
def sort_until_done(integers):
    """
    Bogosort integers until it is sorted.
    Writes iterations to the database.
    Writes backups of the sorting state at BACKUP_INTERVAL iterations.
    """
    this_bogo_id = create_new_bogo(integers)

    celery_logger.info('Sorting {} integers with bogo id {}.'.format(len(integers), this_bogo_id))

    i = 0
    messiness = normalized_messiness(integers)
    # store_iteration(this_bogo_id, messiness)

    while messiness > 0:
        begin_time = time.perf_counter()
        bogo_random.shuffle(sequence)
        messiness = normalized_messiness(sequence)
        if iterations >= config.BACKUP_INTERVAL:
            backup_sorting_state(sequence, bogo_random)
            iterations = 0
        iterations += 1
        iteration_time = time.perf_counter() - begin_time
        update_iteration_speed(1.0/iteration_time)

    close_bogo(this_bogo_id)

    celery_logger.info('Done sorting bogo {}.'.format(this_bogo_id))


def create_new_bogo(sequence):
    """
    Insert a new bogo into the database and return its id.
    """
    db = get_db()

    query = "insert into bogos (sequence_length, started) values (?, ?)"
    data = (
        len(sequence),
        datetime.datetime.utcnow().isoformat()
    )
    cursor = db.execute(query, data)
    db.commit()

    return cursor.lastrowid


def close_bogo(bogo_id):
    """
    Set the finished field of bogo with id bogo_id to now.
    """
    db = get_db()

    fetch_query = "select * from bogos where id=?"
    bogo = execute_and_fetch_one(fetch_query, (bogo_id, ))

    if not bogo:
        raise RuntimeError("Attempted to close a bogo with id {} but none was found in the database.".format(bogo_id))
    if bogo['finished']:
        raise RuntimeError("Attempted to close a bogo with id {} but it already had an end date {}.".format(bogo_id, bogo['finished']))

    query = "update bogos set finished=? where id=?"
    data = (datetime.datetime.utcnow().isoformat(), bogo_id)

    db.execute(query, data)
    db.commit()


def store_iteration(bogo_id, messiness):
    """
    Insert a single iteration into the database.
    """
    db = get_db()
    query = "insert into iterations (bogo, messiness) values (?, ?)"
    db.execute(query, (bogo_id, messiness))
    db.commit()


def connect_db():
    connection = sqlite3.connect(flask_app.config['DATABASE'])
    connection.row_factory = sqlite3.Row
    return connection


@flask_app.teardown_appcontext
def _close_db(error):
    if hasattr(flask.g, config.APP_CONTEXT_DATABASE_NAME):
        getattr(flask.g, config.APP_CONTEXT_DATABASE_NAME).close()


def get_db():
    """
    Return a connection to the app database.
    """
    if not hasattr(flask.g, config.APP_CONTEXT_DATABASE_NAME):
        setattr(flask.g, config.APP_CONTEXT_DATABASE_NAME, connect_db())
    return getattr(flask.g, config.APP_CONTEXT_DATABASE_NAME)


def init_db():
    """
    Run the sql schema script on the database.
    """
    db = get_db()
    with flask_app.open_resource(flask_app.config['DATABASE_SCHEMA'], mode='r') as schema:
        db.cursor().executescript(schema.read())
    db.commit()


@flask_app.cli.command('initdb')
def initdb_command():
    print("Initializing database by executing: {}".format(flask_app.config['DATABASE_SCHEMA']))
    if input("Are you sure? (Y)\n").lower() == "y":
        init_db()
        print("Database initialized")
    else:
        print("Cancelled")


def backup_sorting_state(sequence, random_instance):
    """
    Write sequence, the state of the random module and the date into the database.
    Returns the id of the inserted backup row.
    """
    db = get_db()
    query = "insert into backups (sequence, random_state, saved) values (?, ?, ?)"
    backup_data = (
        repr(sequence),
        repr(random_instance.getstate()),
        datetime.datetime.utcnow().isoformat()
    )
    cursor = db.execute(query, backup_data)
    db.commit()
    return cursor.lastrowid


def execute_and_fetch_one(query, args=()):
    return get_db().execute(query, args).fetchone()


def get_previous_state_all():
    return execute_and_fetch_one("select * from backups order by id desc")

@flask_app.cli.command('restart_from_backup')
def restart_from_previous_known_state():
    raise NotImplementedError("restart from previous state not implemented")
    row = get_previous_state_from_db()
    sequence, random_module_state = tuple(map(ast.literal_eval, row))
    random.setstate(random_module_state)
    bogo(sequence)


def all_sequences(step, max_length):
    seq_upper_limits = range(step + 1, max_length + step, step)
    return (list(range(1, n)) for n in seq_upper_limits)


def bogo(sequence=None):
    for seq in all_sequences(config.SEQUENCE_STEP, config.SEQUENCE_MAX_LENGTH):
        seq.reverse()
        result = sort_until_done.delay(seq)
        result.wait()

