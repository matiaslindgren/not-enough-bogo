"""
Tests written using the property based testing library hypothesis.
"""
import unittest
import unittest.mock as mock
import fakeredis
import werkzeug
from hypothesis import strategies, given, settings, assume
import random
import os
import ast

import re
import io
import tempfile
import logging

import datetime
import dateutil.parser as date_parser

import bogo.main as main
import bogo.config as config


settings.register_profile('dev', settings(max_examples=10))
settings.register_profile('ci', settings(max_examples=500))
settings.load_profile(os.getenv(u'HYPOTHESIS_PROFILE', default='dev'))


def is_sorted(xs):
    return all(xs[i-1] < xs[i] for i in range(1, len(xs)))

@strategies.composite
def _integer_and_less(draw):
    n = draw(strategies.integers(min_value=1, max_value=20))
    i = draw(strategies.integers(min_value=1, max_value=n))
    return (n, i)


mock_redis_app = fakeredis.FakeStrictRedis(
    host="localhost",
    port=config.REDIS_PORT,
    db=0,
    decode_responses=config.REDIS_DECODE_RESPONSES
)

@mock.patch('bogo.main.redis_app', mock_redis_app)
class Test(unittest.TestCase):

    # range(1, n) instances where 2 <= n <= 3000 is random
    RANGE_FROM_ONE = strategies.builds(
            lambda n: range(1, n),
            strategies.integers(min_value=2, max_value=3000))
    # list instances from above ranges
    LIST_RANGE_INTEGERS_SORTED = RANGE_FROM_ONE.map(list)
    # random.sample lists using above ranges as population and size
    LIST_RANGE_INTEGERS_SHUFFLED = RANGE_FROM_ONE.map(lambda rng: random.sample(rng, len(rng)))
    # [1, 2, 3] instances with elements in random order
    LIST_THREE_INTEGERS_SHUFFLED = strategies.builds(lambda: random.sample(range(1, 4), 3))
    # Infinite iterator of above shuffled lists
    STREAM_LIST_RANGE_INTEGERS = strategies.streaming(LIST_RANGE_INTEGERS_SHUFFLED)

    SQL_MAX_INT = 2**63-1
    DATABASE_ID_INTEGERS = strategies.integers(min_value=1, max_value=SQL_MAX_INT)

    def setUp(self):
        self.db_file_desc, main.flask_app.config['DATABASE'] = tempfile.mkstemp()
        main.flask_app.config['TESTING'] = True
        self.app = main.flask_app.test_client()
        with main.flask_app.app_context():
            main.init_db()

        # Ensure 2 different test cases never use a shared state of
        # the global random module
        self.random = random.Random()


    def _insert_bogo(self, xs):
        with main.flask_app.app_context():
            db = main.get_db()
            insert_query = "insert into bogos (sequence_length, started) values (?, ?)"
            db.execute(insert_query, (len(xs), datetime.datetime.utcnow()))
            db.commit()

    def _backup_and_retrieve(self, xs):
        with main.flask_app.app_context():
            main.backup_sorting_state(xs, self.random)
            return main.get_previous_state_all()

    def _get_stringio_logger(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        stringio = io.StringIO()
        logger.addHandler(logging.StreamHandler(stringio))
        return logger, stringio

    def _assertFunctionLogs(self, function, args, logger_name, patterns):
        mock_logger, stringio = self._get_stringio_logger()

        with mock.patch(logger_name, mock_logger):
            with main.flask_app.app_context():
                function(*args)

        stringio.seek(0)
        for log_line, pattern in zip(stringio, patterns):
            self.assertRegex(log_line, pattern)

    def _get_newest_bogo(self):
        with main.flask_app.app_context():
            db = main.get_db()
            fetch_query = "select * from bogos order by started desc"
            return db.execute(fetch_query).fetchone()

    def _get_newest_backup(self):
        with main.flask_app.app_context():
            db = main.get_db()
            fetch_query = "select * from backups order by saved desc"
            return db.execute(fetch_query).fetchone()


    @given(xs=LIST_RANGE_INTEGERS_SORTED)
    def test_normalized_messiness_sorted(self, xs):
        with main.flask_app.app_context():
            self.assertEqual(
                0,
                main.normalized_messiness(xs),
                "Sorted lists should have a messiness equal to 0"
            )


    @given(xs=LIST_RANGE_INTEGERS_SHUFFLED)
    def test_normalized_messiness_notsorted(self, xs):
        self.random.shuffle(xs)
        assume(not is_sorted(xs))
        with main.flask_app.app_context():
            self.assertLess(
                0,
                main.normalized_messiness(xs),
                "Lists which are not sorted should have a messiness greater than 0"
            )


    @given(xs=LIST_RANGE_INTEGERS_SHUFFLED)
    def test_create_new_bogo(self, xs):
        before_insert = datetime.datetime.utcnow()
        with main.flask_app.app_context():
            bogo_id = main.create_new_bogo(xs)
            db = main.get_db()
            fetch_query = "select * from bogos where id=?"
            bogo = db.execute(fetch_query, (bogo_id, )).fetchone()

        self.assertEqual(
            bogo['id'],
            bogo_id,
            "Mismatched id's after bogo insert"
        )
        self.assertEqual(
            bogo['sequence_length'],
            len(xs),
            "Length of actual sequence differs from the length in the database."
        )
        db_date = date_parser.parse(bogo['started'])
        time_delta = db_date - before_insert
        self.assertLess(
            time_delta,
            datetime.timedelta(seconds=5),
            "Timedelta between the time at saving a new bogo and the time stored in the database was greater than 5 seconds."
        )

        redis_key_not_set_msg = "create_new_bogo did not update the redis cache."
        with main.flask_app.app_context():
            self.assertEqual(
                str(bogo_id),
                main.redis_app.get("active_bogo_id"),
                redis_key_not_set_msg
            )
            self.assertEqual(
                str(len(xs)),
                main.redis_app.get("sequence_length"),
                redis_key_not_set_msg
            )
            self.assertEqual(
                db_date.isoformat(),
                main.redis_app.get("start_date"),
                redis_key_not_set_msg
            )
            self.assertEqual(
                "0",
                main.redis_app.get("iter_speed"),
                redis_key_not_set_msg
            )



    @given(bogo_id=DATABASE_ID_INTEGERS)
    def test_close_non_existing_bogo(self, bogo_id):
        with main.flask_app.app_context():
            with self.assertRaises(RuntimeError, msg="Closing a bogo with a non-existing id should raise a RuntimeError."):
                main.close_bogo(bogo_id)


    @given(xs=LIST_RANGE_INTEGERS_SORTED)
    def test_close_already_closed_bogo(self, xs):
        with main.flask_app.app_context():
            bogo_id = main.create_new_bogo(xs)
            main.close_bogo(bogo_id)
            with self.assertRaises(RuntimeError, msg="Closing a bogo which has a finished date should raise a RuntimeError."):
                main.close_bogo(bogo_id)


    @given(xs=LIST_RANGE_INTEGERS_SHUFFLED)
    def test_close_open_bogo(self, xs):
        before_insert = datetime.datetime.utcnow()
        with main.flask_app.app_context():
            bogo_id = main.create_new_bogo(xs)
            main.close_bogo(bogo_id)
            db = main.get_db()
            fetch_query = "select * from bogos where id=?"
            bogo = db.execute(fetch_query, (bogo_id, )).fetchone()
        after_close = datetime.datetime.utcnow()

        self.assertIsNotNone(
            bogo['finished'],
            "Closing a bogo should update the finished field."
        )

        db_started = date_parser.parse(bogo['started'])
        db_finished = date_parser.parse(bogo['finished'])

        total_delta = after_close - before_insert
        db_delta = db_finished - db_started

        self.assertLess(
            db_delta,
            total_delta,
            "After closing an inserted bogo, the timedelta between the start time {} and the finished time {} was greater than the timedelta before calling insert {} and the time after calling close {}."
            .format(bogo['started'], bogo['finished'], before_insert.isoformat(), after_close.isoformat())
        )


    @given(xs=LIST_RANGE_INTEGERS_SHUFFLED)
    def test_backup_sorting_state_sequence_is_intact(self, xs):
        backup = self._backup_and_retrieve(xs)
        self.assertListEqual(
            ast.literal_eval(backup['sequence']),
            xs,
            "The sequence stored as a backup was different when returned from the database."
        )


    @given(xs=LIST_RANGE_INTEGERS_SHUFFLED)
    def test_backup_sorting_state_date_is_sane(self, xs):
        before_insert = datetime.datetime.utcnow()
        backup = self._backup_and_retrieve(xs)
        time_delta = date_parser.parse(backup['saved']) - before_insert
        self.assertLess(
            time_delta,
            datetime.timedelta(seconds=5),
            "Timedelta between the time at saving a backup and the time stored in the database was greater than 5 seconds."
        )


    @given(xs=LIST_RANGE_INTEGERS_SHUFFLED)
    def test_backup_sorting_state_when_random_not_altered(self, xs):
        self.random.seed(config.RANDOM_SEED)
        random_state_before = self.random.getstate()
        backup = self._backup_and_retrieve(xs)
        random_state_db = ast.literal_eval(backup['random_state'])
        self.assertEqual(
            random_state_before,
            random_state_db,
            "The random state returned by the database has is different even though the state of the random module was not changed."
        )


    @given(xs=LIST_RANGE_INTEGERS_SHUFFLED,
           state_change_count=strategies.integers(min_value=0, max_value=10000))
    def test_backup_random_state_preserves_the_pseudorandom_sequence(self, xs, state_change_count):
        self.random.seed(config.RANDOM_SEED)
        for _ in range(state_change_count):
            self.random.random()

        backup = self._backup_and_retrieve(xs)
        random_state_db = ast.literal_eval(backup['random_state'])

        expected_random_sequence = [self.random.random() for _ in range(state_change_count)]
        self.random.setstate(random_state_db)
        from_db_random_sequence = (self.random.random() for _ in range(state_change_count))

        for expected, from_db in zip(expected_random_sequence, from_db_random_sequence):
            self.assertAlmostEqual(
                from_db,
                expected,
                7,
                "The sequence of pseudorandom floats was different when the state was reloaded from the db."
            )


    @given(xs=LIST_THREE_INTEGERS_SHUFFLED)
    def test_sort_until_done_sorts_unsorted_sequence(self, xs):
        with main.flask_app.app_context():
            main.sort_until_done(xs)
        self.assertTrue(is_sorted(xs), "Bogosorting did not sort the sequence.")


    @given(xs=LIST_THREE_INTEGERS_SHUFFLED)
    def test_sort_until_done_logs_correctly(self, xs):
        expected_patterns = (
            r"^Writing backup for bogo \d+",
            "^Begin bogosorting with:",
            re.escape("sequence: {}".format(str(xs))),
            r"^bogo id: \d+",
            "^backup interval: {}".format(config.BACKUP_INTERVAL),
            "^iter speed resolution: {}".format(config.ITER_SPEED_RESOLUTION),
            r"^Done sorting bogo \d+ in \d+ iterations.",
            r"^Bogo \d+ closed.",
            "^Flush.*redis"
        )

        self._assertFunctionLogs(
            main.sort_until_done,
            (xs, ),
            logger_name="bogo.main.celery_logger",
            patterns=expected_patterns
        )

    @given(xs=LIST_THREE_INTEGERS_SHUFFLED)
    def test_sort_until_done_creates_a_new_bogo(self, xs):
        newest_before = self._get_newest_bogo()

        with main.flask_app.app_context():
            main.sort_until_done(xs)

        newest_after = self._get_newest_bogo()

        self.assertIsNotNone(
            newest_after,
            "sort_until_done did not insert a new bogo."
        )
        if newest_before:
            self.assertNotEqual(
                newest_before['id'],
                newest_after['id'],
                "sort_until_done did not insert a new bogo."
            )

    @given(xs=LIST_THREE_INTEGERS_SHUFFLED)
    def test_sort_until_done_creates_a_backup(self, xs):
        date_before = datetime.datetime.utcnow()

        with mock.patch("bogo.main.bogo_random", self.random):
            self.random.seed(config.RANDOM_SEED)
            random_state_before = self.random.getstate()
            with main.flask_app.app_context():
                main.sort_until_done(xs)

        newest_backup_after = self._get_newest_backup()

        self.assertIsNotNone(
            newest_backup_after,
            "sort_until_done did not create a backup."
        )
        self.assertTupleEqual(
            ast.literal_eval(newest_backup_after['random_state']),
            random_state_before,
            "sort_until_done saved a backup but the random state was not the same as before saving the backup."
        )
        self.assertLess(
            date_parser.parse(newest_backup_after['saved']) - date_before,
            datetime.timedelta(seconds=5),
            "The timedelta of right before calling sort_until_done, compared to the saved date in the newest backup was greater than 5 seconds."
        )

    @given(xs=LIST_THREE_INTEGERS_SHUFFLED)
    def test_sort_until_done_closes_the_created_bogo(self, xs):
        before_sort = datetime.datetime.utcnow()
        with main.flask_app.app_context():
            main.sort_until_done(xs)

        newest_bogo = self._get_newest_bogo()
        finished_date = newest_bogo['finished']

        self.assertIsNotNone(
            finished_date,
            "After sort_until_done, the newest bogo should be closed."
        )

        self.assertLess(
            date_parser.parse(finished_date) - before_sort,
            datetime.timedelta(seconds=5),
            "Timedelta between the time at starting sort_until_done the time it was finished was greater than 5 seconds (when the sequence being sorted was of length {}).".format(len(xs))
        )



    @mock.patch("bogo.config.SEQUENCE_MAX_LENGTH", 3)
    @mock.patch("bogo.config.SEQUENCE_STEP", 3)
    def test_bogo_main_initializes_from_config(self):
        mock_step = mock_max_length = 3
        expected_seq = [3, 2, 1]
        expected_patterns = (
            "^Initializing bogo_main with:",
            "sequence step: {}".format(mock_step),
            "last sequence length: {}".format(mock_max_length),
            "backups? found",
            "^" + re.escape("Call sort_until_done with: {}".format(expected_seq))
        )
        self._assertFunctionLogs(
            main.bogo_main,
            (),
            logger_name="bogo.main.celery_logger",
            patterns=expected_patterns
        )


    @mock.patch("bogo.config.SEQUENCE_MAX_LENGTH", 3)
    @mock.patch("bogo.config.SEQUENCE_STEP", 3)
    def test_bogo_main_starts_from_new_sequence_if_no_backups_exist(self):
        expected_seq = [3, 2, 1]
        expected_patterns = (
            "^.",
            "^.",
            "^.",
            "^No backups found, starting a new bogo cycle.",
            "^" + re.escape("Call sort_until_done with: {}".format(expected_seq))
        )
        self._assertFunctionLogs(
            main.bogo_main,
            (),
            logger_name="bogo.main.celery_logger",
            patterns=expected_patterns
        )


    @mock.patch("bogo.config.SEQUENCE_MAX_LENGTH", 3)
    @mock.patch("bogo.config.SEQUENCE_STEP", 3)
    @given(xs=LIST_THREE_INTEGERS_SHUFFLED)
    def test_bogo_main_starts_from_correct_backup(self, xs):
        self._insert_bogo(xs)
        backup = self._backup_and_retrieve(xs)
        backup_seq = ast.literal_eval(backup['sequence'])
        expected_patterns = (
            "^.",
            "^.",
            "^.",
            "^" + re.escape("Previous backup found, seq of len {}".format(len(backup_seq))),
            "^" + re.escape("Resuming sorting with backup: {}".format(backup_seq))
        )
        self._assertFunctionLogs(
            main.bogo_main,
            (),
            logger_name="bogo.main.celery_logger",
            patterns=expected_patterns
        )


    @given(xs_stream=STREAM_LIST_RANGE_INTEGERS,
           count_and_id=_integer_and_less())
    def test_get_adjacent_bogos(self, xs_stream, count_and_id):
        list_count, bogo_id = count_and_id
        for i, xs in enumerate(xs_stream):
            if i >= list_count:
                break
            self._insert_bogo(xs)

        with main.flask_app.app_context():
            this_bogo = main.get_bogo_by_id_or_404(bogo_id)
            prev_bogo, this_bogo, next_bogo = main.get_adjacent_bogos(this_bogo)

        self.assertIsNotNone(
            this_bogo,
            "get_adjacent_bogos should return the bogo given as parameter when it exists."
        )
        if prev_bogo:
            self.assertLess(
                prev_bogo['started'],
                this_bogo['started'],
                "Previous bogo should not be started after this bogo."
            )
        if next_bogo:
            self.assertLess(
                this_bogo['started'],
                next_bogo['started'],
                "Next bogo should not be started before this bogo."
            )

        # Hypothesis runs examples on same test case instance
        self.tearDown()
        self.setUp()


    def test_index_route_redirects(self):
        with main.flask_app.app_context():
            response = self.app.get('/')
            self.assertEqual(
                response.status_code,
                302,
                "Index should redirect"
            )


    @given(bogo_id=DATABASE_ID_INTEGERS)
    def test_nonexisting_route_responds_404(self, bogo_id):
        with main.flask_app.app_context():
            response = self.app.get('/bogo/{:d}'.format(bogo_id))
            self.assertEqual(
                response.status_code,
                404,
                "Getting path with bogo key when the database is empty should 404."
            )


    @given(bogo_id=DATABASE_ID_INTEGERS)
    def test_get_bogo_by_id_or_404_with_nonexisting_id_throws_404(self, bogo_id):
        with main.flask_app.app_context():
            with self.assertRaisesRegex(werkzeug.exceptions.NotFound, "404"):
                main.get_bogo_by_id_or_404(bogo_id)


    @unittest.skip("not implemented")
    def test_bogo_starts_on_command(self):
        self.fail("not implemented")

    @unittest.skip("not implemented")
    def test_bogo_stops_on_command(self):
        self.fail("not implemented")

    @unittest.skip("not implemented")
    def test_get_stats_returns_active_bogo(self):
        self.fail("not implemented")

    @unittest.skip("not implemented")
    def test_get_stats_returns_nonactive_bogo(self):
        self.fail("not implemented")



    def tearDown(self):
        os.close(self.db_file_desc)
        os.unlink(main.flask_app.config['DATABASE'])


if __name__ == "__main__":
    unittest.main(verbosity=2)
