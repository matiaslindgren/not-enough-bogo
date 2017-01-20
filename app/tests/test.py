import unittest
import os
import tempfile
import src.main as main

from hypothesis import strategies, given


class Test(unittest.TestCase):

    def setUp(self):
        self.db_file_desc, main.flask_app.config['DATABASE'] = tempfile.mkstemp()
        main.flask_app.config['TESTING'] = True
        self.app = main.flask_app.test_client()
        with main.flask_app.app_context():
            main.init_db()

    def test_normalized_messiness_sorted(self):
        for xs in (list(range(1, n)) for n in range(2, 100)):
            self.assertEqual(
                0,
                main.normalized_messiness(xs),
                "Sorted lists should have messiness equal to 0"
            )

    def test_normalized_messiness_notsorted(self):
        for xs in (list(reversed(range(1, n))) for n in range(3, 100)):
            self.assertLess(
                0,
                main.normalized_messiness(xs),
                "Reversed sorted lists should have messiness greater than 0"
            )

    def tearDown(self):
        os.close(self.db_file_desc)
        os.unlink(main.flask_app.config['DATABASE'])


if __name__ == "__main__":
    unittest.main(verbosity=2)
