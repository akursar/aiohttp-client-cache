import pickle
from typing import Iterable, Optional

from gridfs import GridFS
from pymongo import MongoClient

from aiohttp_client_cache.backends import BaseCache, CacheController, ResponseOrKey
from aiohttp_client_cache.backends.mongo import MongoDBCache


class GridFSController(CacheController):
    """GridFS cache backend.
    Use MongoDB GridFS to support documents greater than 16MB.
    """

    def __init__(self, cache_name: str, *args, connection: MongoClient = None, **kwargs):
        super().__init__(cache_name, *args, **kwargs)
        self.responses = GridFSCache(cache_name, connection)
        self.keys_map = MongoDBCache(cache_name, 'http_redirects', self.responses.connection)


# TODO: Incomplete/untested
class GridFSCache(BaseCache):
    """A dictionary-like interface for MongoDB GridFS"""

    def __init__(self, db_name, connection: MongoClient = None):
        """
        Args:
            db_name: database name (be careful with production databases)
            connection: MongoDB connection instance to use instead of creating a new one
        """
        self.connection = connection or MongoClient()
        self.db = self.connection[db_name]
        self.fs = GridFS(self.db)

    async def read(self, key: str) -> Optional[ResponseOrKey]:
        result = self.fs.find_one({'_id': key})
        if result is None:
            raise KeyError
        return pickle.loads(bytes(result.read()))

    # TODO
    async def read_all(self) -> Iterable[ResponseOrKey]:
        raise NotImplementedError

    async def keys(self) -> Iterable[str]:
        return [d._id for d in self.fs.find()]

    async def write(self, key: str, item: ResponseOrKey):
        await self.delete(key)
        self.fs.put(pickle.dumps(item, protocol=-1), **{'_id': key})

    # TODO
    async def contains(self, key: str) -> bool:
        raise NotImplementedError

    async def delete(self, key: str):
        res = self.fs.find_one({'_id': key})
        if res is not None:
            self.fs.delete(res._id)

    async def clear(self):
        self.db['fs.files'].drop()
        self.db['fs.chunks'].drop()

    async def size(self) -> int:
        return self.db['fs.files'].count()
