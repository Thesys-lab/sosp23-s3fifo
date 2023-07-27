
import glob

def dedep(datapath):

    lines_set = set()
    with open(datapath, "r") as f:
        lines = f.readlines()

    with open(datapath, "w") as f:
        for line in lines:
            if line not in lines_set:
                f.write(line)
                lines_set.add(line)



def update_algo_name(algo):
    name_update_dict = {
        "FIFO_Reinsertion": "FIFO-Reinsertion",
        "Clock-2": "2-bit Clock",
        "arc": "ARC",
        "cacheus": "CACHEUS",
        "LeCaR-0.50lru": "LeCaR",
        "lecar": "LeCaR",
        "lirs": "LIRS",
        "twoq": "2Q",
        "lru": "LRU",
        "b-lru": "B-LRU",
        "S4LRU(25:25:25:25)": "SLRU",
        "FIFO_Merge_FREQUENCY": "FIFO-Merge", 
        "WTinyLFU-w0.01-SLRU": "TinyLFU",
        "WTinyLFU-w0.10-SLRU": "TinyLFU-0.1",
        "lhd": "LHD",
        "clock": "CLOCK",
        "FIFO": "FIFO",
        "S3FIFO": "S3-FIFO",

        # "S3LRU-LRU-lru-0-0.1000-1":         "S3-LRU-LRU-L-1", 
        # "S3LRU-LRU-lru-1-0.1000-1":         "S3-LRU-LRU-E-1", 
        # "S3LRU-LRU-clock2-0-0.1000-1":         "S3-LRU-FIFO-L-1", 
        # "S3LRU-LRU-clock2-1-0.1000-1":         "S3-LRU-FIFO-E-1", 
        # "S3LRU-LRU-lru-0-0.1000-2":         "S3-LRU-LRU-L", 
        # "S3LRU-LRU-lru-1-0.1000-2":         "S3-LRU-LRU-E", 
        # "S3LRU-LRU-clock2-0-0.1000-2":         "S3-LRU-FIFO-L", 
        # "S3LRU-LRU-clock2-1-0.1000-2":         "S3-LRU-FIFO-E", 

        # "S3LRU-FIFO-lru-0-0.1000-1":         "S3-FIFO-LRU-L-1", 
        # "S3LRU-FIFO-lru-1-0.1000-1":         "S3-FIFO-LRU-E-1", 
        # "S3LRU-FIFO-clock2-0-0.1000-1":         "S3-FIFO-FIFO-L-1", 
        # "S3LRU-FIFO-clock2-1-0.1000-1":         "S3-FIFO-FIFO-E-1", 
        # "S3LRU-FIFO-lru-0-0.1000-2":         "S3-FIFO-LRU-L", 
        # "S3LRU-FIFO-lru-1-0.1000-2":         "S3-FIFO-LRU-E", 
        # "S3LRU-FIFO-clock2-0-0.1000-2":         "S3-FIFO-FIFO-L", 
        # "S3LRU-FIFO-clock2-1-0.1000-2":         "S3-FIFO-FIFO-E", 

        # "QDLPv1-0.1000-0.9000-sfifo-1": "S3-FIFO-sfifo",
        # "QDLPv1-0.1000-0.9000-sfifo-2": "S3-FIFO-sfifo-2",
        # "S3FIFOd-0.1000-1": "S3FIFOd",

        # "QDLPv1-0.1000-0.9000-Clock2": "S3-FIFO",
        # "QDLPv1-0.1000-0.9000-Clock2-2": "S3-FIFO",
        # "QDLPv1-0.10-clock2": "S3-FIFO-0.10",
        # "QDLPv2-Clock2": "S3-FIFO-D", 
    }

    name_update_dict2 = {}
    for o, n in name_update_dict.items():
        name_update_dict2[o.lower()] = n
    name_update_dict = name_update_dict2
    
    return name_update_dict[algo.lower()]


def update_dataset_name(name):
    name = name.replace("tenant_", "")
    name = name.replace("twr", "Twitter KV")
    name = name.replace("cphy", "CloudPhysics (block)")
    name = name.replace("msr", "MSR (block)")
    name = name.replace("tencentphoto", "TencentPhoto CDN")
    name = name.replace("tencent", "Tencent (block)")
    name = name.replace("alibaba", "Alibaba (block)")
    name = name.replace("wiki", "Wikimedia CDN")
    name = name.replace("wiki_tencentphoto", "Wiki + TPhoto")
    name = name.replace("meta_kv", "Meta KV")
    name = name.replace("meta_cdn", "Meta CDN")
    name = name.replace("meta", "Meta")
    name = name.replace("tencent_photo", "TencentPhoto (CDN)")
    name = name.replace("fiu", "fiu (block)")
    name = name.replace("systor", "Systor (block)")

    return name


if __name__ == "__main__":
    DATAPATH = "/disk/result/libCacheSim/result_lecar/"
    for f in glob.glob(DATAPATH + "/*/*.zst"):
        dedep(f)

