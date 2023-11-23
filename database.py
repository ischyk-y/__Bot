import asyncpg


class Database:
    def __init__(self):
        self._connection_pool = None

    async def connection(self):
        if not self._connection_pool:
            try:
                self._connection_pool = await asyncpg.create_pool(
                )
            except Exception as e:
                print(e)

    async def query(self, method, query: str, *args: tuple):
        if not self._connection_pool:
            await self.connection()

        async with self._connection_pool.acquire() as connection:
            try:
                if method == 'fetchval':
                    return await connection.fetchval(query, *args)
                elif method == 'fetchrow':
                    return await connection.fetchrow(query, *args)
                elif method == 'fetch':
                    return await connection.fetch(query, *args)
                elif method == 'execute':
                    return await connection.execute(query, *args)
                elif method == 'executemany':
                    return await connection.executemany(query, *args)
            except Exception as e:
                print(query, e)
