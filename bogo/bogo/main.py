import flask
import sqlite3
import math
import random
import ast
import datetime
import time
import itertools

import bogo.config as config
import bogo.util as util


flask_app, celery_app, celery_logger, redis_app = util.make_app(__name__)

bogo_random = random.Random()
bogo_random.seed(config.RANDOM_SEED)


def update_iteration_speed(iter_per_second):
    return redis_app.set("iter_speed", iter_per_second)

def get_iteration_speed():
    return redis_app.get("iter_speed")


@flask_app.route("/")
def main():
    return flask.render_template('index.html')


@flask_app.route("/current_speed.json")
def get_current_iteration_speed():
    speed = get_iteration_speed().decode('utf-8')
    print("get_current_iteration_speed at {}".format(speed))
    return flask.jsonify(current_speed=speed)


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


def sort_until_done(sequence):
    """
    Bogosort sequence until it is sorted.
    Writes iterations to the database.
    Writes backups of the sorting state at BACKUP_INTERVAL iterations.
    """
    this_bogo_id = create_new_bogo(sequence)

    celery_logger.info('Sorting {} sequence with bogo id {}.'.format(len(sequence), this_bogo_id))

    messiness = normalized_messiness(sequence)
    iterations = 0
    cycle_total_time = 0.0
    # store_iteration(this_bogo_id, messiness)

    while messiness > 0:
        begin_time = time.perf_counter()
        bogo_random.shuffle(sequence)
        messiness = normalized_messiness(sequence)
        if iterations >= config.BACKUP_INTERVAL:
            celery_logger.info('Writing backup for bogo {}'.format(this_bogo_id))
            backup_sorting_state(sequence, bogo_random)
            iterations = 0
        iterations += 1
        cycle_total_time += time.perf_counter() - begin_time
        if iterations % config.ITER_SPEED_RESOLUTION == 0:
            update_iteration_speed(config.ITER_SPEED_RESOLUTION/cycle_total_time)
            cycle_total_time = 0.0

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


def all_sequences(start, step, max_length):
    seq_upper_limits = range(start, max_length + step, step)
    return (list(reversed(range(1, n))) for n in seq_upper_limits)


@celery_app.task(ignore_result=True)
def bogo_main():
    """
    Main sorting function responsible of sorting every defined sequence from
    list(range(1, 11)) up to list(range(1, config.SEQUENCE_MAX_LENGTH)).
    It might be a good idea to run this in a thread.

    Automatically restarts from previous known state.
    """
    print("Initializing bogo_main")
    step = config.SEQUENCE_STEP
    max_length = config.SEQUENCE_MAX_LENGTH
    print("Step {}".format(step))
    print("Max length {}".format(max_length))
    previous_state = get_previous_state_all()

    if previous_state:
        previous_seq = ast.literal_eval(previous_state['sequence'])
        print("Previous backup found, seq of len {}".format(len(previous_seq)))
        next_seq_len = step + 1 + len(previous_seq)
        not_yet_sorted = itertools.chain((previous_seq, ), all_sequences(next_seq_len, step, max_length))
        previous_random = ast.literal_eval(previous_state['random_state'])
        bogo_random.setstate(previous_random)
    else:
        print("No backups found, starting a new bogo cycle.")
        next_seq_len = step + 1
        not_yet_sorted = all_sequences(next_seq_len, step, max_length)

    not_yet_sorted = tuple(not_yet_sorted)
    print("Begin bogosort loop with {} lists".format(len(not_yet_sorted)))
    for seq in not_yet_sorted:
        print("Calling sort_until_done with seq {}".format(seq))
        sort_until_done(seq)
        print("Done")


@flask_app.cli.command("run_bogo")
def run_bogo_command():
    res = bogo_main.delay()


