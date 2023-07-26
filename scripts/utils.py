import os


def get_name(datapath):
    """get the name of the dataset from the path"""

    name = os.path.basename(datapath)
    name = name.capitalize()
    name = name.replace(".sample10", "")
    name = name.replace(".sample100", "")
    name = name.replace(".oraclegeneral", "")
    name = name.replace(".bin", "")
    name = name.replace("Cluster52", "Twitter")
    name = name.replace("block2020", "block")
    name = name.replace("photo1", "photo")
    name = name.replace("Wiki2016", "wiki")
    name = name.replace("Hm_0.iqi", "MSR")
    name = name.replace("_", " ")

    return name


def filename_to_dataset(filename):
    """
    mapping from dataset filename to dataset name

    """

    dataname_mapping = {
        "alibaba_block2020.oracleGeneral.sample10.zst": "alibaba",
        "tencent_block.oracleGeneral.zst": "tencentBlock",
        "tencent_block.oracleGeneral.sample10.zst": "tencentBlock",
        "tencent_photo1.oracleGeneral.sample10.zst": "tencentPhoto",
        "tencent_photo2.oracleGeneral.sample10.zst": "tencentPhoto",
    }

    if filename.startswith("cluster"):
        return "twr"
    elif filename.startswith("wiki_"):
        return "wiki"
    elif filename.startswith("fiu_"):
        return "fiu"
    elif filename.startswith("tencentBlock"):
        return "tencentBlock"
    elif filename.startswith("tencent_photo"):
        return "tencentPhoto"
    elif filename.startswith("io_"):
        return "alibaba"
    elif filename.startswith("cf_"):
        return "CDN2"
    elif filename.startswith("akamai_"):
        return "CDN1"
    elif filename.startswith("fb_"):
        return "fb"
    elif filename.startswith("2016"):
        return "systor"
    elif filename.startswith("meta_kv"):
        return "meta_kv"
    elif filename.startswith("meta_r"):
        return "meta_cdn"
    elif filename.startswith("w"):
        return "cphy"
    elif (
        "cache.0.oracleGeneral.sample10" in filename
        or "cache.1.oracleGeneral.sample10" in filename
    ):
        return "socialNetwork"
    elif ".IQI.bin.oracleGeneral.zst" in filename:
        return "MSR"
    elif filename in dataname_mapping:
        return dataname_mapping[filename]
    else:
        raise RuntimeError("unknown dataset dataname: {}".format(filename))
