import flask
import tasks
import numpy


BROKER_URL = 'amqp://guest:guest@localhost:5672//'

flask_app = flask.Flask(__name__)
flask_app.config.update(
    CELERY_BROKER_URL=BROKER_URL,
    CELERY_RESULT_BACKEND=BROKER_URL
)
celery = tasks.make_celery(flask_app)


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


def get_from_db():
    #TODO
    return []


def next_list(n):
    return list(range(1, n+1))


def powers_of_ten(start=1, end=7):
    return map(lambda n: 10**n, range(start, end))


def restart_from_previous_known_state():
    sequence = get_from_db()
    bogo(sequence)


def bogo(sequence=None):
    prev_ten_exponent = int(numpy.log10(len(sequence))) if sequence else 1
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
