import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from collections import defaultdict

from exif import Image


def hash(data):
    m = hashlib.sha256()
    fields = ["Size","HRFix","Steps","Scale","Hypernetwork","Sampler","Model","Text","Negative"]
    for d in fields:
        m.update(data[d].encode('utf-8'))
    return m.hexdigest()


def parse_seed(file):
    data = {}
    try:
        with open(file, 'r') as txt:
            for line in txt.read().splitlines():
                if line.count(":") == 1:
                    k, v = line.split(":")
                    data[k] = v[1:]
                else:
                    print("Ignoring broken data line: {} in {}".format(line, txt))
            # data["jpg"] = re.sub("[0-9]+-(.+?)\\.txt", "\\1", txt.name)
            data["jpg"] = txt.name[:-4]
            data["jpg_name"] = os.path.basename(data["jpg"])
            key = hash(data)
        return key, data
    except Exception as e:
        print(e)
        print("Error parsing {}. Inspect the file in temp folder and press Enter when finished".format(file))
        input()
        raise e

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", help="zip file with results")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="neurofox-ext-") as tmp:
        with zipfile.ZipFile(args.zip, 'r') as zip_ref:
            zip_ref.extractall(tmp)
            files = os.listdir(tmp)
        metadata = defaultdict(list)
        for file in files:
            if file.endswith(".txt"):
                key, value = parse_seed(os.path.join(tmp, file))
                metadata[key].append(value)
        print(metadata)
        with open("data.json", "w") as j:
            json.dump(metadata, j)
        if not os.path.exists("data"):
            os.mkdir("data")
        for key in metadata:
            v_list = metadata[key]
            if not os.path.exists(os.path.join("data", key)):
                os.mkdir(os.path.join("data", key))
            for value in v_list:
                file = value["jpg"]
                with open(file, "rb") as source:
                    img = Image(source)
                    # tmp file is not needed in exifs
                    value["jpg"] = None
                    # https://exiftool.org/TagNames/EXIF.html standard implies this exists,
                    # but Windows can't parse it, idk...
                    img.set("ImageDescription", value["Text"])
                    # so we put everything to the Model tag!
                    img.set("Model", json.dumps(value))
                    with open(os.path.join("data", key, value["jpg_name"]), 'wb') as target:
                        target.write(img.get_file())
                with open(os.path.join("data", key, "data.json"), "w") as j:
                    json.dump(v_list[0], j)


if __name__ == '__main__':
    run()
