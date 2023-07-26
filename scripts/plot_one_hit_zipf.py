import os
import sys
import logging
import itertools
import random
import bisect
from functools import reduce
import math

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pyutils.common import get_linestyles

from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt

logger = logging.getLogger("oneHit")
logger.setLevel(logging.WARN)

from concurrent.futures import ProcessPoolExecutor, as_completed


class ZipfGenerator:
    def __init__(self, m, alpha):
        # Calculate Zeta values from 1 to n:
        tmp = [1.0 / (math.pow(float(i), alpha)) for i in range(1, m + 1)]
        zeta = reduce(lambda sums, x: sums + [sums[-1] + x], tmp, [0])

        # Store the translation map:
        self.distMap = [x / zeta[-1] for x in zeta]

    def next(self):
        # Take a uniform 0-1 pseudo-random value:
        u = random.random()

        # Translate the Zipf variable:
        return bisect.bisect(self.distMap, u) - 1


def gen_zipf(m, alpha, n):
    """
    m objects with alpha and n requests

    """
    np.random.seed(random.randint(0, 100000))

    alpha = float(alpha)
    np_tmp = np.power(np.arange(1, m + 1), -alpha)
    np_zeta = np.cumsum(np_tmp)
    dist_map = np_zeta / np_zeta[-1]
    r = np.random.uniform(0, 1, n)

    return np.searchsorted(dist_map, r)


def gen_uniform(m, n):
    """
    m objects with alpha and n requests

    """

    return np.random.uniform(0, m, size=n).astype(int)


def cal_one_hit_ratio_zipf(alpha, n_total_obj, n_obj_list):
    n_one_hit_list, n_req_list = [], []
    pos_in_n_obj_list, n_one_hit_count = 0, 0
    n_req = 0

    obj_freq = defaultdict(int)
    while pos_in_n_obj_list < len(n_obj_list):
        if alpha > 0:
            rvs = gen_zipf(n_total_obj, alpha, n_total_obj * 10)
        elif alpha == 0:
            rvs = gen_uniform(n_total_obj, n_total_obj * 10)

        for obj_id in rvs:
            n_req += 1
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

    return np.array(n_one_hit_list), np.array(n_req_list)


def cal_one_hit_ratio_zipf_multiple_times(alphas, n_total_obj, n_times):
    """
    run the computation in parallel

    """

    n_obj_list = [i + 1 for i in range(50)]
    for i in range(200, 1024):
        if int(1.02**i) > n_total_obj * 1:
            break
        n_obj_list.append(int(1.02**i))
    for i in range(n_obj_list[-1] + 1, n_total_obj):
        if i % 100 == 0:
            n_obj_list.append(i)

    n_obj_list = np.array(n_obj_list)

    n_one_hit_list_dict = defaultdict(list)  # alpha -> a list of n_one_hit_list
    futures_dict = {}
    with ProcessPoolExecutor(max_workers=os.cpu_count() // 2) as executor:
        for alpha in alphas:
            for i in range(n_times):
                future = executor.submit(
                    cal_one_hit_ratio_zipf, alpha, n_total_obj, n_obj_list
                )
                futures_dict[future] = alpha

        for future in as_completed(futures_dict):
            alpha = futures_dict[future]
            n_one_hit_list, n_req_list = future.result()
            n_one_hit_list_dict[alpha].append(n_one_hit_list)

    one_hit_ratio_dict = {}
    for alpha in alphas:
        n_one_hit_list = np.mean(n_one_hit_list_dict[alpha], axis=0)
        x = n_obj_list / n_obj_list[-1]
        y = n_one_hit_list / n_obj_list
        one_hit_ratio_dict[alpha] = (x, y)

    return one_hit_ratio_dict


def plot_one_hit_ratio_zipf():
    linestyles = itertools.cycle(reversed(get_linestyles()))
    n_total_obj = 1000000

    one_hit_ratio_dict = cal_one_hit_ratio_zipf_multiple_times(
        [
            0.6,
            0.8,
            1,
            1.2,
        ],
        n_total_obj,
        10,
    )

    start_idx = 0

    for alpha, (x, y) in one_hit_ratio_dict.items():
        if alpha == 0:
            plt.plot(x[start_idx:], y[start_idx:], label="Uniform")
        else:
            plt.plot(
                x[start_idx:],
                y[start_idx:],
                label="Zipf-{}".format(alpha),
                linestyle=next(linestyles),
            )

    plt.ylim(0, 1)
    plt.grid(linestyle="--")
    plt.legend()
    plt.xlabel("Fraction of total objects")
    plt.ylabel("One-hit-wonder ratio")
    plt.savefig("one_hit_ratio_zip.pdf", bbox_inches="tight")

    plt.xscale("log")
    plt.xlim(right=1.2)
    plt.savefig("one_hit_ratio_zipf_log.pdf", bbox_inches="tight")
    plt.clf()


if __name__ == "__main__":
    plot_one_hit_ratio_zipf()

