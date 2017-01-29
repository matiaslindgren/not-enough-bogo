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


flask_app, celery_app, celery_logger, redis_app = util.make_app(__name__)

bogo_random = random.Random()
bogo_random.seed(config.RANDOM_SEED)


##############################
# REDIS
##############################

def update_iteration_speed(iter_per_second):
    return (redis_app.set("iter_speed", iter_per_second) and
            redis_app.expire("iter_speed", 3))

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
# BOGO LOGIC
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


# TODO: rethink the duties of this function and bogo_main, who
# should write the bogos and how to restart backups?
def sort_until_done(sequence, from_backup=False, init_total_iterations=0):
    """
    A stateful mess which shuffles the given sequence until it is sorted.
    If from_backup is given and True, this function will not create a new bogo into the database.
    If from_backup is False, a new bogo will be written into the database.
    Writes backups of the sorting state at BACKUP_INTERVAL iterations.
    """
    total_iterations = init_total_iterations
    backup_interval = config.BACKUP_INTERVAL
    iter_speed_resolution = config.ITER_SPEED_RESOLUTION

    if from_backup:
        bogo = get_newest_bogo()
        if not bogo or not bogo['id']:
            raise RuntimeError("Attempted to restart from backup but get_newest_bogo returned {}.".format(tuple(bogo)))

        this_bogo_id = bogo['id']
        celery_logger.info('Sorting a backup, fetched the id {} from the database.'.format(this_bogo_id))
        overwrite_bogo_cache(this_bogo_id, len(sequence))
    else:
        this_bogo_id = create_new_bogo(sequence)
        celery_logger.info('Writing backup for bogo {}'.format(this_bogo_id))

        backup_sorting_state(sequence, bogo_random, total_iterations)

    celery_logger.info('Begin bogosorting with:\nsequence: {}\nbogo id: {}\nbackup interval: {}\niter speed resolution: {}.'.format(sequence, this_bogo_id, backup_interval, iter_speed_resolution))

    iteration = 0
    cycle_total_time = 0.0

    while not is_sorted(sequence):
        begin_time = time.perf_counter()
        bogo_random.shuffle(sequence)
        if iteration >= backup_interval:
            celery_logger.info('Writing backup for bogo {}'.format(this_bogo_id))
            backup_sorting_state(sequence, bogo_random, total_iterations)
            iteration = 0
        iteration += 1
        total_iterations += 1
        cycle_total_time += time.perf_counter() - begin_time
        if iteration % iter_speed_resolution == 0:
            update_iteration_speed(iter_speed_resolution/cycle_total_time)
            update_total_iterations(total_iterations)
            cycle_total_time = 0.0

    celery_logger.info('Done sorting bogo {} in {} iterations.'.format(this_bogo_id, total_iterations))

    close_bogo(this_bogo_id, total_iterations)
    celery_logger.info('Bogo {} closed.'.format(this_bogo_id))

    if redis_app.flushall():
        celery_logger.info('Flushed all keys from the redis instance.')
    else:
        celery_logger.error('Flushing all redis keys failed.')


@celery_app.task(ignore_result=True)
def bogo_main(max_cycles=None):
    """
    Main sorting function responsible of sorting every defined sequence from
    list(range(1, 11)) up to list(range(1, config.SEQUENCE_MAX_LENGTH)).
    It might be a good idea to run this in a thread.

    Automatically restarts from previous known state.
    """
    min_length = config.SEQUENCE_MIN_LENGTH
    max_length = config.SEQUENCE_MAX_LENGTH
    celery_logger.info("Initializing bogo_main with:\nmin length: {}\nmax length: {}".format(min_length, max_length))
    previous_state = get_previous_state_all()

    if previous_state:
        previous_seq = ast.literal_eval(previous_state['sequence'])
        celery_logger.info("Previous backup found, seq of len {}".format(len(previous_seq)))

        next_seq_len = min(max_length, len(previous_seq) + 1)

        previous_random = ast.literal_eval(previous_state['random_state'])
        bogo_random.setstate(previous_random)

        backup_iterations = previous_state['total_iterations']

        celery_logger.info("Resuming sorting with backup: {}".format(previous_seq))
        sort_until_done(previous_seq, from_backup=True, init_total_iterations=backup_iterations)
        celery_logger.info("Backup sequence sorted: {}".format(previous_seq))
    else:
        celery_logger.info("No backups found, starting a new bogo cycle.")
        next_seq_len = min_length

    for cycle, seq in enumerate(map(list, sequence_generator(next_seq_len, max_length))):
        if max_cycles is not None and cycle > max_cycles:
            celery_logger.info("Reached max cycle {}, bogo_main returning".format(cycle))
            break
        celery_logger.info("Cycle {}, call sort_until_done with: {}".format(cycle, seq))
        sort_until_done(seq)
        celery_logger.info("Cycle {}, sort_until_done returned, parameter is now {}".format(cycle, seq))


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
    query = "insert into bogos (sequence_length, started) values (?, ?)"
    data = (
        len(sequence),
        datetime.datetime.utcnow().isoformat()
    )
    cursor = execute_and_commit(query, data)
    bogo_id = cursor.lastrowid
    if not overwrite_bogo_cache(bogo_id, data[0]):
        raise RuntimeError("Failed to write redis cache for bogo {}".format(bogo_id))
    return bogo_id


def close_bogo(bogo_id, total_iterations):
    """
    Update bogo with finished date set to now and total_iterations given as parameter.
    """
    fetch_query = "select * from bogos where id=?"
    bogo = execute_and_fetch_one(fetch_query, (bogo_id, ))

    if not bogo:
        raise RuntimeError("Attempted to close a bogo with id {} but none was found in the database.".format(bogo_id))
    if bogo['finished']:
        raise RuntimeError("Attempted to close a bogo with id {} but it already had an end date {}.".format(bogo_id, bogo['finished']))

    query = "update bogos set finished=? where id=?"
    data = (datetime.datetime.utcnow().isoformat(), bogo_id)
    execute_and_commit(query, data)
    query = "update bogos set iterations=? where id=?"
    data = (total_iterations, bogo_id)
    execute_and_commit(query, data)


def backup_sorting_state(sequence, random_instance, total_iterations):
    """
    Write backup of the current sorting state.
    Returns the id of the inserted backup row.
    """
    query = "insert into backups (sequence, random_state, saved, total_iterations) values (?, ?, ?, ?)"
    backup_data = (
        repr(sequence),
        repr(random_instance.getstate()),
        datetime.datetime.utcnow().isoformat(),
        total_iterations
    )
    cursor = execute_and_commit(query, backup_data)
    return cursor.lastrowid


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

def get_adjacent_bogos(bogo):
    return get_older_bogo(bogo), bogo, get_newer_bogo(bogo)



##############################
# CLI COMMANDS
##############################


@flask_app.cli.command("run_bogo")
def run_bogo_command():
    bogo_main.delay()


@flask_app.cli.command('initdb')
def initdb_command():
    print("Initializing database by executing: {}".format(flask_app.config['DATABASE_SCHEMA']))
    if input("Are you sure? (Y)\n").lower() == "y":
        init_db()
        print("Database initialized")
    else:
        print("Cancelled")



