import os
import sys
import struct
import random
from collections import defaultdict
from collections import deque
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/common/")
from cache import Cache, LRUCache, FIFOCache, ClockCache
from traceReader import TraceReader, wss_dict


logger = logging.getLogger("flashield")
logger.setLevel(logging.INFO)


class Flashield(Cache):
    class Trainer:
        def __init__(self, name):
            self.name = name
            self.features = {}
            self.labels = {}

        def add_training_sample_features(self, obj_id, n_access):
            if random.randint(1, n_access) == 1:
                self.features[obj_id] = n_access

        def add_training_sample_labels(self, obj_id):
            if obj_id in self.features:
                self.labels[obj_id] = True

        def train(self):
            logging.info("{} Training Flashield...".format(self.name))
            feature_list, label_list = [], []
            for obj_id, n_access in self.features.items():
                feature_list.append([n_access])
                label_list.append(self.labels.get(obj_id, False))
            logging.info(
                "{} Training Flashield: {} features {} labels ...".format(
                    self.name, len(feature_list), len(label_list)
                )
            )
            # print(list(zip(feature_list[:200], label_list[:200])))
            if len(feature_list) > 100000:
                feature_list = feature_list[:100000]
                label_list = label_list[:100000]
            clf = make_pipeline(StandardScaler(), SVC())
            clf.fit(feature_list, label_list)
            logging.info("{} finish training".format(self.name))

            return clf

    def __init__(self, name, size, ram_size_ratio=0.1, disk_cache_type="Clock") -> None:
        super().__init__("Flashield", size)
        self.name = name
        self.start_ts = -1
        self.curr_ts = -1
        self.ram_size = int(size * ram_size_ratio)
        self.disk_size = size - self.ram_size
        self.ram = LRUCache(self.ram_size)
        if disk_cache_type == "FIFO":
            self.disk = FIFOCache(self.disk_size)
        elif disk_cache_type == "Clock":
            self.disk = ClockCache(self.disk_size)
        else:
            raise Exception("Unknown disk cache type: {}".format(disk_cache_type))

        self.n_req_in_ram = defaultdict(int)
        self.training_samples = []

        self.trainer = self.Trainer(name)
        self.classifier = None

        self.n_req = 0
        self.n_miss = 0
        self.disk_write_byte = 0

    def insert(self, obj_id, size, next_access_vtime):
        self.ram.insert(obj_id, size, next_access_vtime)
        if self.curr_ts < 3600:
            self.trainer.add_training_sample_features(obj_id, 1)

        while self.ram.occupied_bytes > self.ram_size:
            obj_id, size, next_access_vtime = self.ram.evict()
            if self.predict(obj_id, size, next_access_vtime):
                self.disk.insert(obj_id, size, next_access_vtime)
                self.disk_write_byte += size
                while self.disk.occupied_bytes > self.disk_size:
                    self.disk.evict()

    def evict(self):
        pass

    def get(self, ts, obj_id):
        self.n_req += 1
        if self.start_ts == -1:
            self.start_ts = ts
        self.curr_ts = ts - self.start_ts

        ret = self.ram.get(ts, obj_id)
        if ret is not None:
            self.n_req_in_ram[obj_id] += 1

            if self.curr_ts < 3600:
                self.trainer.add_training_sample_features(
                    obj_id, self.n_req_in_ram[obj_id]
                )
            elif self.curr_ts < 7200:
                self.trainer.add_training_sample_labels(obj_id)
            elif self.classifier is None:
                self.classifier = self.trainer.train()

            return ret
        else:
            ret = self.disk.get(ts, obj_id)
            if ret is not None:
                return ret
            else:
                self.n_miss += 1
                return None

    def predict(self, obj_id, size, next_access_vtime):
        if self.classifier is None:
            return True

        return self.classifier.predict([[self.n_req_in_ram[obj_id]]])

    def predict_future(self, obj_id, size, next_access_vtime):
        miss_ratio = self.n_miss / self.n_req
        if (
            next_access_vtime > 0
            and next_access_vtime < self.n_req + self.size / miss_ratio
        ):
            return True
        else:
            return False


def run_flashield(
    tracepath,
    cache_size,
    wss,
    ram_size_ratio=0.1,
    disk_cache_type="Clock",
    use_obj_size=False,
    logging_interval=1000000,
):
    dataname = os.path.basename(tracepath)
    name = "{}-{}-{}-{}".format(dataname, ram_size_ratio, disk_cache_type, use_obj_size)
    cache = Flashield(dataname, cache_size, ram_size_ratio, disk_cache_type)
    n_req, n_miss = 0, 0
    with TraceReader(tracepath) as tr:
        for ts, obj_id, size, next_access_vtime in tr:
            n_req += 1
            if not use_obj_size:
                size = 1
            if cache.get(ts, obj_id) is None:
                n_miss += 1
                cache.insert(obj_id, size, next_access_vtime)
                cache.evict()

            # if n_req % 10000000 == 0:
            if n_req % logging_interval == 0:
                logging.info(
                    "{} n_req: {}, n_miss: {}, miss ratio: {:.4f}, disk write {} + {} ({:.4f})".format(
                        name,
                        n_req,
                        n_miss,
                        n_miss / n_req,
                        cache.disk_write_byte,
                        cache.disk.n_rewritten_byte,
                        (cache.disk_write_byte + cache.disk.n_rewritten_byte) / wss,
                    )
                )

    logging.info(
        "{} n_req: {}, n_miss: {}, miss ratio: {:.4f}, disk write {} + {} ({:.4f})".format(
            name,
            n_req,
            n_miss,
            n_miss / n_req,
            cache.disk_write_byte,
            cache.disk.n_rewritten_byte,
            (cache.disk_write_byte + cache.disk.n_rewritten_byte) / wss,
        )
    )


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("tracepath", type=str)
    p.add_argument("--cache-size", type=float, default=0.1)
    p.add_argument("--ram-size-ratio", type=float, default=0.05)
    p.add_argument("--disk-cache-type", type=str, default="Clock")
    p.add_argument("--use-obj-size", type=bool, default=True)
    p.add_argument("--logging-interval", type=int, default=10000000)
    pa = p.parse_args()

    dataname = os.path.basename(pa.tracepath)
    logging.basicConfig(
        format="%(asctime)s: %(levelname)s [%(filename)s:%(lineno)s (%(name)s)]: \t%(message)s",
        level=logging.INFO,
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler("{}.log".format(dataname)),
            logging.StreamHandler(sys.stdout),
        ],
    )

    if pa.cache_size < 1:
        if dataname not in wss_dict:
            logging.info("calculating wss for {}".format(dataname))

            seen_objs = {}
            with TraceReader(pa.tracepath) as tr:
                for ts, obj_id, size, next_access_vtime in tr:
                    seen_objs[obj_id] = size
            wss_obj = len(seen_objs)
            wss_byte = sum(seen_objs.values())
            logging.info(
                "{} wss_obj: {}, wss_byte: {}".format(
                    os.path.basename(pa.tracepath), wss_obj, wss_byte
                )
            )
        else:
            wss_obj, wss_byte = wss_dict[dataname]

        if pa.use_obj_size:
            wss = wss_byte
        else:
            wss = wss_obj

        cache_size = int(pa.cache_size * wss)

    run_flashield(
        pa.tracepath,
        cache_size,
        wss,
        ram_size_ratio=pa.ram_size_ratio,
        disk_cache_type=pa.disk_cache_type,
        use_obj_size=pa.use_obj_size,
    )

