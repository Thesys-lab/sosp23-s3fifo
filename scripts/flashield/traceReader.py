
import os
import sys
import struct
import random


class TraceReader:
    def __init__(self, tracepath, struct_str="<IQIq", n_req=1e30):
        self.tracepath = tracepath
        self.n_req = n_req
        self.struct = struct.Struct(struct_str)
        self.trace_file = None
        self.n_read_req = 0
        self.n_trace_req = 0
        self._open_trace()

    def _open_trace(self):
        self.trace_file = open(self.tracepath, "rb")

    def __enter__(self):
        self._open_trace()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.trace_file is not None:
            self.trace_file.close()
        self.trace_file = None

    def __len__(self):
        self.n_trace_req = os.path.getsize(self.tracepath) // self.struct.size
        assert self.n_trace_req * self.struct.size == os.path.getsize(
            self.tracepath
        ), "trace file size is not mulitple of req struct size"
        return self.n_trace_req

    def __iter__(self):
        return self

    def __next__(self):
        req = self.read_one_req()
        if req:
            return req
        else:
            raise StopIteration

    def reset(self):
        self.n_read_req = 0
        self.trace_file.seek(0, 0)

    def read_one_req(self):
        if self.n_read_req >= self.n_req:
            return None

        d = self.trace_file.read(self.struct.size)
        if d:
            return self.struct.unpack(d)
        else:
            return None


def test_reader():
    tracepath = "/disk/data/de/wiki_2019t.oracleGeneral.sample10"
    with TraceReader(tracepath) as tr:
        for ts, obj_id, size, next_access_vtime in tr:
            print(ts, obj_id, size, next_access_vtime)


wss_dict = {
    "akamai_sjc.oracleGeneral.sample10": (16613067, 15194925831194),
    "wiki_2019t.oracleGeneral.sample10": (1838769, 42956200786),
    "wiki_2019u.oracleGeneral.sample10": (4971097, 822145885238),
    "tencent_photo1.oracleGeneral.sample10": (52930527, 1325229398791),
    "tencent_photo2.oracleGeneral.sample10": (50870860, 1278719057552),
    "cf_colo28.oracleGeneral.sample10": (137891252, 136378065840876),
    "alibaba_block2020.oracleGeneral.sample10": (170191353, 12554714061824),
    "tencent_block.oracleGeneral.sample10": (55063475, 7103717707776),
}


