import asyncio
import unittest

import uvloop


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

