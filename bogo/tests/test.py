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
            datetime.timedelta(seconds=10),
            "Timedelta between the time at saving a new bogo and the time stored in the database was greater than 10 seconds."
        )


    @given(bogo_id=strategies.integers(min_value=1, max_value=SQL_MAX_INT))
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


    def _backup_and_retrieve(self, xs):
        with main.flask_app.app_context():
            main.backup_sorting_state(xs, self.random)
            return main.get_previous_state_all()


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
            datetime.timedelta(seconds=10),
            "Timedelta between the time at saving a backup and the time stored in the database was greater than 10 seconds."
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


    def test_sort_until_done_sorts_unsorted_sequence(self):
        xs = [3, 2, 1]
        with main.flask_app.app_context():
            main.sort_until_done(xs)
        self.assertTrue(is_sorted(xs), "Bogosorting did not sort the sequence.")


    def test_sort_until_done_logs_correctly(self):
        xs = [3, 2, 1]
        expected_patterns = (
            "Begin bogosorting with:",
            re.escape("sequence: {}".format(str(xs))),
            r"bogo id: \d+",
            "backup interval: {}".format(config.BACKUP_INTERVAL),
            "iter speed resolution: {}".format(config.ITER_SPEED_RESOLUTION),
            r"Done sorting bogo \d+ in \d+ iterations.",
            r"Bogo \d+ closed.",
            "Flush.*redis"
        )
        stringio = io.StringIO()
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler(stringio))
        with mock.patch("bogo.main.celery_logger", logger):
            with main.flask_app.app_context():
                main.sort_until_done(xs)
        log_string = stringio.getvalue()
        for pattern, log_line in zip(expected_patterns, log_string.splitlines()):
            self.assertRegex(log_line, pattern)



    @unittest.skip("not implemented")
    def test_bogo_main_starts_from_correct_backup(self):
        self.fail("not implemented")

    @unittest.skip("not implemented")
    def test_bogo_main_starts_from_new_sequence_if_no_backups_exit(self):
        self.fail("not implemented")

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
