

import logging
from collections import defaultdict
from collections import deque
from lru import LRU


logger = logging.getLogger("cache")


class Cache:
    def __init__(self, name, size) -> None:
        self.name = name
        self.size = size
        self.n_obj = 0
        self.occupied_bytes = 0
        self.n_rewritten_byte = 0
        logger.info(f"create {name} cache with size {size}")

    def __str__(self) -> str:
        return "{}: {} objects, {} bytes".format(self.name, self.n_obj,
                                                 self.occupied_bytes)

    def __repr__(self) -> str:
        return self.__str__()

    def insert(self, obj_id, size):
        raise NotImplementedError

    def evict(self):
        raise NotImplementedError

    def get(self, ts, obj_id):
        raise NotImplementedError


class LRUCache(Cache):

    def __init__(self, size) -> None:
        super().__init__("LRU", size)
        # make sure LRU does not evict implicitly
        self.lru = LRU(size + 1)

    def insert(self, obj_id, size, next_access_vtime):
        assert len(self.lru) <= self.size
        self.lru[obj_id] = (size, next_access_vtime)
        self.n_obj += 1
        self.occupied_bytes += size

    def evict(self):
        evicted_obj_id, (size, next_access_vtime) = self.lru.peek_last_item()
        del self.lru[evicted_obj_id]
        self.n_obj -= 1
        self.occupied_bytes -= size

        return evicted_obj_id, size, next_access_vtime

    def get(self, ts, obj_id):
        self.ts = ts
        if self.lru.has_key(obj_id):
            return self.lru[obj_id]
        else:
            return None


class FIFOCache(Cache):

    def __init__(self, size) -> None:
        super().__init__("FIFO", size)
        self.fifo = deque()
        self.objs = {}

    def insert(self, obj_id, size, next_access_vtime):
        assert len(self.fifo) <= self.size
        self.fifo.append(obj_id)
        self.objs[obj_id] = (size, next_access_vtime)
        self.n_obj += 1
        self.occupied_bytes += size

    def evict(self):
        evicted_obj_id = self.fifo.popleft()
        size, next_access_vtime = self.objs[evicted_obj_id]
        del self.objs[evicted_obj_id]
        self.n_obj -= 1
        self.occupied_bytes -= size

        return evicted_obj_id, size, next_access_vtime

    def get(self, ts, obj_id):
        self.ts = ts
        if obj_id in self.objs:
            return self.objs[obj_id]
        else:
            return None


class ClockCache(Cache):

    def __init__(self, size) -> None:
        super().__init__("Clock", size)
        self.fifo = deque()
        self.objs = {}
        self.n_rewritten_byte = 0

    def insert(self, obj_id, size, next_access_vtime):
        assert len(self.fifo) <= self.size
        self.fifo.append(obj_id)
        self.objs[obj_id] = (size, next_access_vtime, 0)
        self.n_obj += 1
        self.occupied_bytes += size

    def evict(self):
        while len(self.objs) > 0:
            evicted_obj_id = self.fifo.popleft()
            size, next_access_vtime, has_access = self.objs[evicted_obj_id]
            if has_access:
                self.fifo.append(evicted_obj_id)
                self.objs[evicted_obj_id] = (size, next_access_vtime, 0)

                self.n_rewritten_byte += size
            else:
                del self.objs[evicted_obj_id]
                self.n_obj -= 1
                self.occupied_bytes -= size

                return evicted_obj_id, size, next_access_vtime

    def get(self, ts, obj_id):
        self.ts = ts
        if obj_id in self.objs:
            size, next_access_vtime, has_access = self.objs[obj_id]
            self.objs[obj_id] = (size, next_access_vtime, 1)
            return self.objs[obj_id][:2]
        else:
            return None


def test_cache():
    tracepath = "/disk/data/de/wiki_2019t.oracleGeneral.sample10"
    cache = LRUCache(200001)
    cache = FIFOCache(200001)
    cache = ClockCache(200001)
    cache_size = 200000
    n_req, n_miss = 0, 0
    with TraceReader(tracepath) as tr:
        for ts, obj_id, size, next_access_vtime in tr:
            n_req += 1
            if cache.get(ts, obj_id) is None:
                n_miss += 1
                cache.insert(obj_id, 1, next_access_vtime)
            if cache.occupied_bytes > cache_size:
                evicted_obj_id, size, next_access_vtime = cache.evict()

    print("n_req: {}, n_miss: {}, miss ratio: {}".format(
        n_req, n_miss, n_miss / n_req))
