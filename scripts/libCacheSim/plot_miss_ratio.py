import os
import sys
import logging
import itertools

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
import numpy as np
import glob
from collections import defaultdict
from load_miss_ratio_data import load_data, load_miss_ratio_reduction_from_dir
import matplotlib.pyplot as plt
from utils import update_algo_name, update_dataset_name

logger = logging.getLogger("plot_miss_ratio")
logger.setLevel(logging.INFO)


def plot_scatter(datapath, size_idx=0, metric="miss_ratio"):
    algo_list = [
        "S3FIFO",
        "ARC",
        "TwoQ",
        "WTinyLFU-w0.10-SLRU",
        "LIRS",
        "Cacheus",
        "LHD",
    ]

    name_list = [update_algo_name(algo) for algo in algo_list]
    markers = itertools.cycle("<>^osp**")
    colors = itertools.cycle(
        reversed(
            [
                "#b2182b",
                "#ef8a62",
                "#fddbc7",
                "#f7f7f7",
                "#d1e5f0",
                "#67a9cf",
                "#2166ac",
            ]
        )
    )

    datasets = os.listdir(datapath)
    print(datasets)

    datasets = [
        "FIU",
        "MSR",
        "Cloudphysics",
        "SYSTOR",
        "TencentBlock",
        "AlibabaBlock",
        "SocialNetwork1",
        "meta_kv",
        "Twitter",
        "CDN1",
        "CDN2",
        "TencentPhoto",
        "meta_cdn",
        "Wiki",
    ]

    dataset_to_mr_reduction = {}
    plt.figure(figsize=(28, 10.8))
    for dataset in datasets:
        mr_reduction_dict_list = load_miss_ratio_reduction_from_dir(
            "{}/{}".format(datapath, dataset), algo_list, metric
        )
        dataset_to_mr_reduction[dataset] = mr_reduction_dict_list

    for dataset in datasets:
        if len(dataset_to_mr_reduction[dataset]) == 0:
            raise RuntimeError("dataset {} does not have data".format(dataset))

    for algo in reversed(algo_list):
        logger.debug(
            "{:48} {} data loaded".format(
                algo,
                [
                    len(dataset_to_mr_reduction[dataset][size_idx][algo])
                    for dataset in datasets
                ],
            )
        )
        y = [
            np.mean(dataset_to_mr_reduction[dataset][size_idx][algo])
            for dataset in datasets
        ]

        edgecolor = "black" if algo == "S3FIFO-d" or algo == "S3FIFO" else "none"
        edgecolor = "grey"
        s = 1080 if algo == "S3FIFO-d" or algo == "S3FIFO" else 800
        plt.scatter(
            y,
            np.arange(len(y)),
            label=update_algo_name(algo),
            marker=next(markers),
            color=next(colors),
            s=s,
            edgecolor=edgecolor,
            linewidths=2,
            alpha=1.0,
        )

    # plt.text(-0.032, 5.64, "<---LIRS -0.05", fontsize=28, )
    # if size_idx == 0:
    #     plt.text(-0.032, 7.64, "<---TinyLFU -0.14", fontsize=28, )
    #     plt.xlim(left=-0.04)
    if size_idx == 2:
        #     plt.text(-0.063, 11.72, "<---TinyLFU -0.11", fontsize=28, )
        plt.xlim(left=-0.02)
    # elif size_idx == 1:
    #     pass

    # plt.legend(ncol=8, loc="upper left", fontsize=28, bbox_to_anchor=(0, 1.2), frameon=False)
    handles, labels = plt.gca().get_legend_handles_labels()
    plt.gca().legend(
        handles[::-1],
        labels[::-1],
        ncol=8,
        loc="upper left",
        fontsize=38,
        markerscale=1.2,
        handletextpad=0.00,
        columnspacing=0.80,
        bbox_to_anchor=(-0.028, 1.16),
        frameon=False,
    )
    plt.yticks(
        range(len(datasets)),
        [update_dataset_name(name) for name in datasets],
        rotation=0.20,
        fontsize=38,
    )
    plt.xticks(fontsize=42)
    plt.ylim(-0.5, len(datasets) - 0.5)

    xlim = plt.xlim()
    plt.xlim(xlim)
    for i in range(len(datasets)):
        if i % 2 == 0:
            alpha = 0.16
        else:
            alpha = 0
        plt.fill_between(xlim, y1=i - 0.5, y2=i + 0.5, color="gray", alpha=alpha)

    if metric == "byte_miss_ratio":
        plt.xlabel("Byte miss ratio reduction from FIFO", fontsize=42)
    else:
        plt.xlabel("Miss ratio reduction from FIFO", fontsize=42)
    plt.grid(axis="x", linestyle="--", linewidth=1, alpha=0.5)
    plt.savefig("{}_per_dataset_{}.pdf".format(metric, size_idx), bbox_inches="tight")
    plt.close()
    plt.clf()


def plot_percentiles(datapath, size_idx=0, metric="miss_ratio"):
    """
    plot the median, mean, 90th percentile of miss ratio reduction

    Args:
        datapath (str): path to result data
    """

    algo_list = [
        "S3FIFO",
        "WTinyLFU-w0.01-SLRU",
        "WTinyLFU-w0.10-SLRU",
        "LIRS",
        "TwoQ",
        "S4LRU(25:25:25:25)",
        "ARC",
        "Cacheus",
        "LeCaR",
        "LHD",
        "FIFO_Merge_FREQUENCY",
        "Clock",
        "B-LRU",
        "LRU",
    ]

    name_list = [update_algo_name(algo) for algo in algo_list]

    markers = itertools.cycle("<^osv>v*p")
    # colors = itertools.cycle(["#d73027", "#fc8d59", "#fee090", "#e0f3f8", "#91bfdb", "#4575b4", ])
    colors = itertools.cycle(
        reversed(["#b2182b", "#ef8a62", "#fddbc7", "#d1e5f0", "#67a9cf", "#2166ac"])
    )

    mr_reduction_dict_list = load_miss_ratio_reduction_from_dir(
        datapath, algo_list, metric
    )

    plt.figure(figsize=(28, 8))

    # print([len(mr_reduction_dict_list[size_idx][algo]) for algo in algo_list])
    y = [
        np.percentile(mr_reduction_dict_list[size_idx][algo], 10) for algo in algo_list
    ]
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
        np.percentile(mr_reduction_dict_list[size_idx][algo], 90) for algo in algo_list
    ]
    plt.scatter(
        range(len(y)), y, label="P90", marker=next(markers), color=next(colors), s=480
    )

    # y = [
    #     np.max(mr_reduction_dict_list[size_idx][algo]) for algo in algo_list
    # ]
    # plt.scatter(
    #     range(len(y)), y, label="Max", marker=next(markers), color=next(colors), s=480
    # )

    # y = [
    #     np.min(mr_reduction_dict_list[size_idx][algo]) for algo in algo_list
    # ]
    # plt.scatter(
    #     range(len(y)), y, label="Min", marker=next(markers), color=next(colors), s=480
    # )

    if plt.ylim()[0] < -0.1:
        plt.ylim(bottom=-0.04)

    plt.xticks(range(len(algo_list)), name_list, fontsize=32, rotation=28)
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


def compare_two_algo_miss_ratio(datapath, algo1, algo2, size_idx_list=(0, 1, 2, 3)):
    mr_reduction_list = []

    for f in sorted(glob.glob(datapath + "/*")):
        # a list of miss ratio dict (algo -> miss ratio) at different cache sizes
        miss_ratio_dict_list = load_data(f)
        for size_idx in size_idx_list:
            mr_dict = miss_ratio_dict_list[size_idx]
            if len(mr_dict) == 0:
                continue
            mr1 = mr_dict.get(algo1, 2)
            mr2 = mr_dict.get(algo2, 2)

            if mr1 == 2 or mr2 == 2:
                # print(f)
                continue

            if mr1 == 0:
                if mr2 != 0:
                    print(f, size_idx, mr1, mr2)
                continue

            mr_reduction_list.append((mr1 - mr2) / mr1)

    print(
        "{}/{}".format(
            sum([1 for x in mr_reduction_list if x > 0]), len(mr_reduction_list)
        )
    )

    print(
        f"{algo1:32} {algo2:32}: miss ratio reduction mean: {np.mean(mr_reduction_list):.4f}, median: {np.median(mr_reduction_list):.4f}, \
        max: {np.max(mr_reduction_list):.4f}, min: {np.min(mr_reduction_list):.4f}, P10, P90: {np.percentile(mr_reduction_list, (10, 90))}"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--datapath", type=str, help="path to the cachesim result")
    ap = parser.parse_args()

    plot_scatter(ap.datapath, size_idx=0, metric="miss_ratio")
    plot_scatter(ap.datapath, size_idx=2, metric="miss_ratio")

    plot_percentiles("{}/all".format(ap.datapath), size_idx=0, metric="miss_ratio")
    plot_percentiles("{}/all".format(ap.datapath), size_idx=2, metric="miss_ratio")
