import asyncio
import unittest
import unittest.mock as mock

import hypothesis
import uvloop

from bogoapp.bogo_manager import BogoManager


def AsyncMock(*args, **kwargs):
    """https://blog.miguelgrinberg.com/post/unit-testing-asyncio-code"""
    m = mock.MagicMock(*args, **kwargs)

    async def mock_coro(*args, **kwargs):
        return m(*args, **kwargs)

    mock_coro.mock = m
    return mock_coro


class TestBogoManager(unittest.TestCase):

    def setUp(self):
        self.loop = uvloop.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def test_load_previous_state(self):
        pass

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

