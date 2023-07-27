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
import re
import glob
from collections import defaultdict

# from load_miss_ratio_data import load_data, load_miss_ratio_reduction_dict_list_from_dir
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

wiki_miss_ratio_write_amp = {
    "FIFO": (0.2017, 3.25),
    # 20% reinsertion based on recency
    "FIFO-Reinsertion": (0.1812, 3.51),
    # 0.1% DRAM LRU
    "Flashield-Clock-0.001": (0.4507, 0.030062),
    # 0.1% DRAM LRU
    "Flashield-FIFO-0.001": (0.4505, 0.030063),
    # 0.1% DRAM LRU with FIFO disk and prob 0.2
    "Probabilistic-Clock-0.001": (0.1532, 1.2630),
    # 0.1% DRAM LRU with FIFO disk and prob 0.2
    "Probabilistic-FIFO-0.001": (0.2070, 0.6683),
    # 0.1% DRAM with Clock, and move threshold 2
    "S3-FIFO-Clock-2-0.001": (0.1319, 0.9982),
    # 0.1% DRAM with FIFO, and move threshold 2
    "S3-FIFO-FIFO-2-0.001": (0.1609, 0.0444),
    # 1% DRAM with Clock
    "Flashield-Clock-0.01": (0.4095, 0.031445),
    # 1% DRAM with Clock
    "Flashield-FIFO-0.01": (0.4078, 0.03168),
    # 1% DRAM LRU with Clock disk and prob 0.2
    "Probabilistic-Clock-0.01": (0.1517, 1.2472),
    # 1% DRAM LRU with FIFO disk and prob 0.2
    "Probabilistic-FIFO-0.01": (0.2046, 0.6595),
    # 1% DRAM with Clock and move threshold 2
    "S3-FIFO-Clock-2-0.01": (0.1308, 0.9952),
    # 1% DRAM with FIFO and move threshold 2
    "S3-FIFO-FIFO-2-0.01": (0.1586, 0.0563),
    # 10% DRAM with Clock
    "Flashield-Clock-0.10": (0.2446, 0.087867),
    # 10% DRAM with Clock
    "Flashield-FIFO-0.10": (0.2446, 0.087867),
    # 10% DRAM LRU with Clock disk and prob 0.2
    "Probabilistic-Clock-0.10": (0.1518, 1.2417),
    # 10% DRAM LRU with FIFO disk and prob 0.2
    "Probabilistic-FIFO-0.10": (0.1987, 0.6381),
    # 10% DRAM with Clock and move threshold 2
    "S3-FIFO-Clock-2-0.10": (0.1332, 1.0699),
    # 10% DRAM with FIFO and move threshold 2
    "S3-FIFO-FIFO-2-0.10": (0.1581, 0.1189),
}
# consider size
tencentPhoto_miss_ratio_write_amp = {
    "FIFO": (0.2540, 1.49),
    # 20% reinsertion based on recency
    "FIFO-Reinsertion": (0.2375, 1.58),
    # 0.1% DRAM LRU
    "Flashield-Clock-0.001": (0.7675, 0.02682),
    # 0.1% DRAM LRU
    "Flashield-FIFO-0.001": (0.7566, 0.02725),
    # 0.1% DRAM LRU with Clock disk and prob 0.2
    "Probabilistic-Clock-0.001": (0.3026, 0.6048),
    # 0.1% DRAM LRU with FIFO disk and prob 0.2
    "Probabilistic-FIFO-0.001": (0.3131, 0.3817),
    # 0.1% DRAM with Clock
    "S3-FIFO-Clock-2-0.001": (0.2379, 0.4231),
    # 0.1% DRAM with FIFO
    "S3-FIFO-FIFO-2-0.001": (0.2474, 0.0825),
    # 1% DRAM LRU
    "Flashield-Clock-0.01": (0.6089, 0.02915),
    # 1% DRAM LRU
    "Flashield-FIFO-0.01": (0.6042, 0.03007),
    # 1% DRAM LRU with Clock disk and prob 0.2
    "Probabilistic-Clock-0.01": (0.2940, 0.5762),
    # 1% DRAM LRU with FIFO disk and prob 0.2
    "Probabilistic-FIFO-0.01": (0.3038, 0.3700),
    "S3-FIFO-Clock-2-0.01": (0.2281, 0.4505),
    "S3-FIFO-FIFO-2-0.01": (0.2369, 0.1219),
    # 10% DRAM LRU
    "Flashield-Clock-0.10": (0.2743, 0.1828),
    # 10% DRAM LRU
    "Flashield-FIFO-0.10": (0.2721, 0.3456),
    # 10% DRAM LRU with Clock disk and prob 0.2
    "Probabilistic-Clock-0.10": (0.2716, 0.5001),
    # 10% DRAM LRU with FIFO disk and prob 0.2
    "Probabilistic-FIFO-0.10": (0.2800, 0.3392),
    "S3-FIFO-Clock-2-0.10": (0.2156, 0.5011),
    "S3-FIFO-FIFO-2-0.10": (0.2240, 0.1870),
}


def plot_write_amp():
    """

    ./flash ${data} oracleGeneral flashProb 0.1 --ignore-obj-size 1 -e "ram-size-ratio=0.05,disk-cache=fifo"
    python3 flashield.py ${data} --ram-size-ratio=0.05 --disk-cache-type=FIFO

    """

    params = {
        "axes.labelsize": 48,
        "axes.titlesize": 48,
        "xtick.labelsize": 48,
        "ytick.labelsize": 48,
        "lines.linewidth": 4,
        "legend.fontsize": 64,
        "legend.handlelength": 2,
    }
    plt.rcParams.update(params)

    markers = "os<*^p>"
    colors = ["#b2182b", "#ef8a62", "#fddbc7", "#d1e5f0", "#67a9cf", "#2166ac"]
    colors = [
        "#d73027",
        "#fc8d59",
        "#fee090",
        "#e0f3f8",
        "#91bfdb",
        "#4575b4",
    ]
    colors = [
        "#ffffbf",
        "#d73027",
        "#4575b4",
    ]
    colors = [
        "#0571b0",
        "#f4a582",
        "#92c5de",
        "#ca0020",
    ]
    colors = [
        "#b2182b",
        "#ef8a62",
        "#67a9cf",
        "#2166ac",
        "#fddbc7",
        "#d1e5f0",
    ]

    figure, axis = plt.subplots(1, 2, figsize=(28, 8))
    plt.subplots_adjust(top=0.99, bottom=0.01, hspace=1.5, wspace=0.4)

    fifo = axis[0].scatter(
        *wiki_miss_ratio_write_amp["FIFO"],
        marker="<",
        s=1280,
        color=colors[4],
        linewidths=2,
        edgecolors="grey",
    )  # label="FIFO"
    # fifor = axis[0].scatter(*wiki_miss_ratio_write_amp["FIFO-Reinsertion"], marker="^", s=1280, color=colors[0], linewidths=2, edgecolors="grey", ) # label="FIFO-Reinsertion"

    p1 = axis[0].scatter(
        *wiki_miss_ratio_write_amp["Probabilistic-FIFO-0.001"],
        marker=">",
        s=1280,
        color=colors[1],
        linewidths=2,
        edgecolors="black",
        label="Probabilistic",
    )
    p2 = axis[0].scatter(
        *wiki_miss_ratio_write_amp["Probabilistic-FIFO-0.01"],
        marker=">",
        s=1280,
        color=colors[2],
        linewidths=2,
        edgecolors="blue",
        linestyle="--",
        label="Probabilistic",
    )
    p3 = axis[0].scatter(
        *wiki_miss_ratio_write_amp["Probabilistic-FIFO-0.10"],
        marker=">",
        s=1280,
        color=colors[3],
        linewidths=2,
        edgecolors="grey",
        linestyle="dotted",
        label="Probabilistic",
    )

    f1 = axis[0].scatter(
        *wiki_miss_ratio_write_amp["Flashield-FIFO-0.001"],
        marker="v",
        s=1280,
        color=colors[1],
        linewidths=2,
        edgecolors="black",
        label="Flashield",
    )
    f2 = axis[0].scatter(
        *wiki_miss_ratio_write_amp["Flashield-FIFO-0.01"],
        marker="v",
        s=1280,
        color=colors[2],
        linewidths=2,
        edgecolors="blue",
        linestyle="--",
        label="Flashield",
    )
    f3 = axis[0].scatter(
        *wiki_miss_ratio_write_amp["Flashield-FIFO-0.10"],
        marker="v",
        s=1280,
        color=colors[3],
        linewidths=2,
        edgecolors="grey",
        linestyle="dotted",
        label="Flashield",
    )

    s1 = axis[0].scatter(
        *wiki_miss_ratio_write_amp["S3-FIFO-FIFO-2-0.001"],
        marker="*",
        s=1280,
        color=colors[1],
        linewidths=2,
        edgecolors="black",
        label="S3-FIFO",
    )
    s2 = axis[0].scatter(
        *wiki_miss_ratio_write_amp["S3-FIFO-FIFO-2-0.01"],
        marker="*",
        s=1280,
        color=colors[2],
        linewidths=2,
        edgecolors="blue",
        linestyle="--",
        label="S3-FIFO",
    )
    s3 = axis[0].scatter(
        *wiki_miss_ratio_write_amp["S3-FIFO-FIFO-2-0.10"],
        marker="*",
        s=1280,
        color=colors[3],
        linewidths=2,
        edgecolors="grey",
        linestyle="dotted",
        label="S3-FIFO",
    )

    # axis[0].set_yscale("log")
    axis[0].set_xticks(
        [
            0.2,
            0.3,
            0.4,
            0.5,
        ]
    )
    axis[0].set_xlabel("Miss ratio")
    axis[0].set_ylabel("Write bytes (normalized)")
    axis[0].grid(linestyle="--")

    fifo = axis[1].scatter(
        *tencentPhoto_miss_ratio_write_amp["FIFO"],
        marker="<",
        s=1280,
        color=colors[4],
        linewidths=2,
        edgecolors="grey",
        label="FIFO",
    )
    # fifor = axis[1].scatter(*tencentPhoto_miss_ratio_write_amp["FIFO-Reinsertion"], marker="^", s=1280, color=colors[0], linewidths=2, edgecolors="grey", label="FIFO-Reinsertion")

    p1 = axis[1].scatter(
        *tencentPhoto_miss_ratio_write_amp["Probabilistic-FIFO-0.001"],
        marker=">",
        s=1280,
        color=colors[1],
        linewidths=2,
        edgecolors="black",
        label="Probabilistic",
    )
    p2 = axis[1].scatter(
        *tencentPhoto_miss_ratio_write_amp["Probabilistic-FIFO-0.01"],
        marker=">",
        s=1280,
        color=colors[2],
        linewidths=2,
        edgecolors="blue",
        linestyle="--",
        label="Probabilistic",
    )
    p3 = axis[1].scatter(
        *tencentPhoto_miss_ratio_write_amp["Probabilistic-FIFO-0.10"],
        marker=">",
        s=1280,
        color=colors[3],
        linewidths=2,
        edgecolors="grey",
        linestyle="dotted",
        label="Probabilistic",
    )

    f1 = axis[1].scatter(
        *tencentPhoto_miss_ratio_write_amp["Flashield-FIFO-0.001"],
        marker="v",
        s=1280,
        color=colors[1],
        linewidths=2,
        edgecolors="black",
        label="Flashield",
    )
    f2 = axis[1].scatter(
        *tencentPhoto_miss_ratio_write_amp["Flashield-FIFO-0.01"],
        marker="v",
        s=1280,
        color=colors[2],
        linewidths=2,
        edgecolors="blue",
        linestyle="--",
        label="Flashield",
    )
    f3 = axis[1].scatter(
        *tencentPhoto_miss_ratio_write_amp["Flashield-FIFO-0.10"],
        marker="v",
        s=1280,
        color=colors[3],
        linewidths=2,
        edgecolors="grey",
        linestyle="dotted",
        label="Flashield",
    )

    s1 = axis[1].scatter(
        *tencentPhoto_miss_ratio_write_amp["S3-FIFO-FIFO-2-0.001"],
        marker="*",
        s=1280,
        color=colors[1],
        linewidths=2,
        edgecolors="black",
        label="S3-FIFO",
    )
    s2 = axis[1].scatter(
        *tencentPhoto_miss_ratio_write_amp["S3-FIFO-FIFO-2-0.01"],
        marker="*",
        s=1280,
        color=colors[2],
        linewidths=2,
        edgecolors="blue",
        linestyle="--",
        label="S3-FIFO",
    )
    s3 = axis[1].scatter(
        *tencentPhoto_miss_ratio_write_amp["S3-FIFO-FIFO-2-0.10"],
        marker="*",
        s=1280,
        color=colors[3],
        linewidths=2,
        edgecolors="grey",
        linestyle="dotted",
        label="S3-FIFO",
    )

    n = matplotlib.lines.Line2D([], [], color="none")

    axis[1].set_xticks(
        [
            0.2,
            0.4,
            0.6,
            0.8,
        ]
    )
    axis[1].set_xlabel("Miss ratio")
    axis[1].set_ylabel("Write bytes (normalized)")
    axis[1].grid(linestyle="--")

    axis[0].text(0.18, 4.76, "DRAM size 0.1%: ", fontsize=38)
    axis[0].text(0.18, 4.40, "DRAM size 1%: ", fontsize=38)
    axis[0].text(0.18, 4.04, "DRAM size 10%: ", fontsize=38)
    axis[0].text(0.18, 3.68, "DRAM size agostic (no admission policy): ", fontsize=38)

    axis[0].legend(
        handles=[
            p1,
            p2,
            p3,
            n,
            f1,
            f2,
            f3,
            fifo,
            s1,
            s2,
            s3,
        ],
        ncol=3,
        loc="upper left",
        bbox_to_anchor=(0.704, 1.504),
        frameon=False,
        fontsize=40,
        columnspacing=1.2,
        handletextpad=0.2,
    )
    # plt.legend(handles=legends, ncol=3, loc="upper left", bbox_to_anchor=(-0.16, 1.28), frameon=False, fontsize=28, columnspacing=0.48, handletextpad=0.2)
    plt.savefig("write_amp.pdf", bbox_inches="tight")
    plt.clf()


if __name__ == "__main__":
    plot_write_amp()
