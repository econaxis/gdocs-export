import requests
from datetime import datetime
import csv

import ujson as json

from requests.adapters import HTTPAdapter

from requests.packages.urllib3.util.retry import Retry
import os

import secrets

GDOCS_FILE_ID = "1nOVrSDsk_kJG9u6SCvVlE6cLfRmGsAmHP2b2QjtsJh0"

retry_strategy = Retry(
    total=3,
    status_forcelist=[413, 429, 500],
    allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
    backoff_factor=5,
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

revision_data_url = "https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start=1&end={end}"
revision_url = "https://www.googleapis.com/drive/v3/files/{}/revisions"



def download_operations(file_id, token):
    auth_header = dict(authorization=f"Bearer {token}")
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
            start_index = x[0]["ibi"] - 1
            end_index = start_index + len(content)
        elif x[0]["ty"] == "ds":
            start_index = x[0]["si"] - 1
            end_index =  x[0]["ei"]

        operations.append(
            dict(date=x[1], content=content, start_index=start_index,end_index=end_index, type=x[0]["ty"])
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
            cur_string[x["start_index"] : x["start_index"]] = char_content
        elif x["type"] == "ds":
            x["content"] = "".join(cur_string[x["start_index"]: x["end_index"]])
            cur_string[x["start_index"] : x["end_index"]] = []
        x["word_count"] = cur_string.count("\n") + cur_string.count(" ")

        yielded_row["word_count"] = x["word_count"]
        yielded_row["cur_string"] = "".join(cur_string)

        yielded_row["date"] = str(datetime.fromtimestamp(x["date"]))

        yield yielded_row


# Also exports to csv
def build_strings(filename, operations):
    with open("data/" + filename + '.csv', "w") as f:
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

            if len(multi_row_chunk) > 20:
                csvwriter.writerows(multi_row_chunk)
                multi_row_chunk.clear()


deletes_optimized = 0
inserts_optimized = 0
def optimize_operations(operations):
    global deletes_optimized, inserts_optimized
    index = 0
    last_time = operations[0]["date"]
    while index < len(operations) -1:
        cur_op = operations[index]
        next_op = operations[index + 1]

        # Coalesce multiple insert operations into one
        if (
            next_op["type"] == cur_op["type"]
            and next_op["date"] - cur_op["date"] < 5 * 1000
            and cur_op["date"] - last_time < 60*1000
        ):
            if (
                cur_op["type"] == "is"
                and cur_op["start_index"] + len(cur_op["content"]) == next_op["start_index"]
            ):
                inserts_optimized += 1
                cur_op["content"] += next_op["content"]
                operations.pop(index+1)
                index-=1
            
            elif cur_op["type"] == "ds" and cur_op["start_index"] == next_op["end_index"]:
                deletes_optimized += 1
                cur_op["content"] = next_op["content"] + cur_op["content"]
                cur_op["start_index"] = next_op["start_index"]
                operations.pop(index+1)
                index -=1


        else:
            last_time = cur_op["date"]
        index+=1


def check_valid_file(name):
    return os.path.exists(f"data/{name}.csv")

def write_zip(name):
    import zipfile
    with zipfile.ZipFile(
        f"data/{name}.csv.zip", "w", compression=zipfile.ZIP_LZMA
    ) as zip:
        zip.write(f"data/{name}.csv", arcname=f"{name}.csv")
    return f"{name}.csv.zip"


def process_file(id, oauth_token):
    secret_user_id = f"{id}-{secrets.token_urlsafe(128)}"
    revision_response = download_operations(id, oauth_token)
    operations = process_operations(revision_response)
    build_strings(secret_user_id, operations)
    optimize_operations(operations)
    return operations, secret_user_id


def default_process_file():
    secret_user_id = f"default-{secrets.token_urlsafe(128)}"
    operations= json.load(open("data/default_data.txt", "r"))
    build_strings(secret_user_id, operations)
    optimize_operations(operations)
    return operations, secret_user_id


def main_test():
    import pickle
    from google.auth.transport.requests import Request
    from datetime import datetime

    token = pickle.load(open("creds2.pickle", "rb"))
    token.refresh(Request())
    id = "1nOVrSDsk_kJG9u6SCvVlE6cLfRmGsAmHP2b2QjtsJh0"
    id_abc = "127N5XfCjm2LLovl1l1ODxglo4HOatv_ox9qFHA-WP7I"
    data = process_file(id, token.token)

    datestr = datetime.now().strftime("%d_%H_%M")
    data = json.dumps(data)
    open(f"/home/henry/gdocs-website/static/js/test_data_{datestr}.json", "w").write(data)
    print(inserts_optimized, deletes_optimized)


if __name__ == "__main__":
    main_test()
