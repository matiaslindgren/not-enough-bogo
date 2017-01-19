import unittest
import os
import tempfile
import src.main as main


class Test(unittest.TestCase):

    def setUp(self):
        self.db_file_desc, main.flask_app.config['DATABASE'] = tempfile.mkstemp()
        main.flask_app.config['TESTING'] = True
        self.app = main.flask_app.test_client()
        with main.flask_app.app_context():
            main.init_db()

    def test_normalized_messiness(self):
        self.assertEqual(0, main.normalized_messiness([1]))

    def tearDown(self):
        os.close(self.db_file_desc)
        os.unlink(main.flask_app.config['DATABASE'])


if __name__ == "__main__":
    unittest.main(verbosity=2)
