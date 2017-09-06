"""
Fear and loathing.
"""
import asyncio
import ast
import datetime
import random
import time
import logging

from bogoapp import seqtools
from bogoapp import settings


logger = logging.getLogger("BogoManager")


def datetime_isoformat(date):
    return date.isoformat(timespec='milliseconds')

def isoformat_now():
    return datetime_isoformat(datetime.datetime.utcnow())

def datetime_from_isoformat(date_string):
    return datetime.datetime.strptime(date_string, settings.DATE_FORMAT)


class BogoError(Exception):
    pass


class Bogo:
    """
    Encapsulates bogosorting state for a single sequence and is also a crappy ORM.
    Considered finished when its sequence is sorted.
    """
    def __init__(self,
                 db_id=None,
                 sequence=None,
                 created=None,
                 finished=None,
                 shuffles=0):
        self.db_id = db_id
        self.sequence = sequence
        self.created = created
        self.finished = finished
        self.shuffles = shuffles

    @classmethod
    def from_database_row(cls, row):
        sequence = ast.literal_eval(row[1])
        return cls(row[0], sequence, *row[2:])

    def as_database_row(self):
        return (self.db_id,
                repr(self.sequence),
                self.created,
                self.finished,
                self.shuffles)

    def shuffle_with(self, shuffle):
        shuffle(self.sequence)
        self.shuffles += 1

    def is_finished(self):
        return bool(self.finished or seqtools.is_sorted(self.sequence))

    def __repr__(self):
        return "<class 'Bogo' with sequence: {}>".format(repr(self.sequence))


class BogoManager:
    """
    Manages all state related to bogosorting a sequence of lists.
    """
    def __init__(self,
                 min_stop,
                 max_stop,
                 sort_limit,
                 speed_resolution,
                 database,
                 seed):
        if speed_resolution <= 0:
            raise BogoError("Invalid speed resolution, "
                            "N shuffles per {} seconds doesn't make sense."
                            .format(speed_resolution))
        self.current_bogo = None
        self.random = random.Random()
        self.random.seed(seed)
        self.min_stop = min_stop
        self.max_stop = max_stop
        self.unsorted_lists = seqtools.unsorted_lists(
                min_stop, max_stop, sort_limit)
        self.speed_resolution = speed_resolution
        self.shuffling_speed = 0
        self.database = database
        self.stopping = False
        self.task = None

    async def load_previous_state(self):
        logging.info("Loading previous state.")
        bogo_row = await self.database.newest_bogo()
        if not bogo_row:
            logging.info("No previous bogo found.")
            return None
        bogo = Bogo.from_database_row(bogo_row)
        random_state_row = await self.database.newest_random_state()
        if not random_state_row:
            raise BogoError("Improperly saved random state "
                            f"Found newest bogo with id {bogo.db_id} "
                            "but no previous random state was found.")
        random_state_bogo_id = random_state_row[3]
        if bogo.db_id != random_state_bogo_id:
            raise BogoError("Improperly saved random state, "
                            f"newest bogo has id {bogo.db_id} "
                            "but newest random state has a reference "
                            f"to a bogo with id {random_state_bogo_id}.")
        logging.info("Setting random state.")
        self.random.setstate(ast.literal_eval(random_state_row[1]))
        logging.info(f"Returning previous bogo {bogo}")
        return bogo

    async def save_state(self, now):
        logging.debug("Saving state.")
        random_state = self.random.getstate()
        await self.database.save_state(self.current_bogo, random_state, now)

    async def make_next_bogo(self, sequence):
        logging.debug(f"Making new bogo from sequence {sequence}.")
        now = isoformat_now()
        self.current_bogo = Bogo(sequence=sequence, created=now)
        await self.save_state(now=now)
        self.current_bogo.db_id = (await self.database.newest_bogo())[0]

    async def sort_current_until_done(self):
        """Bogosort the current sequence until it is sorted."""
        logging.debug("Sorting current bogo until done.")
        delta_iterations = 0
        delta_seconds = 0.0
        while not (self.current_bogo.is_finished() or self.stopping):
            await asyncio.sleep(0)
            perf_counter_start = time.perf_counter()
            self.current_bogo.shuffle_with(self.random.shuffle)
            delta_iterations += 1
            delta_seconds += time.perf_counter() - perf_counter_start
            if delta_seconds >= self.speed_resolution:
                self.shuffling_speed = round(delta_iterations/self.speed_resolution)
                delta_iterations = 0
                delta_seconds = 0.0
        logging.debug("Stopped sorting bogo.")
        now = isoformat_now()
        if self.current_bogo.is_finished():
            logging.debug("Bogo was sorted")
            self.current_bogo.finished = now
        else:
            logging.debug("Bogo was not sorted")
        await self.save_state(now)

    async def sort_all(self):
        logging.debug("Sorting all unsorted lists.")
        for lst in self.unsorted_lists:
            if self.stopping:
                logging.info("Stopping sorting all unsorted lists.")
                break
            await self.make_next_bogo(lst)
            await self.sort_current_until_done()

    async def run(self):
        logging.info("Running BogoManager.")
        previous_bogo = await self.load_previous_state()
        if previous_bogo and not previous_bogo.is_finished():
            logging.info("Found unfinished previous bogo.")
            unfinished_length = len(previous_bogo.sequence)
            if unfinished_length > self.max_stop:
                raise BogoError("Invalid BogoManager configuration, "
                                "previous unfinished bogo sequence has "
                                f"length {unfinished_length} "
                                "while the list generator will generate lists "
                                f"of maximum length {self.max_stop}.")
            self.unsorted_lists = seqtools.fast_forward_to_length(
                    self.unsorted_lists, unfinished_length)
            # Drop next list since it has the same length as the sequence in
            # the unfinished previous_bogo.
            next(self.unsorted_lists)
            self.current_bogo = previous_bogo
            await self.sort_current_until_done()
        else:
            logging.info("Did not find an unfinished previous bogo.")
        await self.sort_all()

    def get_current_state(self):
        return {"sequence":        self.current_bogo.sequence,
                "shuffles":        self.current_bogo.shuffles,
                "created":         self.current_bogo.created,
                "finished":        self.current_bogo.finished,
                "shuffling_speed": self.shuffling_speed}


