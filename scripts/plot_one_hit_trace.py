import os
import sys
import logging
import itertools

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pyutils.common import get_linestyles
from utils import get_name, filename_to_dataset
import struct
import pickle
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt

logger = logging.getLogger("oneHit")
logger.setLevel(logging.WARN)

colors = [
    "#b2182b",
    "#2166ac",
]

if not os.path.exists(".oneHit"):
    os.mkdir(".oneHit")


def cal_one_hit_ratio(datapath, n_obj_list, n_skip=0):
    """calculate the one hit ratio for the first n_obj_list objects in the trace"""

    pickle_path = ".oneHit/{}.pickle".format(os.path.basename(datapath))
    if os.path.exists(pickle_path):
        print("load {}".format(pickle_path))
        n_one_hit_list, n_req_list = pickle.load(open(pickle_path, "rb"))
        return np.array(n_one_hit_list)

    print("calculate {}".format(pickle_path))
    n_one_hit_list, n_req_list = [], []

    pos_in_n_obj_list = 0
    n_one_hit_count, n_req = 0, 0

    if n_skip == -1:
        # skip at least one day of requests because the beginning of some traces
        # have weird patterns due to log collection issues
        n_skip = os.stat(datapath).st_size // 24 // 5

    obj_freq = defaultdict(int)
    with open(datapath, "rb") as f:
        # each request is 24 bytes
        bin_data = f.read(24)
        for _ in range(n_skip):
            bin_data = f.read(24)

        while bin_data:
            ts, obj_id, size, next_access_vtime = struct.unpack("<IQIQ", bin_data)
            n_req += 1
            bin_data = f.read(24)
            if obj_freq[obj_id] == 0:
                n_one_hit_count += 1
            elif obj_freq[obj_id] == 1:
                n_one_hit_count -= 1
            obj_freq[obj_id] += 1
            if len(obj_freq) == n_obj_list[pos_in_n_obj_list]:
                n_one_hit_list.append(n_one_hit_count)
                n_req_list.append(n_req)
                pos_in_n_obj_list += 1
                if pos_in_n_obj_list == len(n_obj_list):
                    break

    with open(pickle_path, "wb") as f:
        pickle.dump((n_one_hit_list, n_req_list), f)

    return np.array(n_one_hit_list)


def plot_one_hit_ratio(datapath_list, name_list, xscale="linear"):
    """
    plot the one-hit-wonder ratio for the datasets
    it calculates the one-hit-wonder ratio if we have not calculated it before

    """

    linestyles = itertools.cycle(get_linestyles())

    i = 0
    for datapath, name in zip(datapath_list, name_list):
        n_obj_list = np.array([int(1.08**i) for i in range(40, 1280)])
        n_one_hit_list = cal_one_hit_ratio(datapath, n_obj_list, n_skip=-1)

        n_obj_list = n_obj_list[: len(n_one_hit_list)]
        x = n_obj_list / n_obj_list[-1]
        y = n_one_hit_list / n_obj_list

        if xscale == "log":
            # we don't want x-axis to show only small values
            start_idx = np.searchsorted(x, 8 * 1e-4)
            x = x[start_idx:]
            y = y[start_idx:]

        plt.plot(x, y, linestyle=next(linestyles), color=colors[i], label=name)
        i += 1

    plt.ylim(0, 1.08)
    if xscale == "log":
        plt.xscale("log")
        figname = "one_hit_ratio_log.pdf"
    else:
        figname = "one_hit_ratio.pdf"

    plt.grid(linestyle="--")
    plt.legend(
        ncol=2,
        frameon=False,
        edgecolor="black",
        markerscale=0.5,
    )
    plt.xlabel("Fraction of objects in the trace")
    plt.ylabel("One-hit-wonder ratio")
    plt.savefig(figname, bbox_inches="tight")

    plt.clf()


################## process the one hit ratio for alll traces ##################
def cal_one_hit_per_dataset(datapath):
    """
    this process the one hit ratio calculation from libCacheSim traceAnalysis
    it calculates the one-hit-wonder ratio for each dataset

    """

    one_hit_ratio_per_dataset_complete = defaultdict(list)
    one_hit_ratio_per_dataset_50 = defaultdict(list)
    one_hit_ratio_per_dataset_20 = defaultdict(list)
    one_hit_ratio_per_dataset_10 = defaultdict(list)
    one_hit_ratio_per_dataset_1 = defaultdict(list)
    one_hit_ratio_per_dataset_01 = defaultdict(list)

    with open(datapath, "r") as ifile:
        for line in ifile:
            if len(line) < 100:
                continue
            dataname, one_hit_ratio_str = line.strip(",\n").split(":")
            dataset = filename_to_dataset(os.path.basename(dataname))
            one_hit_ratio_list = np.array(
                [float(x) for x in one_hit_ratio_str.split(",")]
            )
            n = one_hit_ratio_list.shape[0]
            if n < 100:
                continue
            one_hit_ratio_complete = one_hit_ratio_list[-1]
            one_hit_ratio_50 = one_hit_ratio_list[n // 2]
            one_hit_ratio_20 = one_hit_ratio_list[n // 5]
            one_hit_ratio_10 = one_hit_ratio_list[n // 10]
            one_hit_ratio_1 = one_hit_ratio_list[n // 100]
            one_hit_ratio_01 = one_hit_ratio_list[n // 1000]
            one_hit_ratio_per_dataset_complete[dataset].append(one_hit_ratio_complete)
            one_hit_ratio_per_dataset_50[dataset].append(one_hit_ratio_50)
            one_hit_ratio_per_dataset_20[dataset].append(one_hit_ratio_20)
            one_hit_ratio_per_dataset_10[dataset].append(one_hit_ratio_10)
            one_hit_ratio_per_dataset_1[dataset].append(one_hit_ratio_1)
            one_hit_ratio_per_dataset_01[dataset].append(one_hit_ratio_01)

    print("========= one-hit-wonder-ratio =========")
    print("dataset, complete, 50%, 20%, 10%, 1%")
    for dataset in one_hit_ratio_per_dataset_complete:
        print(
            "{:8}, {:8.4f}, {:8.4f}, {:8.4f}, {:8.4f}, {:8.4f}".format(
                dataset,
                np.mean(one_hit_ratio_per_dataset_complete[dataset]),
                np.mean(one_hit_ratio_per_dataset_50[dataset]),
                np.mean(one_hit_ratio_per_dataset_20[dataset]),
                np.mean(one_hit_ratio_per_dataset_10[dataset]),
                np.mean(one_hit_ratio_per_dataset_1[dataset]),
            )
        )


def plot_one_hit_all_trace(datapath):
    """
    plot the one-hit-wonder ratio for all traces,
    the data is generated from libCachesim traceAnalysis

    """

    metadata_name = ".oneHit.pickle"
    if os.path.exists(metadata_name):
        print("load {}".format(metadata_name))
        one_hit_ratio_dict = pickle.load(open(metadata_name, "rb"))
    else:
        ifile = open(datapath, "r")
        one_hit_ratio_dict = {}  # key: trace name, value: one hit ratio list
        for line in ifile:
            if len(line) < 100:
                continue
            dataname, one_hit_ratio_str = line.strip(",\n").split(":")
            # print(dataname, len(one_hit_ratio_str))
            one_hit_ratio_list = np.array(
                [float(x) for x in one_hit_ratio_str.split(",")]
            )
            if one_hit_ratio_list.shape[0] < 100:
                continue
            one_hit_ratio_list = one_hit_ratio_list[
                :: one_hit_ratio_list.shape[0] // 100
            ]
            assert (
                40 <= len(one_hit_ratio_list) <= 200
            ), "len(one_hit_ratio_list) != 100 {}".format(len(one_hit_ratio_list))
            print(
                get_name(datapath),
                one_hit_ratio_list[0],
                one_hit_ratio_list[24],
                one_hit_ratio_list[49],
                one_hit_ratio_list[74],
                one_hit_ratio_list[99],
            )
            one_hit_ratio_dict[dataname] = one_hit_ratio_list

        pickle.dump(one_hit_ratio_dict, open(metadata_name, "wb"))

        ifile.close()

    # np.set_printoptions(precision=4, suppress=True)

    print(
        "==============================================================="
    )
    print(
        "fraction of all objects in the trace                           " + 
        "{:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f}".format(
            0.01, 0.1, 0.25, 0.5, 0.75, 1.00
        )
    )
    print(
        "mean one-hit-wonder ratio increase compared to full trace      " + 
        "{:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f}".format(
            np.mean(
                [l[len(l) // 100 * 1] / l[-1] for l in one_hit_ratio_dict.values()]
            ),
            np.mean([l[len(l) // 10 * 1] / l[-1] for l in one_hit_ratio_dict.values()]),
            np.mean([l[len(l) // 4 * 1] / l[-1] for l in one_hit_ratio_dict.values()]),
            np.mean([l[len(l) // 4 * 2] / l[-1] for l in one_hit_ratio_dict.values()]),
            np.mean([l[len(l) // 4 * 3] / l[-1] for l in one_hit_ratio_dict.values()]),
            np.mean([l[-1] / l[-1] for l in one_hit_ratio_dict.values()]),
        )
    )

    print(
        "median one-hit-wonder ratio increase compared to full trace    " + 
        "{:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f}".format(
            np.median(
                [l[len(l) // 100 * 1] / l[-1] for l in one_hit_ratio_dict.values()]
            ),
            np.median(
                [l[len(l) // 10 * 1] / l[-1] for l in one_hit_ratio_dict.values()]
            ),
            np.median(
                [l[len(l) // 4 * 1] / l[-1] for l in one_hit_ratio_dict.values()]
            ),
            np.median(
                [l[len(l) // 4 * 2] / l[-1] for l in one_hit_ratio_dict.values()]
            ),
            np.median(
                [l[len(l) // 4 * 3] / l[-1] for l in one_hit_ratio_dict.values()]
            ),
            np.median([l[-1] / l[-1] for l in one_hit_ratio_dict.values()]),
        )
    )

    print(
        "mean one-hit-wonder ratio                                      " + 
        "{:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f}".format(
            np.mean([l[len(l) // 100 * 1] for l in one_hit_ratio_dict.values()]),
            np.mean([l[len(l) // 10 * 1] for l in one_hit_ratio_dict.values()]),
            np.mean([l[len(l) // 4 * 1] for l in one_hit_ratio_dict.values()]),
            np.mean([l[len(l) // 4 * 2] for l in one_hit_ratio_dict.values()]),
            np.mean([l[len(l) // 4 * 3] for l in one_hit_ratio_dict.values()]),
            np.mean([l[-1] for l in one_hit_ratio_dict.values()]),
        )
    )

    print(
        "median one-hit-wonder ratio                                    " + 
        "{:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f}".format(
            np.median([l[len(l) // 100 * 1] for l in one_hit_ratio_dict.values()]),
            np.median([l[len(l) // 10 * 1] for l in one_hit_ratio_dict.values()]),
            np.median([l[len(l) // 4 * 1] for l in one_hit_ratio_dict.values()]),
            np.median([l[len(l) // 4 * 2] for l in one_hit_ratio_dict.values()]),
            np.median([l[len(l) // 4 * 3] for l in one_hit_ratio_dict.values()]),
            np.median([l[-1] for l in one_hit_ratio_dict.values()]),
        )
    )

    meanprops = dict(
        marker="v",
        markerfacecolor="g",
        markersize=24,
        linestyle="none",
        markeredgecolor="r",
    )
    plt.figure(figsize=(28, 8))
    positions = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
    ]
    bplot = plt.boxplot(
        [
            [l[len(l) // 1000 * 1] for l in one_hit_ratio_dict.values()],
            [l[len(l) // 100 * 1] for l in one_hit_ratio_dict.values()],
            [l[len(l) // 50 * 1] for l in one_hit_ratio_dict.values()],
            [l[len(l) // 20 * 1] for l in one_hit_ratio_dict.values()],
            [l[len(l) // 10 * 1] for l in one_hit_ratio_dict.values()],
            [l[len(l) // 5 * 1] for l in one_hit_ratio_dict.values()],
            [l[len(l) // 2 * 1] for l in one_hit_ratio_dict.values()],
            [l[len(l) // 1 * 1 - 1] for l in one_hit_ratio_dict.values()],
        ],
        positions=positions,
        whis=(10, 90),
        showfliers=False,
        vert=True,
        showmeans=True,
        meanprops=meanprops,
        medianprops=dict(color="black", linewidth=1.6),
        labels=[
            0.001,
            0.01,
            0.02,
            0.05,
            0.1,
            0.2,
            0.5,
            1.0,
        ],
    )

    # plt.xlabel("Request sequence length (in #objects in the sequence / #objects in the trace)")
    plt.xlabel("Fraction of objects in the trace", fontsize=48)
    plt.xticks(fontsize=42)
    plt.yticks(fontsize=42)
    plt.ylabel("One-hit-wonder ratio", fontsize=48)
    plt.grid(linestyle="--")
    plt.savefig("{}".format("one_hit.pdf"), bbox_inches="tight")
    plt.close()
    plt.clf()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--datapath", nargs="+")
    p.add_argument("--name", nargs="+")
    p.add_argument("--plotbox", action="store_true")
    p.add_argument("--calperdataset", action="store_true")

    ap = p.parse_args()

    if ap.plotbox:
        plot_one_hit_all_trace(ap.datapath[0])
    elif ap.calperdataset:
        cal_one_hit_per_dataset(ap.datapath[0])
    else:
        if ap.name is None:
            ap.name = [get_name(datapath) for datapath in ap.datapath]
        plot_one_hit_ratio(ap.datapath, ap.name)
        plot_one_hit_ratio(ap.datapath, ap.name, xscale="log")
