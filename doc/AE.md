
# How to reproduce the results
## OS support
All of the experiments should be operating-system-agnostic, however, we have not tested on Ubuntu 20.04 LTS, and we provide installation instructions for Ubuntu. Therefore, we recommend using Ubuntu 20 or Ubuntu 22 for reproducing the results.

## Install Dependency
```bash
sudo apt install -yqq libglib2.0-dev libboost-all-dev zstd libzstd-dev wget
```

## Setup libCacheSim
We use [libCacheSim](https://github.com/1a1a11a/libCacheSim) to perform simulations, it can be installed using the following commands.

```bash 
pushd libCacheSim/scripts && bash install_dependency.sh && bash install_libcachesim.sh && popd;
```

---


## Data access
The data needed to run experiments can be downloaded from [https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/](https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/).

The binary traces are [zstd](https://github.com/facebook/zstd) compressed and have the following format:
```c
struct {
    uint32_t timestamp;
    uint64_t obj_id;
    uint32_t obj_size;
    int64_t next_access_vtime;  // -1 if no next access
}
```
The compressed traces can be used with libCacheSim without decompression. Moreover, libCacheSim provides a tracePrint tool to print the trace in human-readable format.
However, for some experiments, we need decompressed traces, to decompress the traces, you can use the following command:
```bash
zstd -d /path/to/data
```

---


## Reproduce the results and figures
> **Note** 
> The full dataset is very large (2 TB before decompression), so we suggest you only download the traces you need. 
> Many of the experiments require long running time, be prepared. We suggest using the sampled Twitter traces so that you do not have to wait days for the results. 
> libCacheSim allows you to run experiments in parallel, however, which requires more memory. If you would like to reduce DRAM usage, you can run one experiment at each time, e.g., specifying one algorithm or size. 

> **Note**
> The commands below assume you are in the root directory, which contains the libCacheSim, result, scripts, doc folders.

---

### Figure 2a, 2b, one-hit-wonder ratio of Zipf workloads
This plot is generated using the following command:
```bash
python3 scripts/plot_one_hit_zipf.py
```

This script keeps generating requests follow Zipf distribution and measure the one-hit-wonder ratio. 
It generates two figures in the current directory, `one_hit_ratio_zip.pdf` and `one_hit_ratio_zip_log.pdf`. 


### Figure 2c, 2d, one-hit-wonder ratio on real-world workloads
The two traces used in this experiment can be downloaded at [Twitter](https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/twitter/sample/cluster52.oracleGeneral.sample10.zst) and [MSR](https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/msr/msr_hm_0.oracleGeneral.zst).

```bash
# download traces
wget https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/twitter/sample/cluster52.oracleGeneral.sample10.zst -O twitter.oracleGeneral.bin.zst
wget https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/msr/msr_hm_0.oracleGeneral.zst -O msr.oracleGeneral.bin.zst

# decompress traces
zstd -d twitter.oracleGeneral.bin.zst
zstd -d msr.oracleGeneral.bin.zst

# calculate one-hit-wonder ratio, note that it may take 10 - 60 minutes
python3 scripts/plot_one_hit_trace.py --datapath twitter.oracleGeneral.bin msr.oracleGeneral.bin --name twitter msr

```

This will generate two figures `one_hit_ratio.pdf` and `one_hit_ratio_lg.pdf`

---

### Figure 3, one-hit-wonder ratio across traces
This figure shows the distribution of one-hit-wonder ratio across all traces. It requires first calculating the one-hit-wonder ratio for all traces, then plot the results. 
Because the computation takes days to run and involves some traces not in the public domain, we provide computed results that can be downloaded [here](https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/sosp23/oneHit.zst). You are welcome to verify the provided results. 


This plot is generated using the following command:
```bash
# download results
wget https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/sosp23/oneHit.zst

# decompress 
zstd -d oneHit.zst

# plot results, note that it may take 10 - 60 minutes
python3 scripts/plot_one_hit_trace.py --datapath oneHit --plotbox

# [optionally] this calculates the last two columns of Table 1
python3 scripts/plot_one_hit_trace.py --datapath oneHit --calperdataset

```

[Optional] To re-generate or verify our results, you can use the `traceOneHit` from the libCacheSim tools
```bash
# this will calculates the one-hit-winder ratio for every 100 new and unique objects, e.g., the one-hit-wonder ratio in the first 100, 200, 300, 400... objects  
./libCacheSim/_build/bin/traceOneHit msr.oracleGeneral.bin oracleGeneral caloneHit
```
---

### Figure 4, object frequency distribution during eviction
The plots use the same two traces as Figure 2c and Figure 2d, download them if you skipped the figures

To generate these two plots, we first need to turn on eviction tracking and run a few cache simulations 

#### Run simulations
```bash
# turn on eviction tracking (will print to stdout)
sed -i "s|// #define TRACK_EVICTION_V_AGE|#define TRACK_EVICTION_V_AGE|g" libCacheSim/libCacheSim/include/config.h
# recompile libCacheSim
pushd libCacheSim/_build/ && cmake .. && make -j && popd

# run LRU caches on the Twitter trace at cache size 0.001, 0.01, 0.1 and 0.5 of #obj in the trace 
for cache_size in 0.001 0.01 0.1 0.5; do 
    ./libCacheSim/_build/bin/cachesim twitter.oracleGeneral.bin.zst oracleGeneral LRU ${cache_size} --ignore-obj-size 1 > twitter_lru_${cache_size} &
done

# run Belady caches on the Twitter trace
for cache_size in 0.001 0.01 0.1 0.5; do 
    ./libCacheSim/_build/bin/cachesim twitter.oracleGeneral.bin.zst oracleGeneral Belady ${cache_size} --ignore-obj-size 1 > twitter_belady_${cache_size} &
done

# run LRU caches on the MSR trace
for cache_size in 0.001 0.01 0.1 0.5; do 
    ./libCacheSim/_build/bin/cachesim msr.oracleGeneral.bin.zst oracleGeneral LRU ${cache_size} --ignore-obj-size 1 > msr_lru_${cache_size} &
done

# run Belady caches on the MSR trace
for cache_size in 0.001 0.01 0.1 0.5; do 
    ./libCacheSim/_build/bin/cachesim msr.oracleGeneral.bin.zst oracleGeneral Belady ${cache_size} --ignore-obj-size 1 > msr_belady_${cache_size} &
done
```
Now wait a few minutes until all of them finish (can monitor the cachesim process with `htop`)


#### plot the results

```bash
# Figure 4a
python3 scripts/libCacheSim/plot_eviction_freq.py --datapath twitter_lru_0.001 twitter_lru_0.01 twitter_lru_0.1 twitter_lru_0.5 --figname twitter_lru
# Figure 4b
python3 scripts/libCacheSim/plot_eviction_freq.py --datapath twitter_belady_0.001 twitter_belady_0.01 twitter_belady_0.1 twitter_belady_0.5 --figname twitter_belady
# Figure 4c
python3 scripts/libCacheSim/plot_eviction_freq.py --datapath msr_lru_0.001 msr_lru_0.01 msr_lru_0.1 msr_lru_0.5 --figname msr_lru
# Figure 4d
python3 scripts/libCacheSim/plot_eviction_freq.py --datapath msr_belady_0.001 msr_belady_0.01 msr_belady_0.1 msr_belady_0.5 --figname msr_belady
```

This will generate four figures `eviction_freq_msr_lru.pdf`, `eviction_freq_msr_belady.pdf`, `eviction_freq_twitter_lru.pdf`, and `eviction_freq_twitter_belady.pdf`. 


#### turn off eviction tracking and recompile libCacheSim

```bash
sed -i "s|#define TRACK_EVICTION_V_AGE|// #define TRACK_EVICTION_V_AGE|g" libCacheSim/libCacheSim/include/config.h
pushd libCacheSim/_build/ && make -j && popd;
```

### Figure 6, Figure 7, miss ratio reductions on all traces and datasets

> **Warning**
> This experiment takes 100,000 to 1,000,000 core • hours to finish, we don't expect reviewers to finish them within the deadline. So we provide already computed results so that reviewers can spot check and plot them. 

The provided results are in [/result/cachesim/](/result/cachesim/)

#### Plot the figures using the results
```bash
python3 scripts/libCacheSim/plot_miss_ratio.py --datapath=result/cachesim/
```

This generates `miss_ratio_per_dataset_0.pdf` which is Figure 7b and `miss_ratio_per_dataset_2.pdf` which is Figure 7a, 
and `miss_ratio_percentiles_0.pdf` which is Figure 6b and `miss_ratio_percentiles_2.pdf` which is Figure 6a. 

#### [Optional] Verify the simulation results
You can verify the simulation results by picking any trace and run cachesim using the following commands
```bash 
# use size 0 to choose cache size based on the trace footprint 
# it uses cache sizes 0.001, 0.003, 0.01, 0.03, 0.1, 0.2, 0.4, 0.8 of the number of objects or bytes in the trace
./libCacheSim/_build/bin/cachesim /path/to/data oracleGeneral algo 0 --ignore-obj-size 1
# an example
./libCacheSim/_build/bin/cachesim msr.oracleGeneral.bin oracleGeneral lru,s3fifo 0 --ignore-obj-size 1
```

You can also verify the result of one dataset, for example, the MSR dataset, 
* first download all traces of the MSR dataset from https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/
* then you can run `cachesim` on each trace and collect the results
```bash
for trace in ${trace_dir}; do
    ./libCacheSim/_build/bin/cachesim ${trace} oracleGeneral FIFO,LRU,ARC,LIRS,TinyLFU,2Q,SLRU,S3FIFO 0 --ignore-obj-size 1;
done
```


If your node does not have enough DRAM, you can reduce the number of algorithms in each run and run each command one by one. 

This will create a `result` folder and store the results in the folder, and it also prints the output to stdout. 
You verify with the result data we provided under `result/cachesim/MSR/`.


### Figure 8
The results are generated using cachelib implementations and plot using 
```bash
python3 scripts/plot_throughput.py
```
You should have `cachelib_thrpt_zipf_500.pdf` and `cachelib_thrpt_zipf_4000.pdf`

[Optional] If you would like to run cachelib to verify the results, follow the instructions below
Note that this needs a machine with Intel CPUs of at least 16 hardware threads (32 hyper-threads) in one NUMA domain. If you use Cloudlab, we recommend using r650 and c6420 from Clemson cloudlab. 

Setup for the benchmark were only tested on Ubuntu 20 and Ubuntu 22 and it may require some changes to use on other systems. 

```bash
# generate Zipf request data of 1 million objects 100 million requests
python3 libCacheSim/scripts/data_gen.py -m 1000000 -n 20000000 --alpha 1.0 --bin-output cachelib/mybench/zipf1.0_1_100.oracleGeneral.bin

git clone https://github.com/Thesys-lab/cachelib-sosp23 cachelib;
cd cachelib/mybench/; 

# turnoff turobo boose and change to performance mode, this is very important for getting consistent results
bash turboboost.sh disable
# you can monitor the CPU freq using this 
# watch -n.1 "cat /proc/cpuinfo | grep \"^[c]pu MHz\" | sort -t : -r -nk 2"

# build cachelib, it takes a few minutes up to one hour
bash build.sh
```

Run benchmark
```bash
# usage: bash run.sh algo size
bash run.sh s3fifo 4000

```

Run Segcache
```bash
git clone https://github.com/Thesys-lab/Segcache.git
cd Segcache && mkdir _build && cd _build
cmake ..
# update the reader to use oracleGeneral trace 
sed -i "s/reader->trace_entry_size = 20;/reader->trace_entry_size = 24;/g" ../benchmarks/trace_replay/reader.c
make -j

```

create the config file for running N threads, you need to replace N with the number of threads you would like to run 
```bash
echo '''
debug_logging: no
trace_path: ../../cachelib/mybench/zipf1.0_1_100.oracleGeneral.bin
default_ttl_list: 8640000:1
heap_mem: 4294967296
hash_power: 26
seg_evict_opt: 5
n_thread:N
seg_n_thread:N

''' > trace_replay_seg.conf
```


Run benchmarks
```bash
./benchmarks/trace_replay_seg trace_replay_seg.conf
```

### Figure 9
These figures are plotted using two CDN traces from Tencent and Wikimedia and can be downloaded here: [Tencent](https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/tencentPhoto/tencent_photo1.oracleGeneral.zst), [WikiMedia](https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/wiki/wiki_2019t.oracleGeneral.zst)

```bash
# download traces
wget https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/tencentPhoto/tencent_photo1.oracleGeneral.zst -O tencent_photo1.oracleGeneral.bin.zst
wget https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/cacheDatasets/wiki/wiki_2019t.oracleGeneral.zst -O wiki_2019t.oracleGeneral.bin.zst

# decompress
zstd -d tencent_photo1.oracleGeneral.bin.zst;
zstd -d wiki_2019t.oracleGeneral.bin.zst;

# calculate the miss ratio and write amplification of FIFO 
./libCacheSim/_build/bin/flash /path/to/data oracleGeneral FIFO 0.1 &

for dram_size_ratio in 0.001 0.01 0.1; do
    # calculate the miss ratio and write amplication of probabilistic admission
    ./libCacheSim/_build/bin/flash /path/to/data oracleGeneral flashProb 0.1 -e "ram-size-ratio=${dram_size_ratio},disk-admit-prob=0.2,disk-cache=fifo"
    # calculate the miss ratio and write amplication when using FIFO filters
    ./libCacheSim/_build/bin/flash /path/to/data oracleGeneral qdlp 0.1 -e "fifo-size-ratio=${dram_size_ratio},main-cache=fifo,move-to-main-threshold=2"
done
```

We implemented the flashield simulator in Python, and you need to install `sklean` and `lru-dict`
```bash
python -m pip install scikit-learn lru-dict
```

Then you can run flashield: 
```bash
# calcualte the miss ratio and write amplification of flashield
# note that this will take more than one day to run, add --logging-interval 100000 to have frequent logging
python3 scripts/flashield/flashield.py /path/to/data --ram-size-ratio=0.001 --disk-cache-type=FIFO --use-obj-size true
python3 scripts/flashield/flashield.py /path/to/data --ram-size-ratio=0.01 --disk-cache-type=FIFO --use-obj-size true
python3 scripts/flashield/flashield.py /path/to/data --ram-size-ratio=0.10 --disk-cache-type=FIFO --use-obj-size true
```
You can take the last line as the result. 
We have filled the result in [plot_write_amp.py](/scripts/plot_write_amp.py), which are similar to the results above, so you can plot using 
```bash
python3 scripts/plot_write_amp.py
```

This will generate `write_amp.pdf`. 


### Table 2
The results in the table are from cachesim using the Twitter and MSR traces
```bash
# get the miss ratio of LRU and ARC 
./libCacheSim/_build/bin/cachesim msr.oracleGeneral.bin oracleGeneral lru,arc 0.1 --ignore-obj-size 1

# get the miss ratios of S3-FIFO with different small FIFO sizes
# the second col S3FIFO-0.0100-2 is the algorithm name where the 0.0100 is the small FIFO queue size
for s in 0.01 0.02 0.05 0.10 0.20 0.30 0.40; do 
    echo "running simulation using cache S3-FIFO cache size 0.1 small fifo size $s trace MSR"
    ./libCacheSim/_build/bin/cachesim msr.oracleGeneral.bin oracleGeneral s3fifo 0.1 --ignore-obj-size 1 -e "fifo-size-ratio=${s}" | tail -n 1
done

# get the miss ratios of W-TinyLFU with different window sizes
for s in 0.01 0.02 0.05 0.10 0.20 0.30 0.40; do 
    echo "running simulation using cache W-TinyLFU cache size 0.1 small fifo size $s trace MSR"
    ./libCacheSim/_build/bin/cachesim msr.oracleGeneral.bin oracleGeneral wtinylfu 0.1 --ignore-obj-size 1 -e "window-size=${s}" | tail -n 1
done
```
The output are the results in the table.


### Figure 10 
We have compiled the results and stored in [result/demotion/](/result/demotion/), so that you can directly plot the computed data using 
```bash
# MSR and large size
python3 scripts/libCacheSim/plot_demotion.py plot --datapath result/demotion/demotion_0.1 --dataname MSR

# MSR and small size
python3 scripts/libCacheSim/plot_demotion.py plot --datapath result/demotion/demotion_0.001 --dataname MSR

# Twitter and large size
python3 scripts/libCacheSim/plot_demotion.py plot --datapath result/demotion/demotion_0.1 --dataname twitter

# Twitter and small size
python3 scripts/libCacheSim/plot_demotion.py plot --datapath result/demotion/demotion_0.001 --dataname twitter
``` 

The generated figures will have name `MSR_demotion.pdf` and `twitter_demotion.pdf`


[optional] If you would like to verify the results, e.g., the results in result/demotion/demotion_0.1 
```bash
# turn on demotion tracking
sed -i "s|// #define TRACK_DEMOTION|#define TRACK_DEMOTION|g" libCacheSim/libCacheSim/include/config.h
# compile
pushd libCacheSim/_build/ && make -j && popd

mkdir demotion;
# get the demotion result of ARC
./libCacheSim/_build/bin/cachesim msr.oracleGeneral.bin oracleGeneral arc 0.1 --ignore-obj-size 1 > demotion/MSR_ARC_0.1

# get the demotion result of S3-FIFO
for s in 0.01 0.02 0.05 0.10 0.20 0.30 0.40; do 
    echo "running simulation using cache S3-FIFO cache size 0.1 small fifo size $s trace MSR"
    ./libCacheSim/_build/bin/cachesim msr.oracleGeneral.bin oracleGeneral s3fifo 0.1 --ignore-obj-size 1 -e "fifo-size-ratio=${s}" > demotion/MSR_S3FIFO_0.1_${s}_0.1
done

# get the demotion result of W-TinyLFU
for s in 0.01 0.02 0.05 0.10 0.20 0.30 0.40; do 
    echo "running simulation using cache TinyLFU cache size 0.1 small fifo size $s trace MSR"
    ./libCacheSim/_build/bin/cachesim msr.oracleGeneral.bin oracleGeneral wtinylfu 0.1 --ignore-obj-size 1 -e "window-size=${s}" > demotion/MSR_TinyLFU_0.1_${s}_0.1
done

# Analyze the demotion results
for f in demotion/*; do
    python3 scripts/libCacheSim/plot_demotion.py calc --datapath $f >> demotion_0.1; 
done

# plot the demotion results
python3 scripts/libCacheSim/plot_demotion.py plot --datapath demotion_0.1 --dataname MSR

# turn off demotion tracking
sed -i "s|#define TRACK_DEMOTION|// #define TRACK_DEMOTION|g" libCacheSim/libCacheSim/include/config.h
# compile
pushd libCacheSim/_build/ && make -j && popd

```

### Figure 11 Miss ratio reduction on different small FIFO queue sizes
This set of results are similar to Figure 6 and also requires a lot of computation, we estimate another 1 million cores•hours, so we provide the results. 
Reviewers can spot check the results using libCacheSim by running

```bash
# plot the miss ratio reduction results
python3 scripts/libCacheSim/plot_fifo_size.py --datapath result/cachesim_fifo/
```

The figures will be `miss_ratio_percentiles_0.pdf` and `miss_ratio_percentiles_2.pdf` for small and large cache sizes. 


#### [Optional] Verify the simulation results
To spot check the result, you can pick a trace and run the following commands
```bash
    # use cachesim to obtain results of different small FIFO queue sizes
    ./libCacheSim/_build/bin/cachesim /path/to/trace oracleGeneral s3fifo 0.1 --ignore-obj-size 1 -e "fifo-size-ratio=${s}"

    # for example, we can run simulation using cache S3-FIFO cache size 0.001 and 0.1, small fifo size $s on the small MSR trace
    ./libCacheSim/_build/bin/cachesim msr.oracleGeneral.bin.zst oracleGeneral s3fifo 0.001,0.1 --ignore-obj-size 1 -e "fifo-size-ratio=0.1"
```



---

Wow, congratulations! You have reached the end of the artifact evaluation! 




