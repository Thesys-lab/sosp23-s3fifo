import os
import sys
import logging
import itertools

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from pyutils.common import (
    conv_size_to_byte,
    conv_to_cdf,
    get_colors,
    get_markers,
    get_linestyles,
)

from load_miss_ratio_data import load_data, load_miss_ratio_reduction_from_dir

import re
import glob
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt

logger = logging.getLogger("plot_fifo_size")
logger.setLevel(logging.INFO)

N_CACHE_SIZES = 8
N_MIN_OBJ = 1000

regex = re.compile(
    r"result/(?P<data>.*?) (?P<algo>.*?) cache size \s*(?P<cache_size>\d+)(?P<cache_size_unit>[KMGT]iB)?, (?P<n_req>\d+) req, miss ratio (?P<miss_ratio>\d\.\d+), byte miss ratio (?P<byte_miss_ratio>\d\.\d+)"
)


def load_data(datapath):
    miss_ratio_dict = defaultdict(list)  # {algo -> [miss_ratio, ...]}

    ifile = open(datapath, "r")
    cache_sizes = []
    for line in ifile:
        m = regex.search(line)
        if m is None:
            continue

        cache_size = int(m.group("cache_size"))
        cache_size = conv_size_to_byte(cache_size, m.group("cache_size_unit"))

        cache_sizes.append(cache_size)
        miss_ratio_dict[m.group("algo").strip()].append(float(m.group("miss_ratio")))

    ifile.close()

    cache_sizes = sorted(list(set(cache_sizes)))
    miss_ratio_dict_list = [
        {} for _ in range(len(cache_sizes))
    ]  # [{algo -> miss_ratio}, ... ]

    for algo, miss_ratio_list in miss_ratio_dict.items():
        n = len(miss_ratio_list) / N_CACHE_SIZES
        if (
            n > 1
            and n == int(n)
            and miss_ratio_list[0] == miss_ratio_list[N_CACHE_SIZES]
        ):
            miss_ratio_list = miss_ratio_list[:N_CACHE_SIZES]
        assert (
            len(miss_ratio_list) <= N_CACHE_SIZES
        ), f"{datapath} {algo} has {len(miss_ratio_list)} cache sizes, more than {N_CACHE_SIZES}"

        # offset = N_CACHE_SIZES - len(miss_ratio_list)
        # if offset != 0:
        #     logger.debug(f"{datapath} {algo} has {len(miss_ratio_list)} cache sizes, less than {N_CACHE_SIZES}")
        #     print(offset)
        offset = 0
        if len(cache_sizes) != len(miss_ratio_list):
            print(
                datapath,
                algo,
                len(cache_sizes),
                len(miss_ratio_list),
                cache_sizes,
                miss_ratio_list,
            )
        for idx in range(len(miss_ratio_list)):
            if cache_sizes[idx] >= N_MIN_OBJ:
                miss_ratio_dict_list[idx + offset][algo] = miss_ratio_list[idx]

    # print(datapath, len(miss_ratio_dict_list))
    if len(miss_ratio_dict_list[0]) == 0:
        logger.debug(
            f"{datapath} has no small size, {[len(d) for d in miss_ratio_dict_list]} algorithms"
        )

    return cache_sizes, miss_ratio_dict_list


def plot_fifo_size_percentiles(datapath, size_idx=0, metric="miss_ratio"):
    """
    plot the median, mean, 90th percentile of miss ratio reduction

    Args:
        datapath (str): path to result data
    """

    algo_list = [
        "S3FIFO-0.0100-0.9000",
        "S3FIFO-0.0500-0.9000",
        "S3FIFO-0.1000-0.9000",
        "S3FIFO-0.2000-0.9000",
        "S3FIFO-0.3000-0.9000",
        "S3FIFO-0.4000-0.9000",
        "S3FIFO-0.5000-0.9000",
        "S3FIFO-0.6000-0.9000",
        "S3FIFO-0.7000-0.9000",
        "S3FIFO-0.8000-0.9000",
        "S3FIFO-0.9000-0.9000",
    ]

    name_list = ["{:.2f}".format(float(name.split("-")[1])) for name in algo_list]

    markers = itertools.cycle("<^osv>v*p")
    colors = itertools.cycle(
        reversed(["#b2182b", "#ef8a62", "#fddbc7", "#d1e5f0", "#67a9cf", "#2166ac"])
    )

    mr_reduction_dict_list = load_miss_ratio_reduction_from_dir(
        datapath, algo_list, metric
    )

    plt.figure(figsize=(28, 8))

    # print([len(mr_reduction_dict_list[size_idx][algo]) for algo in algo_list])
    y = [np.percentile(mr_reduction_dict_list[size_idx][algo], 5) for algo in algo_list]
    plt.scatter(
        range(len(y)), y, label="P10", marker=next(markers), color=next(colors), s=480
    )

    y = [
        np.percentile(mr_reduction_dict_list[size_idx][algo], 25) for algo in algo_list
    ]
    plt.scatter(
        range(len(y)), y, label="P25", marker=next(markers), color=next(colors), s=480
    )

    y = [
        np.percentile(mr_reduction_dict_list[size_idx][algo], 50) for algo in algo_list
    ]
    plt.scatter(
        range(len(y)),
        y,
        label="Median",
        marker=next(markers),
        color=next(colors),
        s=480,
    )

    y = [np.mean(mr_reduction_dict_list[size_idx][algo]) for algo in algo_list]
    plt.scatter(
        range(len(y)), y, label="Mean", marker=next(markers), color=next(colors), s=480
    )

    y = [
        np.percentile(mr_reduction_dict_list[size_idx][algo], 75) for algo in algo_list
    ]
    plt.scatter(
        range(len(y)), y, label="P75", marker=next(markers), color=next(colors), s=480
    )

    y = [
        np.percentile(mr_reduction_dict_list[size_idx][algo], 95) for algo in algo_list
    ]
    plt.scatter(
        range(len(y)), y, label="P90", marker=next(markers), color=next(colors), s=480
    )

    if plt.ylim()[0] < -0.1:
        plt.ylim(bottom=-0.1)

    plt.xticks(range(len(algo_list)), name_list, fontsize=32, rotation=0)
    plt.xlabel("Probationary FIFO size (in fraction of cache size)")
    if metric == "byte_miss_ratio":
        plt.ylabel("Byte miss ratio reduction from FIFO", fontsize=32)
    else:
        plt.ylabel("Miss ratio reduction from FIFO")
    plt.grid(linestyle="--")
    plt.legend(
        ncol=8,
        loc="upper left",
        fontsize=38,
        bbox_to_anchor=(-0.02, 1.2),
        frameon=False,
    )
    plt.savefig("{}_percentiles_{}.pdf".format(metric, size_idx), bbox_inches="tight")
    plt.clf()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--datapath", type=str, help="path to the cachesim result")
    ap = parser.parse_args()

    plot_fifo_size_percentiles(
        "{}".format(ap.datapath), size_idx=0, metric="miss_ratio"
    )
    plot_fifo_size_percentiles(
        "{}".format(ap.datapath), size_idx=2, metric="miss_ratio"
    )

