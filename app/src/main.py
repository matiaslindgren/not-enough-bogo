import flask
import sqlite3
import math
import random
import ast
import datetime

import src.config as config
import src.util as util


random.seed(config.RANDOM_SEED)

flask_app, celery_app, celery_logger = util.make_app(__name__)


@flask_app.route("/")
def main(name=None):
    return flask.render_template('main.html', name=name)


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
@celery_app.task
def sort_until_done(integers):
    """
    Bogosort integers until it is sorted.
    Writes iterations to the database.
    Writes backups of the sorting state at BACKUP_INTERVAL iterations.
    """
    this_bogo_id = create_new_bogo(integers[:])

    celery_logger.info('Sorting {} integers with bogo id {}.'.format(len(integers), this_bogo_id))

    i = 0
    messiness = normalized_messiness(integers)
    store_iteration(this_bogo_id, messiness)

    while messiness > 0:
        random.shuffle(integers)
        messiness = normalized_messiness(integers)
        store_iteration(this_bogo_id, messiness)
        if i >= config.BACKUP_INTERVAL:
            backup_sorting_state(integers)
            i = 0
        i += 1

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
        datetime.date.today().isoformat()
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
    bogo = db.execute(fetch_query, (bogo_id,)).fetchone()

    if not bogo:
        raise RuntimeError("Attempted to close a bogo with id {} but none was found in the database.".format(bogo_id))
    if bogo['finished']:
        raise RuntimeError("Attempted to close a bogo with id {} but it already had an end date {}.".format(bogo_id, bogo['finished']))

    query = "update bogos set finished=? where id=?"
    data = (datetime.date.today().isoformat(), bogo_id)

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


def backup_sorting_state(sequence):
    """
    Write sequence, the state of the random module and the date into the database.
    """
    db = get_db()
    query = "insert into backups (sequence, random_state, saved) values (?, ?, ?)"
    backup_data = (
        repr(sequence),
        repr(random.getstate()),
        datetime.date.today().isoformat()
    )
    db.execute(query, backup_data)
    db.commit()


def get_previous_state_from_db():
    db = get_db()
    query = "select sequence, random_state from backups order by id desc"
    return db.execute(query).fetchone()


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

