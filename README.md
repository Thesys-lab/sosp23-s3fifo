
# FIFO queues are all you need for cache eviction
This repo contains code for SOSP'23 paper: [FIFO queues are all you need for cache eviction](https://jasony.me/publication/sosp23-s3fifo.pdf)

![S3-FIFO diagram](diagram/diagram_s3fifo.svg)


## Abstract
As a cache eviction algorithm, FIFO has a lot of attractive properties, such as simplicity, speed, scalability, and flash-friendliness. The most prominent criticism of FIFO is its low efficiency (high miss ratio).

In this work, we demonstrate a simple, scalable FIFO-based algorithm with three static queues (S3-FIFO). Evaluated on 6594 cache traces from 14 datasets, we show that S3-FIFO has lower miss ratios than state-of-the-art algorithms across traces. Moreover, S3-FIFO’s efficiency is robust — it has the lowest mean miss ratio on 10 of the 14 datasets and is among the top algorithms on the other datasets. The use of FIFO queues enables S3-FIFO to achieve good scalability with 6× higher throughput compared to optimized LRU at 16 threads.

Our insight is that most objects in Zipf workloads will only be accessed once in a short window, so it is critical to evict them early. And the key of S3-FIFO is a small FIFO queue that filters out most objects from entering the main cache. We show that filtering with a small static FIFO queue has a guaranteed eviction time and higher eviction precision compared to state-of-the-art adaptive algorithms.


## Repo structure 
The repo is a snapshot of [libCacheSim](https://github.com/1a1a11a/libCacheSim), modified [cachelib](https://github.com/facebook/cachelib/), and [distComp](https://github.com/1a1a11a/distComp). 


### How to use libCacheSim
You can compile libCacheSim, which will provide a `cachesim` binary, then you can run simulations with
```bash
# ./cachesim DATAPATH TRACE_FORMAT EVICTION_ALGO CACHE_SIZE [OPTION...]
./cachesim DATA oracleGeneral fifo,arc,lecar,s3fifo 0 --ignore-obj-size 1
```
Detailed instructions can be found at [libCacheSim](https://github.com/1a1a11a/libCacheSim).

### How to use cachelib
Cachelib compilation takes a longer time. You can compile cachelib with
```bash

cd mybench; bash run.sh
```

### How to use distComp
If you need to scale up the computation by using more nodes, you would need to use distComp. See [here](https://github.com/1a1a11a/distComp) for more details. 


## Instructions for reproducing results (artifact evaluation)
Please see [artifact evaluation](/doc/AE.md) for detailed instructions.


## Traces
The traces we used can be downloaded [here](https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/).

The binary traces are [zstd](https://github.com/facebook/zstd) compressed and have the following format:
```c
struct {
    uint32_t timestamp;
    uint64_t obj_id;
    uint32_t obj_size;
    int64_t next_access_vtime;  // -1 if no next access
}
```
The compressed traces can be used with libCacheSim without decompression. And libCacheSim provides a tracePrint tool to print the trace in human-readable format.


### Acknowledgement
We greatly thank the following people and organizations that made this work possible. 
#### Testbed
We greatly appreciate the resources and support provided by [Cloudlab](https://cloudlab.us) and [PDL](https://pdl.cmu.edu) for performing large-scale evaluations. 


#### Open source cache traces and **the people behind them**
* [Twitter](https://github.com/twitter/cache-traces)
* [Tencent Block](https://www.usenix.org/conference/atc20/presentation/zhang-yu) ([Download](http://iotta.snia.org/traces/parallel?only=27917))
* [Tencent Photo](https://dl.acm.org/doi/10.1145/3205289.3205299) ([Download](http://iotta.snia.org/traces/parallel?only=27476))
* [Wikimedia CDN](https://wikitech.wikimedia.org/wiki/Analytics/Data_Lake/Traffic/Caching)
* [Alibaba Block](https://github.com/alibaba/block-traces)
* [MSR](http://iotta.snia.org/traces/block-io?only=388)
* [FIU](http://iotta.snia.org/traces/block-io?only=390)
* [CloudPhysics](https://www.usenix.org/conference/fast15/technical-sessions/presentation/waldspurger)
* [Meta](https://cachelib.org/docs/Cache_Library_User_Guides/Cachebench_FB_HW_eval/)


#### Funding
This work was supported in part by [Meta Fellowship](https://research.facebook.com/blog/2020/1/announcing-the-recipients-of-the-2020-facebook-fellowship-awards/), NSF grants CNS 1901410 and 1956271, and an AWS grant. 


### Citation
```bibtex
@inproceedings{yang2023-s3fifo,
  title={FIFO queues are all you need for cache eviction},
  author={Yang, Juncheng and Zhang, Yazhuo and Qiu, Ziyue and Yue, Yao and Rashmi, K.V.},
  booktitle={Symposium on Operating Systems Principles (SOSP'23)},
  year={2023}
}
``` 

### License
```
Copyright 2023, Carnegie Mellon University

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```