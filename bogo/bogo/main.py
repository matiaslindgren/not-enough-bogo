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


##############################
# REDIS
##############################

def update_iteration_speed(iter_per_second):
    return redis_app.set("iter_speed", iter_per_second)


def get_active_bogo_id():
    return redis_app.get("active_bogo_id")


def overwrite_bogo_cache(bogo_id, sequence_length, start_date):
    """
    Clear redis cache and insert new values.
    """
    redis_app.flushall()
    return (redis_app.set("active_bogo_id", bogo_id) and
            redis_app.set("sequence_length", sequence_length) and
            redis_app.set("start_date", start_date) and
            update_iteration_speed(0))


def get_stats(bogo_id):
    """
    Retrieve sorting statistics for bogo with given id.
    If the bogo is actively sorting a sequence, fetch
    data from the redis cache, else from the database.
    """
    if not bogo_id:
        stats = {}
    elif get_active_bogo_id() == str(bogo_id):
        stats = {
            "startDate":      redis_app.get("start_date"),
            "endDate":        None,
            "sequenceLength": redis_app.get("seqeuence_length"),
            "currentSpeed":   ast.literal_eval(redis_app.get("iter_speed"))
        }
    else:
        bogo_row = get_bogo_by_id(bogo_id)
        if bogo_row:
            stats = {
                "startDate":      bogo_row['started'],
                "endDate":        bogo_row['finished'],
                "sequenceLength": bogo_row['sequence_length'],
                "currentSpeed":   0
            }
        else:
            stats = {}
    return stats


##############################
# ROUTES
##############################

@flask_app.route("/")
def index():
    bogo_id = get_active_bogo_id()
    if not bogo_id:
        print("WARNING: no active bogo in redis cache!")
        bogo = get_newest_bogo()
        if not bogo or 'id' not in bogo:
            flask.abort(404)
        bogo_id = bogo['id']
    return flask.redirect(flask.url_for("view_bogo", bogo_id=bogo_id))


@flask_app.route("/about")
def about():
    return "nothing here, yet"


@flask_app.route("/history")
def history():
    return "nothing here, yet"


@flask_app.route("/bogo/<int:bogo_id>")
def view_bogo(bogo_id):
    prev_bogo, _, next_bogo = get_adjacent_bogos(bogo_id)
    render_context = {
        "bogo_stats_url": flask.request.base_url + "/statistics.json",
        "start_date": redis_app.get('start_date'),
        "sequence_length": redis_app.get('sequence_length'),
        "page": {
            "previous": prev_bogo['id'] if prev_bogo else None,
            "next": next_bogo['id'] if next_bogo else None
        }
    }
    return flask.render_template('index.html', **render_context)


@flask_app.route("/bogo/<int:bogo_id>/statistics.json")
def bogo_statistics(bogo_id):
    stats = get_stats(bogo_id)
    return flask.jsonify(currentSpeed=stats['currentSpeed'], endDate=stats['endDate'])


##############################
# BOGO LOGIC
##############################


def normalized_messiness(seq):
    """
    Heuristic sortedness measure.
    Works only if list(sorted(seq)) == list(range(1, len(seq)+1)).

    Returns 0 if list(seq) == list(range(1, len(seq)+1)).
    Else returns an integer d > 0, which increases for every
    integer in seq that is further away from its index.
    """
    return int(math.ceil(sum(abs(i + 1 - x) for i, x in enumerate(seq))/len(seq)))


def all_sequences(start, step, max_length):
    seq_upper_limits = range(start, max_length + step, step)
    return (list(reversed(range(1, n))) for n in seq_upper_limits)


def sort_until_done(sequence):
    """
    Bogosort sequence until it is sorted.
    Writes iterations to the database.
    Writes backups of the sorting state at BACKUP_INTERVAL iterations.
    """
    this_bogo_id = create_new_bogo(sequence)
    backup_interval = config.BACKUP_INTERVAL
    iter_speed_resolution = config.ITER_SPEED_RESOLUTION

    celery_logger.info('Begin bogosorting with:\nsequence: {}\nbogo id: {}\nbackup interval: {}\niter speed resolution: {}.'.format(sequence, this_bogo_id, backup_interval, iter_speed_resolution))

    celery_logger.info('Writing backup for bogo {}'.format(this_bogo_id))
    backup_sorting_state(sequence, bogo_random)

    messiness = normalized_messiness(sequence)
    iteration = 0
    total_iterations = 0
    cycle_total_time = 0.0


    while messiness > 0:
        begin_time = time.perf_counter()
        bogo_random.shuffle(sequence)
        messiness = normalized_messiness(sequence)
        if iteration >= backup_interval:
            celery_logger.info('Writing backup for bogo {}'.format(this_bogo_id))
            backup_sorting_state(sequence, bogo_random)
            iteration = 0
        iteration += 1
        total_iterations += 1
        cycle_total_time += time.perf_counter() - begin_time
        if iteration % iter_speed_resolution == 0:
            # This should be checked outside the task in a black box manner.
            # Though, then it requires an additional thread
            update_iteration_speed(iter_speed_resolution/cycle_total_time)
            cycle_total_time = 0.0

    celery_logger.info('Done sorting bogo {} in {} iterations.'.format(this_bogo_id, total_iterations))

    close_bogo(this_bogo_id)
    celery_logger.info('Bogo {} closed.'.format(this_bogo_id))

    if redis_app.flushall():
        celery_logger.info('Flushed all keys from the redis instance.')
    else:
        celery_logger.error('Flushing all redis keys failed.')


@celery_app.task(ignore_result=True)
def bogo_main():
    """
    Main sorting function responsible of sorting every defined sequence from
    list(range(1, 11)) up to list(range(1, config.SEQUENCE_MAX_LENGTH)).
    It might be a good idea to run this in a thread.

    Automatically restarts from previous known state.
    """
    step = config.SEQUENCE_STEP
    max_length = config.SEQUENCE_MAX_LENGTH
    celery_logger.info("Initializing bogo_main with:\nsequence step: {}\nlast sequence length: {}".format(step, max_length))
    previous_state = get_previous_state_all()

    if previous_state:
        previous_seq = ast.literal_eval(previous_state['sequence'])
        celery_logger.info("Previous backup found, seq of len {}".format(len(previous_seq)))
        next_seq_len = step + 1 + len(previous_seq)
        not_yet_sorted = itertools.chain((previous_seq, ), all_sequences(next_seq_len, step, max_length))
        previous_random = ast.literal_eval(previous_state['random_state'])
        bogo_random.setstate(previous_random)
    else:
        celery_logger.info("No backups found, starting a new bogo cycle.")
        next_seq_len = step + 1
        not_yet_sorted = all_sequences(next_seq_len, step, max_length)

    for seq in not_yet_sorted:
        celery_logger.info("Call sort_until_done with: {}".format(seq))
        sort_until_done(seq)
        celery_logger.info("sort_until_done returned, parameter is now {}".format(seq))


##############################
# DATABASE IO
##############################

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


def get_bogo_by_id(bogo_id):
    return execute_and_fetch_one("select * from bogos where id=?", (bogo_id, ))


def get_previous_state_all():
    return execute_and_fetch_one("select * from backups order by saved desc")

def get_newest_bogo():
    return execute_and_fetch_one("select * from bogos order by started desc")

def get_older_bogo(bogo):
    select_previous = "select * from bogos where started < ? order by started desc limit 1"
    return execute_and_fetch_one(select_previous, (bogo['started'], ))

def get_newer_bogo(bogo):
    select_next = "select * from bogos where started > ? order by started limit 1"
    return execute_and_fetch_one(select_next, (bogo['started'], ))


def get_adjacent_bogos(bogo_id):
    this_bogo = get_bogo_by_id(bogo_id)
    if not this_bogo:
        raise RuntimeError("Cannot retrieve adjacent bogos for bogo {} which is not in the database.".format(bogo_id))
    return get_older_bogo(this_bogo), this_bogo, get_newer_bogo(this_bogo)



def create_new_bogo(sequence):
    """
    Insert a new bogo into the database and redis cache.
    Return its id.
    """
    db = get_db()

    query = "insert into bogos (sequence_length, started) values (?, ?)"
    data = (
        len(sequence),
        datetime.datetime.utcnow().isoformat()
    )
    cursor = db.execute(query, data)
    db.commit()

    bogo_id = cursor.lastrowid
    if not overwrite_bogo_cache(bogo_id, *data):
        raise RuntimeError("Failed to write redis cache for bogo {}".format(bogo_id))

    return bogo_id


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



##############################
# CLI COMMANDS
##############################


@flask_app.cli.command("run_bogo")
def run_bogo_command():
    res = bogo_main.delay()


@flask_app.cli.command('initdb')
def initdb_command():
    print("Initializing database by executing: {}".format(flask_app.config['DATABASE_SCHEMA']))
    if input("Are you sure? (Y)\n").lower() == "y":
        init_db()
        print("Database initialized")
    else:
        print("Cancelled")



