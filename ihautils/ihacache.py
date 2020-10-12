import asyncio
import math
from functools import partial
from typing import Any, Union

import diskcache
from sanic.log import logger

import ujson

udumps = partial(ujson.dumps, ensure_ascii=False, escape_forward_slashes=False)


class ihateanimeCache:
    def __init__(self, cache_location: asyncio.AbstractEventLoop, loop=None):
        logger.info("[ihaCache] Spinning up new diskcache server!")
        self.cachedb = diskcache.Cache(cache_location)
        self.loop: asyncio.AbstractEventLoop = loop
        self._usable = None
        if self.loop is None:
            self.loop = asyncio.get_event_loop()

    def is_usable(self):
        return self._usable

    async def _execute(self, func, *args, **kwargs) -> Any:
        """Execute a function in async env

        :param func: Callable: A function to call
        :param args: Arguments
        :param kwargs: keywords arguments
        :return: result of function execution
        :rtype: Any
        """
        logger.debug("[ihaCache:execute] Executing function!")
        wrapped_func = partial(func, *args, **kwargs)
        fut = self.loop.run_in_executor(None, wrapped_func)
        res = await fut
        logger.debug("[ihaCache:execute] Function executed!")
        return res

    async def get(self, key: str) -> Union[None, str, bytes]:
        """Get a value from a key, return None if there's KeyError

        :param key: cache key
        :type key: str
        :return: value of a key.
        :rtype: Union[None, str, bytes]
        """
        logger.info(f"[ihaCache] Getting key: {key}")
        try:
            val = await self._execute(self.cachedb.get, key=key, default=None, retry=True)
        except KeyError:
            val = None
        except TimeoutError:
            val = None
        if isinstance(val, str):
            try:
                val = ujson.loads(val)
            except ValueError:
                pass
        return val

    async def set(self, key: str, val: Union[str, bytes, dict, list]) -> bool:
        """Set a value to a key

        :param key: cache key
        :type key: str
        :param val: cache value
        :type val: Union[str, bytes, dict, list]
        :return: see result
        :rtype: bool
        """
        logger.info(f"[ihaCache] Setting key: {key}")
        if isinstance(val, (list, dict)):
            val = udumps(val)
        elif isinstance(val, tuple):
            val = str(val)
        res = await self._execute(self.cachedb.set, key=key, value=val, retry=True)
        return res

    async def setex(self, key: str, expired: Union[int, float], val: Union[str, bytes, dict, list],) -> bool:
        """Set a value to a key with expiration time

        :param key: cache key
        :type key: str
        :param expired: expiring time since current epoch time
        :type expired: Union[int, float]
        :param val: cache value
        :type val: Union[str, bytes, dict, list]
        :return: see result
        :rtype: bool
        """
        logger.info(f"[ihaCache] Setting key: {key} (Expired: {expired})")
        if isinstance(val, dict):
            val = udumps(val)
        elif isinstance(val, (list, tuple)):
            val = str(val)
        if isinstance(expired, float):
            expired = math.ceil(expired)
        res = await self._execute(self.cachedb.set, key=key, value=val, retry=True, expire=expired)
        return res

    async def expire(self):
        logger.info("[ihaCache] Expiring all keys...")
        await self._execute(self.cachedb.expire)

    async def delete(self, key: str):
        """
        Delete key

        :param key: str: key to delete
        """
        logger.info(f"[ihaCache] Deleting key: {key}")
        try:
            await self._execute(self.cachedb.delete, key=key, retry=True)
        except TimeoutError:
            pass
        except Exception:
            pass

    async def clean_db(self):
        """
        Clean database.
        """
        logger.info("[ihaCache] Cleaning database...")
        await self._execute(self.cachedb.clear, retry=True)

    async def ping(self):
        """
        Test cache client connection
        """
        logger.info("[ihaCache:ping] Pinging!")
        ping = await self.get("ping")
        if not ping:
            res = await self.set("ping", "pong")
            if not res:
                logger.info("[ihaCache:ping] Ping failed, not usable!")
                self._usable = False
                return
            ping = await self.get("ping")

        if ping != "pong":
            logger.info("[ihaCache:ping] Ping failed, not usable!")
            self._usable = False
            return

        logger.info("[ihaCache:ping] Pong!")
