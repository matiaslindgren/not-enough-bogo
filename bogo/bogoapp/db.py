"""
Simple async database connections for saving and retrieving sorting state.
"""
import asyncio
import itertools
import sqlite3
import logging

import aioodbc


logger = logging.getLogger("Database")


class Database:

    def __init__(self, dsn, sql_schema_path):
        self.data_source_name = dsn
        self.sql_schema_path = sql_schema_path
        self.random_state_ids = itertools.cycle(range(1, 11))

    async def execute_sql(self, command, data=(), commit=False):
        """
        Execute an SQL command asynchronously on the database.
        If commit is given and True, commit after executing the command and return None.
        Else, do fetchall after executing the command and return the results.
        """
        dsn = self.data_source_name
        loop = asyncio.get_event_loop()
        async with aioodbc.create_pool(dsn=dsn, loop=loop) as pool:
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute(command, data)
                    if not commit:
                        return await cursor.fetchall()
                    await connection.commit()
                    return None

    def init(self):
        """
        Not async. Run and commit the SQL schema script.
        Fast forward random state ids.
        """
        logging.info("Initializing empty database.")
        database_path = self.data_source_name.split("Database=")[-1]
        connection = sqlite3.connect(database_path)
        with open(self.sql_schema_path) as schema:
            schema_source = schema.read()
        connection.executescript(schema_source)
        connection.commit()
        self.fast_forward_ids()
        logging.info("Initialized empty database.")

    def fast_forward_ids(self):
        """
        Not async. If the database contains non-null random state rows,
        fast forward the id generator to the next new value.
        """
        logging.info("Fast forwarding random state row ids.")
        loop = asyncio.get_event_loop()
        newest_random_state = loop.run_until_complete(self.newest_random_state())
        if newest_random_state and newest_random_state[1]:
            newest_id = newest_random_state[0]
            logging.debug(f"Newest random state has id {newest_id}.")
            self.random_state_ids = itertools.dropwhile(
                    lambda i: i != newest_id,
                    self.random_state_ids)
            next(self.random_state_ids)

    # TODO separate random state and bogo saving
    async def save_state(self, bogo, random_state, now):
        logging.debug(f"Writing state into database for bogo with id {bogo.db_id}.")
        row = bogo.as_database_row()
        if await self.exists(bogo):
            bogo_command = ("update bogos set "
                            "sequence=?, created=?, finished=?, shuffles=? "
                            "where id=?")
            bogo_id = row[0]
            bogo_data = (*row[1:], bogo_id)
        else:
            bogo_command = ("insert into bogos "
                            "(sequence, created, finished, shuffles) "
                            "values (?, ?, ?, ?)")
            # Drop id placeholder
            bogo_data = row[1:]
        await self.execute_sql(bogo_command, bogo_data, commit=True)
        bogo_id = (await self.newest_bogo())[0]
        if await self.exists_random_state(bogo_id):
            rand_command = ("update random set "
                            "state=?, saved=? "
                            "where bogo=?")
            rand_data = (repr(random_state), now, bogo_id)
        else:
            rand_command = ("update random set "
                            "state=?, saved=?, bogo=? "
                            "where id=?")
            next_rand_id = next(self.random_state_ids)
            rand_data = (repr(random_state), now, bogo_id, next_rand_id)
        await self.execute_sql(rand_command, rand_data, commit=True)

    async def query_and_get_first(self, query, data=()):
        results = await self.execute_sql(query, data)
        return results[0] if results else None

    async def exists_random_state(self, bogo_id):
        select_with_foreign_key = "select * from random where bogo=?"
        rand_state = await self.query_and_get_first(select_with_foreign_key, (bogo_id, ))
        return rand_state is not None

    async def bogo_by_id(self, bogo_id):
        select_with_id = "select * from bogos where id=?"
        return await self.query_and_get_first(select_with_id, (bogo_id, ))

    async def exists(self, bogo):
        return (await self.bogo_by_id(bogo.db_id)) is not None

    async def newest_bogo(self):
        select_newest = "select * from bogos order by created desc limit 1"
        return await self.query_and_get_first(select_newest)

    async def newest_random_state(self):
        select_newest = "select * from random order by saved desc limit 1"
        return await self.query_and_get_first(select_newest)

    async def newer_bogo(self, bogo):
        select_next = "select * from bogos where created > ? order by created limit 1"
        return await self.query_and_get_first(select_next, (bogo['created'], ))

    async def older_bogo(self, bogo):
        select_previous = "select * from bogos where created < ? order by created desc limit 1"
        return await self.query_and_get_first(select_previous, (bogo['created'], ))

    async def adjacent_bogos(self, bogo):
        return (await self.older_bogo(bogo),
                await self.newer_bogo(bogo))

