import ast
import asyncio
import unittest

import hypothesis
import uvloop

from . import strategies

from bogoapp.bogo import Bogo
from bogoapp.bogo_manager import BogoManager, BogoError


class TestBogoManager(unittest.TestCase):

    def setUp(self):
        self.loop = uvloop.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _run_in_loop(self, f):
        self.assertTrue(asyncio.iscoroutinefunction(f),
                        "Expected a coroutine function but instead got {}"
                        .format(repr(f)))
        return self.loop.run_until_complete(f())

    @hypothesis.given(init_args=strategies.bogo_manager_init_arg_tuples,
                      newest_bogo_mock=strategies.async_mocks)
    def test_load_previous_state_empty_db(self, init_args, newest_bogo_mock):
        """
        Loading the newest state from an empty database fails silently.
        """
        self.bogo_manager = BogoManager(*init_args)
        newest_bogo_mock.mock.return_value = None
        self.bogo_manager.database.newest_bogo = newest_bogo_mock
        newest_bogo = self._run_in_loop(self.bogo_manager.load_previous_state)
        self.assertIsNone(newest_bogo,
                          "Without a bogo in the database, load_previous_state should "
                          "return None, not {}."
                          .format(repr(newest_bogo)))

    @hypothesis.given(init_args=strategies.bogo_manager_init_arg_tuples,
                      bogo_row=strategies.database_bogo_rows,
                      newest_bogo_mock=strategies.async_mocks,
                      newest_random_mock=strategies.async_mocks)
    def test_load_previous_state_bogo_but_no_random(
            self, init_args, bogo_row, newest_bogo_mock, newest_random_mock):
        """
        Loading the newest state containing a sorting state but no random module state is an error.
        """
        self.bogo_manager = BogoManager(*init_args)
        newest_bogo_mock.mock.return_value = bogo_row
        self.bogo_manager.database.newest_bogo = newest_bogo_mock
        newest_random_mock.mock.return_value = None
        self.bogo_manager.database.newest_random_state = newest_random_mock
        with self.assertRaises(BogoError, msg="If the database contains a bogo "
                                              "but no previous random state, "
                                              "it should be an error."):
            self._run_in_loop(self.bogo_manager.load_previous_state)

    @hypothesis.given(init_args=strategies.bogo_manager_init_arg_tuples,
                      bogo_row=strategies.database_bogo_rows,
                      random_row=strategies.database_random_state_rows,
                      newest_bogo_mock=strategies.async_mocks,
                      newest_random_mock=strategies.async_mocks)
    def test_load_previous_state_bogo_foreign_key_mismatch(
            self, init_args, bogo_row, random_row, newest_bogo_mock, newest_random_mock):
        """
        Loading the newest state containing a random module state with an mismatched reference id to the newest sorting state is an error.
        """
        hypothesis.assume(bogo_row[0] != random_row[3])
        self.bogo_manager = BogoManager(*init_args)
        newest_bogo_mock.mock.return_value = bogo_row
        self.bogo_manager.database.newest_bogo = newest_bogo_mock
        newest_random_mock.mock.return_value = random_row
        self.bogo_manager.database.newest_random_state = newest_random_mock
        with self.assertRaises(BogoError, msg="The newest random state should "
                                              "always contain a reference to "
                                              "the newest bogo."):
            self._run_in_loop(self.bogo_manager.load_previous_state)

    @hypothesis.given(init_args=strategies.bogo_manager_init_arg_tuples,
                      bogo_row=strategies.database_bogo_rows,
                      random_row=strategies.database_random_state_rows,
                      newest_bogo_mock=strategies.async_mocks,
                      newest_random_mock=strategies.async_mocks)
    def test_load_previous_state_successful(
            self, init_args, bogo_row, random_row, newest_bogo_mock, newest_random_mock):
        """
        Loading the newest state from a correctly saved database initializes the BogoManager instance with the loaded state.
        """
        hypothesis.assume(random_row[3] == bogo_row[0])
        random_module_state = ast.literal_eval(random_row[1])
        self.bogo_manager = BogoManager(*init_args)
        newest_bogo_mock.mock.return_value = bogo_row
        self.bogo_manager.database.newest_bogo = newest_bogo_mock
        newest_random_mock.mock.return_value = random_row
        self.bogo_manager.database.newest_random_state = newest_random_mock
        newest_bogo = self._run_in_loop(self.bogo_manager.load_previous_state)
        self.assertIsInstance(newest_bogo, Bogo, "load_previous_state should build "
                                                 "a Bogo instance when state loading "
                                                 "is successful.")
        msg = "load_previous_state returned an incorrectly initialized Bogo instance."
        self.assertEqual(newest_bogo.db_id, bogo_row[0], msg)
        self.assertEqual(newest_bogo.sequence, ast.literal_eval(bogo_row[1]), msg)
        self.assertEqual(newest_bogo.created, bogo_row[2], msg)
        self.assertEqual(newest_bogo.finished, bogo_row[3], msg)
        self.assertEqual(newest_bogo.shuffles, bogo_row[4], msg)
        self.assertEqual(self.bogo_manager.random.getstate(),
                         random_module_state,
                         "load_previous_state should initialize the state "
                         "of the random module from the retrieved random state "
                         "database row.")


    def test_save_state(self):
        pass

    def test_make_next_bogo(self):
        pass

    def test_sort_current_until_done(self):
        pass

    def test_sort_all(self):
        pass

    def test_run(self):
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)

