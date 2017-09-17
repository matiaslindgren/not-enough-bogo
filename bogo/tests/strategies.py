import datetime
import hypothesis
from unittest.mock import MagicMock

from tests import conftest
from bogoapp import settings
from bogoapp import tools

def AsyncMock(*args, **kwargs):
    """https://blog.miguelgrinberg.com/post/unit-testing-asyncio-code"""
    m = MagicMock(*args, **kwargs)

    async def mock_coro(*args, **kwargs):
        return m(*args, **kwargs)

    mock_coro.mock = m
    return mock_coro

db_indexes = hypothesis.strategies.integers(
        min_value=1,
        max_value=2**63-1)

natural_numbers = hypothesis.strategies.integers(
        min_value=0)

unsorted_list_cycle_lengths = hypothesis.strategies.integers(
        min_value=conftest.LIST_CYCLE_MIN_LENGTH,
        max_value=conftest.LIST_CYCLE_MAX_LENGTH)

maximum_sequence_stop = hypothesis.strategies.integers(
        min_value=settings.MINIMUM_SEQUENCE_STOP,
        max_value=settings.MAXIMUM_SEQUENCE_STOP*100)

datetimes = hypothesis.strategies.datetimes(
        min_value=datetime.datetime(2000, 1, 1, 0, 0),
        max_value=datetime.datetime(4000, 12, 31, 23, 59, 59))

timedeltas = hypothesis.strategies.timedeltas(
        min_value=datetime.timedelta(**{settings.TIMESPEC: 1}),
        max_value=datetime.timedelta(days=4000*365))

async_mocks = hypothesis.strategies.builds(
        AsyncMock)

def isoformatted(dates):
    return tuple(d.isoformat(timespec=settings.TIMESPEC) for d in dates)

@hypothesis.strategies.composite
def _unsorted_list(draw):
    sequence_stop = draw(maximum_sequence_stop)
    return list(range(sequence_stop, 0 , -1))

@hypothesis.strategies.composite
def _unsorted_list_cycle(draw):
    sequence_stop = draw(maximum_sequence_stop)
    cycle_length = draw(unsorted_list_cycle_lengths)
    return tools.unsorted_lists(0, sequence_stop, cycle_length)

@hypothesis.strategies.composite
def _datetime_and_later(draw):
    start = draw(datetimes)
    later = start + draw(timedeltas)
    return start, later

@hypothesis.strategies.composite
def _database_bogo_row(draw):
    return (draw(db_indexes),
            repr(draw(_unsorted_list())),
            *isoformatted(draw(_datetime_and_later())),
            draw(natural_numbers))

@hypothesis.strategies.composite
def _database_random_state_row(draw):
    return (draw(db_indexes),
            repr(draw(hypothesis.strategies.randoms()).getstate()),
            draw(datetimes),
            draw(db_indexes))

@hypothesis.strategies.composite
def _bogo_init_args(draw):
    return (draw(db_indexes),
            draw(_unsorted_list()),
            *isoformatted(draw(_datetime_and_later())),
            draw(natural_numbers))

@hypothesis.strategies.composite
def _bogo_manager_init_args(draw):
    return (draw(_unsorted_list_cycle()),
            draw(hypothesis.strategies.integers(min_value=1)),
            draw(hypothesis.strategies.builds(MagicMock)),
            draw(hypothesis.strategies.randoms()))


unsorted_list_cycles = _unsorted_list_cycle()
database_bogo_rows = _database_bogo_row()
database_random_state_rows = _database_random_state_row()
bogo_init_arg_tuples = _bogo_init_args()
bogo_manager_init_arg_tuples = _bogo_manager_init_args()

