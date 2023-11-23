import os
from dotenv import load_dotenv
import redis
from redis import ConnectionPool

load_dotenv()  # take environment variables from .env.


class RedisDatabase:
    def __init__(self):
        self.pool = ConnectionPool(
            host=os.getenv('HOST'),
            port=os.getenv('PORT'),
            username=os.getenv('USERNAME'),
            password=os.getenv('PASSWORD'),
            db=0
        )
        self.connection = redis.Redis(connection_pool=self.pool)

    def hset(self, key, *args, **kwargs):
        return self.connection.hset(key, *args, **kwargs)

    def expire(self, key, ttl):
        return self.connection.expire(key, ttl)

    def get(self, key):
        return self.connection.get(key)

    def set(self, key, value, **kwargs):
        return self.connection.set(key, value, **kwargs)

    def keys(self, pattern):
        return self.connection.keys(pattern)

    def hget(self, key, field):
        return self.connection.hget(key, field)

    def hmget(self, key, *args):
        return self.connection.hmget(key, *args)

    def hkeys(self, key):
        return self.connection.hkeys(key)
