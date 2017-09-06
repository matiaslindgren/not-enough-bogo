import itertools
import datetime

from bogoapp import settings


def datetime_isoformat(date):
    return date.isoformat(timespec=settings.TIMESPEC)

def isoformat_now():
    return datetime_isoformat(datetime.datetime.utcnow())

def datetime_from_isoformat(date_string):
    return datetime.datetime.strptime(date_string, settings.DATE_FORMAT)


def is_sorted(seq):
    """
    Return True if elements in the given sequence are in ascending order.
    >>> is_sorted([1, 2, 3])
    True
    >>> is_sorted([1, 20, 300])
    True
    >>> is_sorted([3, 2, 1])
    False
    >>> is_sorted([10, 2, 300])
    False
    """
    return all(seq[i-1] < seq[i] for i in range(1, len(seq)))


def fast_forward_to_length(sequences, length):
    """
    Return an itertools.dropwhile that starts from
    the first sequence that has the given length.
    >>> list(fast_forward_to_length([list(range(n)) for n in range(6)], 4))
    [[0, 1, 2, 3], [0, 1, 2, 3, 4]]
    """
    return itertools.dropwhile(lambda seq: len(seq) != length, sequences)


def unsorted_lists(min_stop, max_stop, until):
    """
    Return an itertools.cycle of lists from reversed ranges with stop between
    (incl.) min_stop and max_stop.
    If until is greater than zero, return an itertools.islice of the cycle up to until.
    Else return an unbounded generator.
    >>> cycle = unsorted_lists(2, 4, 0)
    >>> next(cycle)
    [2, 1]
    >>> next(cycle)
    [3, 2, 1]
    >>> next(cycle)
    [4, 3, 2, 1]
    >>> next(cycle)
    [2, 1]
    >>> g = unsorted_lists(2, 4, 1)
    >>> next(g)
    [2, 1]
    >>> next(g)
    Traceback (most recent call last):
    ...
    StopIteration
    """
    cycle = itertools.cycle(list(range(n, 0, -1)) for n in range(min_stop, max_stop+1))
    if until > 0:
        cycle = itertools.islice(cycle, until)
    return cycle

