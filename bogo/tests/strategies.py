import datetime
import hypothesis
from bogoapp import settings

db_indexes = hypothesis.strategies.integers(
        min_value=1,
        max_value=2**63-1)

natural_numbers = hypothesis.strategies.integers(
        min_value=0)

maximum_sequence_stop = hypothesis.strategies.integers(
        min_value=settings.MINIMUM_SEQUENCE_STOP,
        max_value=settings.MAXIMUM_SEQUENCE_STOP*100)

datetimes = hypothesis.strategies.datetimes(
        min_value=datetime.datetime(2000, 1, 1, 0, 0),
        max_value=datetime.datetime(4000, 12, 31, 23, 59, 59))

timedeltas = hypothesis.strategies.timedeltas(
        min_value=datetime.timedelta(**{settings.TIMESPEC: 1}),
        max_value=datetime.timedelta(days=4000*365))

def isoformatted(dates):
    return tuple(d.isoformat(timespec=settings.TIMESPEC) for d in dates)

@hypothesis.strategies.composite
def _unsorted_list(draw):
    sequence_stop = draw(maximum_sequence_stop)
    return list(range(sequence_stop, 0 , -1))

@hypothesis.strategies.composite
def _datetime_and_later(draw):
    start = draw(datetimes)
    later = start + draw(timedeltas)
    return start, later

@hypothesis.strategies.composite
def _database_bogo_row(draw):
    db_id = draw(db_indexes)
    unsorted_list_string = repr(draw(_unsorted_list()))
    created, finished = isoformatted(draw(_datetime_and_later()))
    shuffles = draw(natural_numbers)
    return db_id, unsorted_list_string, created, finished, shuffles

@hypothesis.strategies.composite
def _bogo_init_args(draw):
    return (draw(db_indexes),
            draw(_unsorted_list()),
            *isoformatted(draw(_datetime_and_later())),
            draw(natural_numbers))

database_bogo_rows = _database_bogo_row()
bogo_init_arg_tuples = _bogo_init_args()

