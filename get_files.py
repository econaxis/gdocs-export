import requests
from datetime import datetime
import csv

import ujson as json

from requests.adapters import HTTPAdapter

from requests.packages.urllib3.util.retry import Retry
import os

# Replace here with your file ID
GDOCS_FILE_ID = "1nOVrSDsk_kJG9u6SCvVlE6cLfRmGsAmHP2b2QjtsJh0"
OAUTH_TOKEN = os.environ["DEFAULT_OAUTH_TOKEN"]

retry_strategy = Retry(
    total=3,
    status_forcelist=[413, 429, 500],
    allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
    backoff_factor=1.5,
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

revision_data_url = "https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start=1&end={end}"
revision_url = "https://www.googleapis.com/drive/v3/files/{}/revisions"


def download_operations(file_id, token):
    auth_header = dict(authorization=f"Bearer {token}")
    # auth_header = dict()
    rev_id_response = requests.get(
        url=revision_url.format(file_id), headers=auth_header
    )
    if rev_id_response.status_code != 200:
        print(rev_id_response.text)
        raise RuntimeError("not 200")
    rev_id_response = json.loads(rev_id_response.text)
    last_rev_id = rev_id_response["revisions"][-1]["id"]

    revision_response = http.get(
        url=revision_data_url.format(file_id=file_id, end=last_rev_id),
        headers=auth_header,
    ).text[5:]
    revision_response = json.loads(revision_response)
    return revision_response


def process_operations(revision_response):
    operations = []

    for x in revision_response["changelog"]:
        if x[0]["ty"] not in {"is", "ds", "mlti"}:
            continue

        if x[0]["ty"] == "mlti":
            for i in x[0]["mts"]:
                revision_response["changelog"].append([i, x[1]])
            continue

        content = None
        if x[0]["ty"] == "is":
            content = x[0]["s"]
            index = x[0]["ibi"] - 1
        elif x[0]["ty"] == "ds":
            index = [x[0]["si"], x[0]["ei"] + 1]

        operations.append(
            dict(date=x[1] / 1e3, content=content, index=index, type=x[0]["ty"])
        )

    operations = sorted(operations, key=lambda k: k["date"])
    return operations


def build_strings_generator(operations):
    cur_string = []
    last_count = {"index": 0, "count": 0}
    join_cache = {"str": "", "index": 0}
    x_keys = operations
    for x in x_keys:
        yielded_row = {}
        if x["type"] == "is":
            char_content = list(x["content"])
            cur_string[x["index"]: x["index"]] = char_content
        elif x["type"] == "ds":
            cur_string[x["index"][0]: x["index"][1]] = []
        x["word_count"] = (
                cur_string[last_count["index"]:].count(" ") + last_count["count"]
        )

        last_count.update({"index": len(cur_string) - 1, "count": x["word_count"]})

        yielded_row["word_count"] = x["word_count"]
        yielded_row["cur_string"] = join_cache["str"] + "".join(
            cur_string[join_cache["index"]:]
        )
        join_cache.update(
            {
                "index": len(yielded_row["cur_string"]) - 1,
                "str": yielded_row["cur_string"],
            }
        )

        yielded_row["date"] = str(datetime.fromtimestamp(x["date"]))

        yield yielded_row


# Also exports to csv
def build_strings(name, operations):
    with open("data/" + name, "w") as f:
        csvwriter = csv.DictWriter(
            f,
            dialect="excel",
            extrasaction="ignore",
            fieldnames=["date", "cur_string", "word_count"],
            escapechar="\\",
            doublequote=False,
        )
        csvwriter.writeheader()
        multi_row_chunk = []
        for x in build_strings_generator(operations):
            multi_row_chunk.append(x)

            if len(multi_row_chunk) > 10:
                csvwriter.writerows(multi_row_chunk)
                multi_row_chunk.clear()


def write_zip(name):
    import zipfile

    with zipfile.ZipFile(
            f"data/{name}.csv.zip", "w", compression=zipfile.ZIP_LZMA
    ) as zip:
        zip.write(f"data/{name}.csv")
    return f"{name}.csv.zip"


def process_file(id, oauth_token):
    revision_response = download_operations(id, oauth_token)
    operations = process_operations(revision_response)
    build_strings(f"{id}.csv", operations)
    return operations


def default_process_file():
    import pickle
    from google.auth.transport.requests import Request

    creds = pickle.load(open("creds2.pickle", "rb"))
    creds.refresh(Request())
    return process_file(GDOCS_FILE_ID, creds.token)


if __name__ == "__main__":
    default_process_file()
