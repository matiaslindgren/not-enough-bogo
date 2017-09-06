import unittest
import datetime
import hypothesis

from . import strategies
from . import conftest

from bogoapp import bogo
from bogoapp import tools


class TestDateHelpers(unittest.TestCase):

    def test_now_string_is_recent(self):
        for _ in range(1000):
            now = datetime.datetime.utcnow()
            now_string = tools.isoformat_now()
            now_from_string = tools.datetime_from_isoformat(now_string)

            self.assertIsInstance(
                    now_from_string,
                    datetime.datetime,
                    "Expected datetime_from_isoformat to return a datetime instance from "
                    "the given string")
            self.assertLessEqual(
                    now_from_string - now,
                    datetime.timedelta(milliseconds=1),
                    "The date helpers should return datetimes which are now.")


class TestBogo(unittest.TestCase):

    @hypothesis.given(row=strategies.database_bogo_rows)
    def test_build_bogo_from_database_row(self, row):
        bogo_obj = bogo.Bogo.from_database_row(row)

        self.assertEqual(bogo_obj.db_id, row[0])
        self.assertIsInstance(bogo_obj.sequence, list)
        self.assertEqual(repr(bogo_obj.sequence), row[1])
        self.assertEqual(bogo_obj.created, row[2])
        self.assertEqual(bogo_obj.finished, row[3])
        self.assertLess(tools.datetime_from_isoformat(bogo_obj.created),
                        tools.datetime_from_isoformat(bogo_obj.finished))
        self.assertEqual(bogo_obj.shuffles, row[4])
        self.assertGreaterEqual(bogo_obj.shuffles, 0)

    @hypothesis.given(init_args=strategies.bogo_init_arg_tuples)
    def test_bogo_as_database_row(self, init_args):
        bogo_obj = bogo.Bogo(*init_args)
        bogo_row = bogo_obj.as_database_row()
        expected_row = (init_args[0], repr(init_args[1]), *init_args[2:])

        self.assertTupleEqual(bogo_row, expected_row)

    @hypothesis.given(init_args=strategies.bogo_init_arg_tuples,
                      random=hypothesis.strategies.randoms())
    def test_bogo_shuffle(self, init_args, random):
        bogo_obj = bogo.Bogo(*init_args)
        shuffles_start = bogo_obj.shuffles
        random_state = random.getstate()

        bogo_obj.shuffle_with(random.shuffle)

        self.assertEqual(bogo_obj.shuffles - 1,
                         shuffles_start)
        self.assertNotEqual(repr(random.getstate()), repr(random_state))

    @hypothesis.given(init_args=strategies.bogo_init_arg_tuples)
    def test_bogo_is_finished(self, init_args):
        hypothesis.assume(not tools.is_sorted(init_args[1]))
        bogo_obj = bogo.Bogo(*init_args)
        finished, bogo_obj.finished = bogo_obj.finished, None
        self.assertFalse(bogo_obj.is_finished())

        bogo_obj.finished = finished
        self.assertTrue(bogo_obj.is_finished())

        bogo_obj.finished = None
        bogo_obj.sequence.sort()
        self.assertTrue(bogo_obj.is_finished())

        bogo_obj.finished = finished
        self.assertTrue(bogo_obj.is_finished())


if __name__ == "__main__":
    unittest.main(verbosity=2)

