import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from pyutils.common import *
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, AutoMinorLocator


def load_eviction_stat(datapath):
    """
    load eviction age and freq from the libCacheSim output file

    """

    # obj -> eviction age list
    ea_dict = defaultdict(list)

    # count of (frequency at each eviction)
    freq_dict = defaultdict(int)

    ifile = open(datapath, "r")

    # skip the first 1/4 of the file because the cache is not warm up
    ifile.seek(os.stat(datapath).st_size // 4)
    ifile.readline()

    for line in ifile:
        if line.startswith("ea: "):
            line = line.strip().split()
            obj, eviction_age = int(line[1]), int(line[2])
            raise RuntimeError("ea: is not supported")
        elif line.startswith("ea_freq:"):
            line = line.strip().split()
            obj, eviction_age, freq = int(line[1]), int(line[2]), int(line[3]) + 1
            freq_dict[freq] += 1
        elif line[0].isdigit():
            # ts: obj evicttion_age freq
            obj, eviction_age_str, freq_str = line.strip().split(":")[1].split()
            eviction_age = int(eviction_age_str)
            freq = int(freq_str) + 1
            freq_dict[freq] += 1
        else:
            continue
        ea_dict[obj].append(eviction_age)

    ifile.close()

    return ea_dict, freq_dict


def cal_eviction_freq_frac(freq_dict_list):
    """
    load the frequency of objects at eviction time and
    calculate the fraction of frequency one, two and more than two

    freq_dict_list: a list of freq_dict

    """

    plot_data = [[], [], []]

    for freq_dict in freq_dict_list:
        # each freq_dict is an algo
        # 1, 2, 2+
        cnt_list = [
            0,
            0,
            0,
        ]
        for freq, cnt in freq_dict.items():
            if freq == 1:
                cnt_list[0] += cnt
            elif freq == 2:
                cnt_list[1] += cnt
            else:
                cnt_list[len(cnt_list) - 1] += cnt

        cnt_list = np.array(cnt_list)
        cnt_list = cnt_list / np.sum(cnt_list)

        plot_data[0].append(cnt_list[0])
        plot_data[1].append(cnt_list[1])
        plot_data[2].append(cnt_list[2])

    return plot_data


def plot_eviction_freq(freq_dict_list_list, name_list, size_list, dataname):
    """
    plot the eviction frequency (the frequency of objects at eviction)

    freq_dict_list_list: a list of freq_dict_list,
            each freq_dict_list corresponds to one size and is a list of freq_dict
            each freq_dict corresponds to an algo and freq to count
    """

    COLOR_THREE = [
        "#43a2ca",
        "#a8ddb5",
        "#e0f3db",
    ]
    COLOR_THREE = [
        "#2166ac",
        "#67a9cf",
        "#d1e5f0",
        "#b2182b",
        "#ef8a62",
        "#fddbc7",
    ]

    fig, ax = plt.subplots(figsize=(10.8, 8))
    space_between_bars = 1
    xticks, xtick_labels = [], []
    for idx, freq_dict_list in enumerate(freq_dict_list_list):
        plot_data = cal_eviction_freq_frac(freq_dict_list)
        # print(plot_data)

        bottom_list = np.array([0.0 for _ in range(len(name_list))])
        x = np.arange(len(name_list)) + (len(name_list) + space_between_bars) * idx
        xticks.extend(list(x))
        xtick_labels.extend(name_list)

        p1 = plt.bar(
            x,
            plot_data[0],
            bottom=bottom_list,
            alpha=0.64,
            width=0.64,
            # hatch="-",
            color=COLOR_THREE[0],
            label="Freq 1",
        )
        bottom_list += np.array(plot_data[0])
        p2 = plt.bar(
            x,
            plot_data[1],
            bottom=bottom_list,
            alpha=0.64,
            width=0.64,
            hatch="+",
            color=COLOR_THREE[1],
            label="Freq 2",
        )
        bottom_list += np.array(plot_data[1])
        p3 = plt.bar(
            x,
            plot_data[2],
            bottom=bottom_list,
            alpha=0.64,
            width=0.64,
            hatch="x",
            color=COLOR_THREE[2],
            label="Freq 2+",
        )
        bottom_list += np.array(plot_data[2])

    plt.xticks(
        np.arange(len(size_list)) * (len(name_list) + space_between_bars)
        + (len(name_list) - 1) / 2,
        [str(s) for s in size_list],
    )
    # print([str(s) for s in size_list])
    # plt.xticks(xticks, xtick_labels, fontsize=32)
    plt.xticks(fontsize=32)
    plt.yticks(fontsize=32)
    plt.xlabel("Cache size (fraction of objects in the trace)", fontsize=32)
    plt.ylabel("Fraction of evicted objects", fontsize=38)
    plt.legend(
        handles=list([p1, p2, p3]),
        loc="upper left",
        bbox_to_anchor=(-0.064, 1.16),
        labelspacing=0.2,
        columnspacing=1.2,
        ncol=3,
        frameon=False,
    )
    plt.ylim(-0.024, 1.028)
    plt.grid(linestyle="--", axis="y")
    plt.savefig("eviction_freq_{}.pdf".format(dataname), bbox_inches="tight")
    plt.clf()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--datapath", type=str, nargs="+", help="path to the eviction stat data file"
    )
    parser.add_argument("--figname", default="", type=str, help="figname of the plot")

    ap = parser.parse_args()

    algo_list, size_list, freq_dict_list = [], [], []
    for datapath in ap.datapath:
        ns = os.path.basename(datapath).split("_")
        dataname = "_".join(ns[:-2])
        algo, cache_size = ns[-2], float(ns[-1])

        algo_list.append(algo)
        size_list.append(cache_size)
        ea_dict, freq_dict = load_eviction_stat(datapath)
        freq_dict_list.append(freq_dict)

    n_algo = len(set(algo_list))
    n_size = len(set(size_list))
    print(
        "{}: {} data {} names {} sizes".format(
            dataname, len(freq_dict_list), n_algo, n_size
        )
    )
    assert (
        len(freq_dict_list) == n_algo * n_size
    ), "data size not match {} != {} * {}".format(len(freq_dict_list), n_algo, n_size)

    algo_list = algo_list[:n_algo]
    size_list = size_list[::n_algo]
    print(algo_list, size_list)

    freq_dict_list_list = []
    for i in range(n_size):
        freq_dict_list_list.append([])
        for k in range(n_algo):
            freq_dict_list_list[-1].append(freq_dict_list[i * n_algo + k])

    plot_eviction_freq(freq_dict_list_list, algo_list, size_list, ap.figname if ap.figname else dataname)

