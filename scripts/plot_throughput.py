import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from pyutils.common import *

import matplotlib.pyplot as plt

n_threads = [ 1, 2, 4, 8, 16, ]

# throughput at cache size 500 MB
thrpt_500 = {
    "strict_lru": [ 2.13, 1.96, 1.86, 1.69, 1.18, ],
    "lru": [ 1.86, 2.74, 2.80, 2.71, 1.91, ],
    "twoQ": [ 1.86, 2.56, 2.46, 2.25, 1.57, ],
    "tinyLFU": [ 1.56, 1.76, 1.66, 1.46, 1.21, ],
    "s3fifo": [ 2.40, 3.85, 6.48, 10.75, 13.49, ],
    "segcache": [ 1.91, 3.65, 6.73, 12.59, 20.49, ],
}

thrpt_1000 = {
    "strict_lru": [ 2.20, 2.01, 1.93, 1.74, 1.22, ],
    "lru": [ 2.25, 2.87, 2.98, 2.87, 1.98, ],
    "twoQ": [ 2.17, 2.62, 2.61, 2.39, 1.66, ],
    "tinyLFU": [ 1.57, 1.94, 1.85, 1.63, 1.27, ],
    "s3fifo": [ 2.52, 4.31, 7.23, 11.94, 16.42, ],
    "segcache": [ 1.99, 4.20, 7.75, 14.91, 25.83, ],
}

thrpt_2000 = {
    "strict_lru": [ 2.39, 2.05, 2.03, 1.91, 1.33,],
    "lru": [ 2.45, 3.09, 3.21, 3.20, 2.31, ],
    "twoQ": [ 2.37, 2.76, 2.88, 2.80, 1.95, ],
    "tinyLFU": [ 1.73, 2.23, 2.15, 1.82, 1.52, ],
    "s3fifo": [ 2.84, 4.95, 8.20, 13.84, 19.54, ],
    "segcache": [ 2.92, 5.47, 9.97, 18.90, 30.20, ],
}

thrpt_4000 = {
    "strict_lru": [ 2.65, 2.24, 2.34, 2.85, 2.41, ],
    "lru": [2.77, 3.35, 3.88, 4.10, 5.25, ],
    "twoQ": [ 2.71, 2.99, 3.57, 4.41, 4.89, ],
    "tinyLFU": [ 2.10, 2.67, 2.31, 2.23, 1.58, ],
    "s3fifo": [ 3.55, 6.29, 10.39, 18.55, 29.39, ],
    "segcache": [ 2.86, 5.41, 10.08, 18.79, 32.03, ],
}

miss_ratio_zipf = {
    "strict_lru": [ 0.2088, 0.1450, 0.0784, 0.0119, ],
    "lru": [ 0.2089, 0.1450, 0.0784, 0.0119, ],
    "twoQ": [ 0.1934, 0.1369, 0.0766, 0.0121, ],
    "tinyLFU": [ 0.1609, 0.1126, 0.0637, 0.0115, ],
    "s3fifo": [ 0.1687, 0.1202, 0.0694, 0.0118, ],
}

colors = ["#b2182b", "#ef8a62", "#fddbc7", "#67a9cf", "#2166ac"]
colors = ["#b2182b", "#ef8a62", "#602c21", "#67a9cf", "#2166ac"]


def plot_throughput(data_dict, yticks, name):
    plt.plot(
        n_threads,
        data_dict["s3fifo"],
        marker="*",
        markersize=20,
        color=colors[0],
        linestyle="-",
        label="S3-FIFO",
    )
    plt.plot(
        n_threads,
        data_dict["strict_lru"],
        marker="<",
        markersize=20,
        color=colors[1],
        linestyle="--",
        label="LRU",
    )
    plt.plot(
        n_threads,
        data_dict["segcache"],
        marker="v",
        markersize=20,
        color=colors[4],
        linestyle="-.",
        label="Segcache",
    )
    plt.plot(
        n_threads,
        data_dict["lru"],
        marker=">",
        markersize=20,
        color=colors[2],
        linestyle="dotted",
        label="Optimized LRU",
    )

    plt.plot(
        n_threads,
        data_dict["tinyLFU"],
        marker="v",
        markersize=20,
        color=colors[3],
        linestyle="-.",
        label="Optimized TinyLFU",
    )

    plt.xlabel("Number of threads")
    plt.ylabel("Throughput (Mops/sec)")
    plt.xscale("log")
    # plt.yscale("log")
    plt.xticks(n_threads, n_threads)
    plt.yticks(yticks, yticks)
    plt.grid(linestyle="--", linewidth=0.5)
    # plt.title("Throughput of Zipfian workload")

    plt.legend(
        loc="upper left",
        ncol=2,
        fontsize=28,
        frameon=False,
        columnspacing=0.5,
        handletextpad=0.2,
        #    labelspacing=0.2,
        bbox_to_anchor=(0.0, 1.0),
    )
    plt.savefig("cachelib_thrpt_{}.pdf".format(name), bbox_inches="tight")
    plt.clf()


if __name__ == "__main__":
    plot_throughput(
        thrpt_500,
        [ 0, 4, 8, 12, 16, 20, 24, ],
        "zipf_500",
    )
    plot_throughput(
        thrpt_4000,
        [ 0, 8, 16, 24, 32, 40, ],
        "zipf_4000",
    )
