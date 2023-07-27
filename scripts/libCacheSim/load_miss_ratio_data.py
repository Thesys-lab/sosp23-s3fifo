import os
import sys
import pickle
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from pyutils.common import conv_size_to_byte
import re
import glob
from collections import defaultdict


logger = logging.getLogger("load_miss_ratio")
logger.setLevel(logging.DEBUG)

regex = re.compile(
    r"(?P<data>.*?) (?P<algo>.*?) cache size \s*(?P<cache_size>\d+)(?P<cache_size_unit>[KMGT]iB)?, (?P<n_req>\d+) req, miss ratio (?P<miss_ratio>\d\.\d+), byte miss ratio (?P<byte_miss_ratio>\d\.\d+)"
)

N_CACHE_SIZES = 8
# ignore the traces that are too small
N_MIN_OBJ = 1000
N_MIN_BYTE = 1024 * 1024 * 1024
obj_size_dict = {}


def _load_obj_size():
    """
    load the mean object size in each trace
    used for simulations considering object sizes

    """
    import json

    obj_size_dict = {}

    with open(
        "{}/../../result/obj_size.json".format(os.path.dirname(__file__)), "r"
    ) as f:
        obj_size_dict = json.load(f)
    for k, v in obj_size_dict.items():
        obj_size_dict[k] = int(v)

    return obj_size_dict


def _find_cache_size(datapath, metric):
    if metric == "byte_miss_ratio":
        obj_size_dict = _load_obj_size()

    cache_sizes = []
    fifo_miss_ratios = []
    ifile = open(datapath, "r")
    for line in ifile:
        if " FIFO " not in line:
            continue

        m = regex.search(line)
        if m is None:
            raise RuntimeError(f"no match: {line}")
            continue

        cache_size = int(m.group("cache_size"))
        cache_size = conv_size_to_byte(cache_size, m.group("cache_size_unit"))

        cache_sizes.append(cache_size)
        if m.group("algo").strip() == "FIFO":
            fifo_miss_ratios.append(float(m.group("miss_ratio")))

    if len(fifo_miss_ratios) == 0:
        raise RuntimeError("the result has no FIFO data: {}".format(datapath))

    cache_sizes = sorted(list(set(cache_sizes)))

    # print(datapath, cache_sizes, len(cache_sizes))
    if len(cache_sizes) < N_CACHE_SIZES:
        # too few objects and 0.0001 has no objects
        # logger.debug(
        #     "load_miss_ratio_data: skip {} because of small working set size {} cache sizes".format(
        #         datapath, len(cache_sizes)
        #     )
        # )
        return [
            -1,
            -1,
            -1,
            -1,
        ]

    if fifo_miss_ratios[4] == fifo_miss_ratios[5]:
        # logger.debug(
        #     "load_miss_ratio_data: skip {} because FIFO reaches compulsory miss ratio: {} size {}, miss ratio {}".format(
        #         datapath, len(cache_sizes), cache_sizes, fifo_miss_ratios
        #     )
        # )
        return [
            -1,
            -1,
            -1,
            -1,
        ]

    assert len(cache_sizes) <= N_CACHE_SIZES, "{} too many cache sizes: {} > {}".format(
        datapath, len(cache_sizes), N_CACHE_SIZES
    )
    while len(cache_sizes) < N_CACHE_SIZES:
        cache_sizes.append(cache_sizes[-1])

    # 0.1, 1, 10, 40
    if N_CACHE_SIZES == 8:
        # {            0.1, 0.3, 1, 3, 10, 20,     40,     80}
        cache_sizes = [
            cache_sizes[0],
            cache_sizes[2],
            cache_sizes[4],
            cache_sizes[6],
        ]
    else:
        raise RuntimeError("unknown N_CACHE_SIZES: {}".format(N_CACHE_SIZES))

    for i in range(len(cache_sizes)):
        n_obj = cache_sizes[i]
        if metric == "byte_miss_ratio":
            dataname = datapath.split("/")[-1]
            n_obj = cache_sizes[i] // obj_size_dict.get(dataname, 1)
        if n_obj < N_MIN_OBJ:
            cache_sizes[i] = -1

    return cache_sizes


def load_data(datapath, metric="miss_ratio"):
    cache_size_list = _find_cache_size(datapath, metric)
    miss_ratio_dict_list = [
        {} for _ in range(len(cache_size_list))
    ]  # [{algo -> miss_ratio}, ... ]

    if cache_size_list[-1] == -1:
        # logger.debug(f"{datapath} no large cache size found")
        return miss_ratio_dict_list

    ifile = open(datapath, "r")
    for line in ifile:
        m = regex.search(line)
        if m is None:
            if len(line.strip()) > 8:
                logger.debug("skip line: {}".format(line))
            continue

        cache_size = int(m.group("cache_size"))
        cache_size = conv_size_to_byte(cache_size, m.group("cache_size_unit"))

        try:
            idx = cache_size_list.index(cache_size)
            miss_ratio_dict_list[idx][m.group("algo").strip()] = float(m.group(metric))
        except ValueError as e:
            pass

    ifile.close()

    return miss_ratio_dict_list


def load_miss_ratio_reduction_from_dir(data_dir_path, algos, metric="miss_ratio"):
    data_dirname = os.path.basename(data_dir_path)

    mr_reduction_dict_list = []
    for f in sorted(glob.glob(data_dir_path + "/*")):
        # a list of miss ratio dict (algo -> miss ratio) at different cache sizes
        miss_ratio_dict_list = load_data(f, metric)
        # print(f, sorted(miss_ratio_dict_list[2].keys()))

        if len(mr_reduction_dict_list) == 0:
            mr_reduction_dict_list = [
                defaultdict(list) for _ in range(len(miss_ratio_dict_list))
            ]
        for size_idx, miss_ratio_dict in enumerate(miss_ratio_dict_list):
            if len(miss_ratio_dict) == 0:
                continue

            mr_fifo = miss_ratio_dict["FIFO"]
            if mr_fifo == 0 or 1 - mr_fifo == 0:
                continue

            miss_ratio_dict = {k.lower(): v for k, v in miss_ratio_dict.items()}

            mr_reduction_dict = {}
            for algo in algos:
                if algo.lower() not in miss_ratio_dict:
                    logger.warning("no data for {} in {}".format(algo.lower(), f))
                    break
                miss_ratio = miss_ratio_dict[algo.lower()]
                mr_reduction = (mr_fifo - miss_ratio) / mr_fifo
                if mr_reduction < 0:
                    mr_reduction = -(miss_ratio - mr_fifo) / miss_ratio

                mr_reduction_dict[algo] = mr_reduction

            if len(mr_reduction_dict) < len(algos):
                # some algorithm does not have data
                logger.info(
                    "skip {} because of missing algorithm result {}".format(
                        f, set(algos) - set(miss_ratio_dict.keys())
                    )
                )
                continue

            for algo, mr_reduction in mr_reduction_dict.items():
                mr_reduction_dict_list[size_idx][algo].append(mr_reduction)

    return mr_reduction_dict_list


if __name__ == "__main__":
    r = load_data(
        "/disk/result/libCacheSim/result//all/meta_kvcache_traces_1.oracleGeneral.bin.zst"
    )
