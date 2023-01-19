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
    fields = ["Size", "HRFix", "Steps", "Scale", "Hypernetwork", "Sampler", "Model", "Text", "Negative"]
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


def format_date(d):
    result = ""
    for index, elem in enumerate(list(d)):
        # year
        if index == 0:
            result += str(elem) + "-"
        else:
            result += '%02d' % elem + "-"
    return result


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip", help="zip file with results")
    args = parser.parse_args()
    file_creation_timestamps = dict()
    with tempfile.TemporaryDirectory(prefix="neurofox-ext-") as tmp:
        with zipfile.ZipFile(args.zip, 'r') as zip_ref:
            for file in zip_ref.infolist():
                zip_ref.extract(file, tmp)
                name = file.filename
                # txt files are created at other time
                if name.endswith(".jpg"):
                    file_creation_timestamps[name] = file.date_time
            files = os.listdir(tmp)
        metadata = defaultdict(list)
        for file in files:
            if file.endswith(".txt"):
                key, value = parse_seed(os.path.join(tmp, file))
                metadata[key].append(value)
        with open("data.json", "w") as j:
            json.dump(metadata, j)
        if not os.path.exists("data"):
            os.mkdir("data")
        for key in metadata:
            v_list = metadata[key]
            ts_prefix = format_date(min([file_creation_timestamps[d["jpg_name"]] for d in v_list]))
            os_specific_folder_name = os.path.join("data", ts_prefix + "-" + key)
            if not os.path.exists(os_specific_folder_name):
                os.mkdir(os_specific_folder_name)
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
                    with open(os.path.join(os_specific_folder_name, value["jpg_name"]), 'wb') as target:
                        target.write(img.get_file())
                with open(os.path.join(os_specific_folder_name, "data.json"), "w") as j:
                    json.dump(v_list[0], j)


if __name__ == '__main__':
    run()
