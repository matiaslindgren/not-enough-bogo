import flask
import tasks

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


@celery.task()
def sort_until_done(integers):
    import time
    time.sleep(1)
    return sorted(integers)


# def bogosort(seq):
    # """In-place bogosort with inversion number counter."""
    # inversion_counter = collections.Counter()
    # current_inversions = inversions.inversion_number(seq)

    # # bogosort
    # while current_inversions:
    #     inversion_counter[current_inversions] += 1
    #     random.shuffle(seq)
    #     current_inversions = inversions.inversion_number(seq)

