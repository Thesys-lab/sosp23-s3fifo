import os
import sys
import re
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from pyutils.common import *

regex = re.compile(r"working set size: (?P<wss_obj>\d+) object (?P<wss_byte>\d+) byte")
regex2 = re.compile(
    r"(?P<datapath>.+?)\s+(?P<algo>.+?) cache size\s+(?P<cache_size>.+?),\s+(?P<n_req>\d+) req, miss ratio (?P<miss_ratio>0\.\d+), throughput (?P<xput>\d+.\d+) MQPS"
)


def cal_demotion_speed_and_accuracy(datapath):
    """
    this parses the libCacheSim demotion output (enable TRACK_DEMOTION in libCacheSim/config.h)
    and prints the stat for plot

    """

    dataname = os.path.basename(datapath)
    s = dataname.split("_")
    dataname, algo, cache_size = "_".join(s[:-2]), s[-2], s[-1]

    ifile = open(datapath, "r")
    # find working set size
    line = ifile.readline()
    line = ifile.readline()
    m = regex.search(line)
    assert m is not None, "cannot find wss in line {} {}".format(line, datapath)
    cache_size = int(int(m.group("wss_obj")) * float(cache_size))
    # find the miss ratio
    ifile.seek(os.stat(datapath).st_size - 160, 0)
    miss_ratio = -1
    for line in ifile:
        m = regex2.search(line)
        if m:
            miss_ratio = float(m.group("miss_ratio"))

    assert miss_ratio != -1, "cannot find miss ratio in file {}".format(datapath)
    # print("working set size: {} object, miss ratio: {}".format(cache_size, miss_ratio))

    # next access distance larger than n_req_threshold will be considered as correct to demote
    n_req_threshold = int(cache_size / miss_ratio)

    # rewind to 1/4 of the file, and skip the first 1/4 which the cache is not warmed up
    # right after the cache is full, we will see a lot of objects with large ages being demoted
    ifile.seek(os.stat(datapath).st_size // 4, 0)
    ifile.readline()

    pos = ifile.tell()
    demotion_age_list = []
    n_correct_keep, n_correct_demote = 0, 0
    n_incorrect_keep, n_incorrect_demote = 0, 0
    for line in ifile:
        pos += len(line)
        # skip the end of traces, at which objects have no future access
        if pos > os.stat(datapath).st_size // 4 * 3:
            break

        if line.startswith("\x1b"):
            continue
        try:
            curr_vtime, op, create_vtime, next_access_vtime = line.strip().split()
        except Exception as e:
            # print("line: {} error {}".format(line, e))
            continue

        # print(line, curr_vtime, op, create_vtime, next_access_vtime)
        assert int(curr_vtime) >= int(
            create_vtime
        ), "curr_vtime {} < create_vtime {} line {} file {}".format(
            curr_vtime, create_vtime, line, datapath
        )

        # print(curr_vtime, op, create_vtime, next_access_vtime)

        if op == "keep":
            if int(next_access_vtime) < int(curr_vtime) + n_req_threshold:
                n_correct_keep += 1
            else:
                n_incorrect_keep += 1
        elif op == "demote":
            demotion_age_list.append(int(curr_vtime) - int(create_vtime))
            if int(next_access_vtime) > int(curr_vtime) + n_req_threshold:
                n_correct_demote += 1
            else:
                n_incorrect_demote += 1
        else:
            raise Exception("Unknown op: {}".format(op))

    demotion_age_list = np.array(demotion_age_list)
    print(
        "{:16} {:16} size {:8}, miss ratio {:.4f}, demotion age mean {:8}, median {:8}, std {:8}".format(
            dataname,
            algo,
            cache_size,
            miss_ratio,
            np.mean(demotion_age_list).astype(int),
            np.median(demotion_age_list).astype(int),
            np.std(demotion_age_list).astype(int),
        ),
        end=", ",
    )
    # print(
    #     "n_correct_keep {}, n_incorrect_keep {}, n_correct_demote {}, n_incorrect_demote {}"
    #     .format(n_correct_keep, n_incorrect_keep, n_correct_demote,
    #             n_incorrect_demote))
    # print(
    #     "n_correct_keep {:8} {:.4f}, n_incorrect_keep {:8} {:.4f}, n_correct_demote {:8} {:.4f}, n_incorrect_demote {:8} {:.4f}"
    #     .format(n_correct_keep,
    #             n_correct_keep / (n_correct_keep + n_incorrect_keep + 1),
    #             n_incorrect_keep,
    #             n_incorrect_keep / (n_correct_keep + n_incorrect_keep + 1),
    #             n_correct_demote,
    #             n_correct_demote / (n_correct_demote + n_incorrect_demote),
    #             n_incorrect_demote,
    #             n_incorrect_demote / (n_correct_demote + n_incorrect_demote)))
    print(
        "n_correct_demote {:.0f} {:.4f}, n_incorrect_demote {:.0f}/{:.0f} {:.4f}".format(
            n_correct_demote / 1000,
            n_correct_demote / (n_correct_demote + n_incorrect_demote + 1),
            n_incorrect_demote / 1000,
            (n_correct_demote + n_incorrect_demote) / 1000,
            n_incorrect_demote / (n_correct_demote + n_incorrect_demote + 1),
            # n_correct_demote / (n_correct_demote + n_incorrect_keep)
        )
    )

    ifile.close()


colors = [
    "#b2182b",
    "#ef8a62",
    "#fddbc7",
    "#f7f7f7",
    "#d1e5f0",
    "#67a9cf",
    "#2166ac",
]
colors = [
    # "#ef8a62",
    "#b2182b",
    "#f7f7f7",
    # "#67a9cf",
    "#2166ac",
]
colors1 = list(
    reversed(
        [
            "#fee5d9",
            "#fcbba1",
            "#fc9272",
            "#fb6a4a",
            "#ef3b2c",
            "#cb181d",
            "#99000d",
        ]
    )
)
colors2 = list(
    reversed(
        [
            "#eff3ff",
            "#c6dbef",
            "#9ecae1",
            "#6baed6",
            "#4292c6",
            "#2171b5",
            "#084594",
        ]
    )
)


def load_demotion_result(datafile):
    regex = re.compile(
        r"(?P<dataname>.+?)\s+(?P<algo>.+?)\s+size\s+(?P<cachesize>\d+), miss ratio (?P<miss_ratio>\d\.\d+), demotion age mean\s+(?P<age_mean>\d+), median\s+(?P<age_median>\d+), std\s+(\d+), n_correct_demote (?P<correct_demote>\d+) (?P<correct_demote_ratio>\d\.\d+?), n_incorrect_demote (?P<incorrect_demote>\d+)/(?P<total_demote>\d+) (?P<incorrect_demote_ratio>\d\.\d+)"
    )

    # {dataname => {algo => {miss ratio,
    #                        demotion age mean,
    #                        demotion age median,
    #                        n total demotions,
    #                        incorrect demotion ratio
    #                       }
    #               }
    # }
    data_dict = {}
    with open(datafile, "r") as ifile:
        for line in ifile:
            m = regex.search(line)
            if m is None:
                print("line: {} does not match in file {}".format(line, datafile))
                continue
            if m.group("dataname") not in data_dict:
                data_dict[m.group("dataname")] = {}
            data_dict[m.group("dataname")][m.group("algo")] = {
                "miss_ratio": float(m.group("miss_ratio")),
                "age_mean": int(m.group("age_mean")),
                "age_median": int(m.group("age_median")),
                "total_demote": int(m.group("total_demote")),
                "incorrect_demote_ratio": float(m.group("incorrect_demote_ratio")),
            }

    return data_dict


def plot_demotion(datapath, dataname):
    data_dict = load_demotion_result(datapath)

    handles = []
    s1 = plt.axvline(x=1, color="grey", linestyle="--", label="LRU")
    s2 = plt.scatter(
        data_dict[dataname]["lru"]["age_mean"] / data_dict[dataname]["arc"]["age_mean"],
        1 - data_dict[dataname]["arc"]["incorrect_demote_ratio"],
        marker="s",
        s=640,
        color=colors[1],
        edgecolor="grey",
        linewidth=1.6,
        label="ARC",
    )
    handles.append(s1)
    handles.append(s2)

    x, y = [], []
    a = 1
    idx = 0
    for i in (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4):
        x.append(
            data_dict[dataname]["lru"]["age_mean"]
            / data_dict[dataname]["wtinylfu-{}".format(i)]["age_mean"]
        )
        y.append(data_dict[dataname]["wtinylfu-{}".format(i)]["incorrect_demote_ratio"])
        s = 1280 if i == 0.10 else 640
        lw = 3.2 if i == 0.10 else 0.8
        s3 = plt.scatter(
            x[-1],
            1 - y[-1],
            #  alpha=a,
            marker="<",
            s=s,
            linewidths=lw,
            edgecolor="blue",
            #  color=colors[2],
            color=colors2[idx],
            label="TinyLFU",
        )
        if idx == 0:
            handles.append(s3)
        a -= 0.12
        idx += 1

    x, y = [], []
    a = 1
    idx = 0
    for i in (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4):
        x.append(
            data_dict[dataname]["lru"]["age_mean"]
            / data_dict[dataname]["s3fifo-{}".format(i)]["age_mean"]
        )
        y.append(data_dict[dataname]["s3fifo-{}".format(i)]["incorrect_demote_ratio"])
        s = 1280 if i == 0.10 else 640
        lw = 3.2 if i == 0.10 else 0.8
        s4 = plt.scatter(
            x[-1],
            1 - y[-1],
            marker="*",
            s=s,
            #  alpha=a,
            linewidths=lw,
            edgecolor="black",
            #  color=colors[0],
            color=colors1[idx],
            label="S3-FIFO",
        )
        if idx == 0:
            handles.append(s4)
        a -= 0.16
        idx += 1

    # plt.text(64.00, plt.ylim()[1] * 1.01, "light color: smaller probationary queue size", fontsize=24)

    # print(handles)
    # plt.xscale("log")
    # plt.xticks([0, 1, 20, 40, 60, 80, 100])
    # plt.yticks([0.13, 0.14, 0.15, 0.16, 0.17, 0.18, ])
    plt.xscale("log")
    plt.xlabel("Normalized demotion speed")
    plt.ylabel("Demotion precision")
    plt.grid(linestyle="--")
    plt.legend(
        handles=handles,
        loc="upper left",
        ncol=4,
        bbox_to_anchor=(0.00, 1.128),
        #    mode="expand",
        columnspacing=0.64,
        handletextpad=0.02,
        borderaxespad=0,
        frameon=False,
    )
    plt.savefig(
        "{}_{}.pdf".format(dataname, os.path.basename(datapath)), bbox_inches="tight"
    )
    plt.clf()


if __name__ == "__main__":
    from argparse import ArgumentParser

    ap = ArgumentParser()
    ap.add_argument("task", type=str, choices=["plot", "calc"])
    ap.add_argument("--datapath", type=str, help="path to the data, e.g., demotion_0.1")
    ap.add_argument(
        "--dataname", type=str, default="", help="name of the dataset used for plot"
    )

    ap.description = (
        "calculate demotion stat from libCacheSim output and plot the result"
    )

    args = ap.parse_args()

    if args.task == "calc":
        cal_demotion_speed_and_accuracy(args.datapath)

    elif args.task == "plot":
        plot_demotion(args.datapath, args.dataname)

# usage:
# python3 plot_demotion.py plot demotion_0.1 --dataname "hm0"

