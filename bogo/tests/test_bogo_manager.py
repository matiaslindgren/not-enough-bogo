import asyncio
import unittest
import unittest.mock as mock

import hypothesis
import uvloop

from . import strategies

from bogoapp.bogo_manager import BogoManager, BogoError


def AsyncMock(*args, **kwargs):
    """https://blog.miguelgrinberg.com/post/unit-testing-asyncio-code"""
    m = mock.MagicMock(*args, **kwargs)

    async def mock_coro(*args, **kwargs):
        return m(*args, **kwargs)

    mock_coro.mock = m
    return mock_coro


class TestBogoManager(unittest.TestCase):

    timeout = 5

    def setUp(self):
        self.loop = uvloop.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _run(self, f):
        self.assertTrue(asyncio.iscoroutinefunction(f),
                        "Expected a coroutine function but instead got {}"
                        .format(repr(f)))
        return self.loop.run_until_complete(f())

    # TODO move this monster to custom strategies as a BogoManager strategy
    @hypothesis.settings(max_examples=100)
    @hypothesis.given(bogo_row=strategies.database_bogo_rows,
                      unsorted_list_cycle=strategies.unsorted_list_cycles,
                      speed_resolution=hypothesis.strategies.integers(min_value=1),
                      mock_database=hypothesis.strategies.builds(mock.MagicMock),
                      random_module=hypothesis.strategies.randoms(),
                      async_mock=hypothesis.strategies.builds(AsyncMock))
    def test_load_previous_state(self,
                                 bogo_row,
                                 unsorted_list_cycle,
                                 speed_resolution,
                                 mock_database,
                                 random_module,
                                 async_mock):
        async def load_previous_state():
            return await self.bogo_manager.load_previous_state()
        self.bogo_manager = BogoManager(unsorted_list_cycle,
                                        speed_resolution,
                                        mock_database,
                                        random_module)
        async_mock.mock.return_value = None
        self.bogo_manager.database.newest_bogo = async_mock
        newest_bogo = self._run(load_previous_state)
        self.assertIsNone(newest_bogo,
                          "Without a bogo in the database, load_previous_state should "
                          "return None, not {}."
                          .format(repr(newest_bogo)))

        async_mock.mock.return_value = bogo_row
        self.bogo_manager.database.newest_random_state = async_mock
        with self.assertRaises(BogoError, msg="If the database contains a bogo "
                                              "but no previous random state, "
                                              "it should be an error."):
            newest_bogo = self._run(load_previous_state)

        # TODO bogo id and random state id not equal
        # TODO random module state is set
        # TODO bogo is returned

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

