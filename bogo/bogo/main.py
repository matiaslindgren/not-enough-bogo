import flask
import sqlite3
import random
import ast
import math
import datetime
import time
import itertools

import bogo.config as config
import bogo.util as util


flask_app, worker_logger, redis_app = util.make_app(__name__)

bogo_random = random.Random()
bogo_random.seed(config.RANDOM_SEED)


##############################
# REDIS
##############################

def update_iteration_speed(iter_per_second):
    return (redis_app.set("iter_speed", iter_per_second) and
            redis_app.expire("iter_speed", config.ITER_SPEED_CACHE_EXPIRE_SECONDS))

def update_total_iterations(total_iterations):
    return redis_app.set("total_iterations", total_iterations)

def get_cached_iteration_speed():
    speed = redis_app.get("iter_speed")
    return math.floor(float(speed)) if speed is not None else 0

def get_cached_iteration_count():
    total_iterations = redis_app.get("total_iterations")
    return int(total_iterations) if total_iterations is not None else 0

def get_active_bogo_id():
    return redis_app.get("active_bogo_id")

def overwrite_bogo_cache(bogo_id, sequence_length):
    """ Clear redis cache and insert new values.  """
    redis_app.flushall()
    return (
        redis_app.set("active_bogo_id", bogo_id) and
        redis_app.set("sequence_length", sequence_length) and
        update_iteration_speed(0) and
        update_total_iterations(0)
    )

def get_cached_stats():
    """ Retrieve current sorting state from the redis cache.  """
    return {
        "currentSpeed":     get_cached_iteration_speed(),
        "totalIterations":  get_cached_iteration_count(),
        "activeId":         get_active_bogo_id(),
    }

def get_full_stats(bogo_id):
    stats = get_db_stats(bogo_id)
    if get_active_bogo_id() == str(bogo_id):
        stats.update(get_cached_stats())
    return stats


##############################
# ROUTES
##############################

# TODO
# cache = flask_cache.Cache(flask_app)
# @cache.cached(timeout=60)
@flask_app.route("/")
def index():
    bogo_id = get_active_bogo_id()
    if not bogo_id:
        bogo = get_newest_bogo()
        if not bogo or not hasattr(bogo, 'id'):
            flask.abort(404)
        bogo_id = bogo['id']
    return flask.redirect(flask.url_for("view_bogo", bogo_id=bogo_id))

@flask_app.route("/about")
def about():
    return flask.render_template('about.html')

@flask_app.route("/statistics")
def statistics():
    return flask.render_template('statistics.html')

@flask_app.route("/source")
def source():
    return flask.render_template('source.html')

@flask_app.route("/eternal")
def eternal_sort():
    render_context = { "column_count": config.DUMMY_SORT_COLUMN_COUNT }
    return flask.render_template('eternal_sort.html', **render_context)


@flask_app.route("/bogo/<int:bogo_id>")
def view_bogo(bogo_id):
    get_bogo_by_id_or_404(bogo_id)
    render_context = {
            "bogo_id":              bogo_id,
            "bogo_stats_url":       flask.request.base_url + ".json",
            "active_state_url":     flask.url_for("active_state"),
            "max_polling_interval": 1000, # TODO maybe this could be calculated from the server load?
    }
    return flask.render_template('index.html', **render_context)


def full_view_for_bogo_id(bogo_id):
    return flask.url_for("view_bogo", bogo_id=bogo_id, _external=True)


@flask_app.route("/bogo/<int:bogo_id>.json")
def bogo_statistics(bogo_id):
    """ Return full statistics for a bogo with given id as JSON. """
    stats = {
        'links': {'self': full_view_for_bogo_id(bogo_id)},
        'data': get_full_stats(bogo_id)
    }

    bogo = get_bogo_by_id_or_404(bogo_id)
    prev_bogo, _, next_bogo = get_adjacent_bogos(bogo)

    if prev_bogo:
        stats['links']['previous'] = full_view_for_bogo_id(prev_bogo['id'])
    if next_bogo:
        stats['links']['next'] = full_view_for_bogo_id(next_bogo['id'])

    return flask.jsonify(**stats)


@flask_app.route("/bogo/active_state.json")
def active_state():
    """ Return the smallest set of changing variables for the active bogo. """
    stats = get_cached_stats()
    # Compress data
    data = [
        stats['activeId'],
        stats['currentSpeed'],
        stats['totalIterations']
    ]
    return flask.jsonify(data)


##############################
# BOGO LOGIC, hold on to your hat: exceedingly imperative stuff ahead
##############################


def is_sorted(xs):
    return all(xs[i-1] < xs[i] for i in range(1, len(xs)))


def sequence_generator(start, stop):
    """
    Infinite iterator yielding following tuples:
        (start, start-1, ..., 1)
        (start+1, start, start-1, ..., 1)
        (start+2, start+1, start, start-1, ..., 1)
         .
         .
         .
        (stop, stop-1, ..., start+1, start, start-1, ..., 1)
        (start, start-1, ..., 1)
        (start+1, start, start-1, ..., 1)
         .
         .
         .
    """
    return itertools.cycle(tuple(reversed(range(1, n))) for n in range(start+1, stop+2))


def bogosort_until_done(sequence, cache_interval):
    """
    Given sequence, bogosort it until it is sorted, while caching state.
    """
    delta_iterations = 0
    delta_seconds = 0.0
    total_iterations = 0

    while not is_sorted(sequence):
        perf_counter_start = time.perf_counter()
        bogo_random.shuffle(sequence)
        delta_iterations += 1
        total_iterations += 1
        delta_seconds += time.perf_counter() - perf_counter_start
        if delta_seconds >= cache_interval:
            update_iteration_speed(delta_iterations)
            update_total_iterations(total_iterations)
            delta_iterations = 0
            delta_seconds = 0.0

    return sequence, total_iterations


def bogo_cycle(sequence):
    """
    Create bogo into database for sequence, bogosort it and save the result.
    """
    worker_logger.debug("Creating a new bogo with sequence of length {}.".format(len(sequence)))
    bogo_id = create_new_bogo(sequence)
    worker_logger.debug("Begin bogosorting sequence {}.".format(sequence))
    sorted_sequence, total_iterations = bogosort_until_done(sequence, 1.0)
    worker_logger.debug("bogosort_until_done sorted sequence {} with {} iterations.".format(sorted_sequence, total_iterations))
    worker_logger.debug("Closing bogo {}.".format(bogo_id))
    close_bogo(bogo_id, bogo_random, total_iterations)


def bogo_main(min_length, max_length, max_cycles=None):
    """
    A stateful mess which is responsible of the main sorting process.
    Automatically restarts from previous known state.

    Args:
        min_length (int): Length of the first generated sequence in every cycle.
        max_length (int): Length of the last generated sequence in every cycle.
        max_cycles (int): (Optional) Maximum amount of generated cycles until the generation loop terminates. If not given, 'infinite' is assumed.
    """
    worker_logger.debug("Starting sequence cycle generation with first sequence length {} and max length {}.".format(min_length, max_length))
    if max_cycles:
        worker_logger.debug("Max cycles limited to {}.".format(max_cycles))

    sequence_cycle = map(list, sequence_generator(min_length, max_length))

    bogo = get_newest_bogo()

    if bogo is not None:
        worker_logger.debug("Found a previous bogo of id {}, length {}.".format(bogo['id'], bogo['sequence_length']))
        worker_logger.debug("Reloading state.")
        bogo_random.setstate(ast.literal_eval(bogo['random_state']))
        first_length = bogo['sequence_length']
        worker_logger.debug("Fast forwarding sequence generator next sequence length to {}.".format(first_length))
        sequence_cycle = itertools.dropwhile(lambda seq: len(seq) != first_length, sequence_cycle)
        if bogo['finished'] is None:
            worker_logger.debug("Previous bogo is not finished.")
            worker_logger.debug("Begin sorting unfinished bogo.")
            sorted_sequence, total_iterations = bogosort_until_done(next(sequence_cycle), 1.0)
            worker_logger.debug("bogosort_until_done sorted sequence {} with {} iterations.".format(sorted_sequence, total_iterations))
            worker_logger.debug("Closing bogo {}.".format(bogo['id']))
            close_bogo(bogo['id'], bogo_random, total_iterations)
            worker_logger.debug("Unfinished bogo sorted, proceeding with main cycle.")
        else:
            first_length += 1
            worker_logger.debug("Previous bogo was finished, begin main cycle from sequence length {}.".format(first_length))
    else:
        worker_logger.debug("Database is empty, starting new cycle.")

    for cycle, seq in enumerate(sequence_cycle):
        worker_logger.debug("Cycle {} starting".format(cycle))
        if max_cycles is not None and cycle > max_cycles:
            worker_logger.debug("Reached max cycle {}, bogo_main terminating.".format(cycle))
            break
        bogo_cycle(seq)
        worker_logger.debug("Cycle {} finished.".format(cycle))


##############################
# DATABASE IO
##############################

def connect_db():
    connection = sqlite3.connect(flask_app.config['DATABASE'])
    connection.row_factory = sqlite3.Row # Rows as dict-like objects
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
    Run the sql schema script on the database and flushes the redis cache.
    """
    db = get_db()
    with flask_app.open_resource(flask_app.config['DATABASE_SCHEMA'], mode='r') as schema:
        db.cursor().executescript(schema.read())
    db.commit()
    redis_app.flushall()


def execute_and_commit(query, data):
    db = get_db()
    cursor = db.execute(query, data)
    db.commit()
    return cursor


def create_new_bogo(sequence):
    """
    Insert a new bogo into the database and redis cache.
    Return its id.
    """
    query = "insert into bogos (sequence_length, started, random_state) values (?, ?, ?)"
    data = (
        len(sequence),
        datetime.datetime.utcnow().isoformat(),
        repr(bogo_random.getstate())
    )
    cursor = execute_and_commit(query, data)
    bogo_id = cursor.lastrowid
    if not overwrite_bogo_cache(bogo_id, data[0]):
        raise RuntimeError("Failed to write redis cache for bogo {}".format(bogo_id))
    return bogo_id


def close_bogo(bogo_id, random_instance, total_iterations):
    """
    Update bogo with finished date set to now, total_iterations given as parameter and with the state of the random instance.
    Clears the redis cache.
    """
    fetch_query = "select * from bogos where id=?"
    bogo = execute_and_fetch_one(fetch_query, (bogo_id, ))

    if not bogo:
        raise RuntimeError("Attempted to close a bogo with id {} but none was found in the database.".format(bogo_id))
    if bogo['finished']:
        raise RuntimeError("Attempted to close a bogo with id {} but it already had an end date {}.".format(bogo_id, bogo['finished']))

    query = "update bogos set finished=?, random_state=?, iterations=? where id=?"
    data = (
        datetime.datetime.utcnow().isoformat(),
        repr(random_instance.getstate()),
        total_iterations,
        bogo_id
    )
    execute_and_commit(query, data)
    redis_app.flushall()


def get_db_stats(bogo_id):
    """ Retrieve sorting statistics for bogo with given id from the database.  """
    bogo_row = get_bogo_by_id_or_404(bogo_id)
    return  {
        "startDate":       bogo_row['started'],
        "endDate":         bogo_row['finished'],
        "sequenceLength":  bogo_row['sequence_length'],
        "totalIterations": bogo_row['iterations'],
        "currentSpeed":    0
    }


def get_bogo_by_id_or_404(bogo_id):
    result = execute_and_fetch_one("select * from bogos where id=?", (bogo_id, ))
    if not result:
        flask.abort(404)
    return result


def execute_and_fetch_one(query, args=()):
    return get_db().execute(query, args).fetchone()

def get_previous_state():
    return execute_and_fetch_one("select * from backups order by saved desc limit 1")

def get_newest_bogo():
    return execute_and_fetch_one("select * from bogos order by started desc")

def get_older_bogo(bogo):
    select_previous = "select * from bogos where started < ? order by started desc limit 1"
    return execute_and_fetch_one(select_previous, (bogo['started'], ))

def get_newer_bogo(bogo):
    select_next = "select * from bogos where started > ? order by started limit 1"
    return execute_and_fetch_one(select_next, (bogo['started'], ))

def get_adjacent_bogos(bogo):
    return get_older_bogo(bogo), bogo, get_newer_bogo(bogo)



##############################
# CLI COMMANDS
##############################


@flask_app.cli.command("run_bogo")
def run_bogo_command():
    init_data = {
        "min_length": config.SEQUENCE_MIN_LENGTH,
        "max_length": config.SEQUENCE_MAX_LENGTH,
    }
    bogo_main(**init_data)


@flask_app.cli.command('initdb')
def initdb_command():
    print("Initializing database by executing: {}".format(flask_app.config['DATABASE_SCHEMA']))
    if input("Are you sure? (Y)\n").lower() == "y":
        init_db()
        print("Database initialized")
    else:
        print("Cancelled")



