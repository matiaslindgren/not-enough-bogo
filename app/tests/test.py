import unittest
import os
import flaskr
import tempfile
import main

class Test(unittest.TestCase):

    def setUp(self):
        self.db_file_desc, flaskr.app.config['DATABASE'] = tempfile.mkstemp()
        flaskr.app.config['TESTING'] = True
        self.app = flaskr.app.test_client()
        with flaskr.app.app_context():
            flaskr.init_db()

    def test_normalized_messiness(self):
        self.assertEqual(0, main.normalized_messiness([1]))

    def tearDown(self):
        os.close(self.db_file_desc)
        os.unlink(flaskr.app.config['DATABASE'])


if __name__ == "__main__":
    unittest.main(verbosity=2)
