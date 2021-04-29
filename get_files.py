import requests
from datetime import datetime
import csv
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os
import secrets

# If the user doesn't submit any valid fileID, then we use this default file ID to have something for the user to see.
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

# URL to load the revisions data
revision_data_url = "https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start=1&end={end}"

# URL to find the number of revisions a file has.
revision_url = "https://www.googleapis.com/drive/v3/files/{}/revisions"


def download_operations(file_id, token):
    """
    Downloads the Google Docs revision data as JSOn format. Does no additional processing.

    :param file_id: The Google Docs fileid as a string.
    :param token: The authorization token. This should be requested in front-end Javascript.

    :return: Dict containing the JSON of Google Docs response.
    """

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
    """
    Processes the operations downloaded from Google Docs.

    :param revision_response: The dict downloaded from Google Docs.
    :return: An array of operations. Each operation is a dict as follows:
            {
                date: timestamp (milliseconds)
                content: what text was inserted or deleted
                start_index: at what index in the document was the text inserted/deleted
                end_index (valid only for deletion): to what index to delete to
                type: 'is' for insertion, 'ds' for deletion.
            }
    """
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
            end_index = x[0]["ei"]

        operations.append(
            dict(date=x[1], content=content, start_index=start_index, end_index=end_index, type=x[0]["ty"])
        )

    operations = sorted(operations, key=lambda k: k["date"])
    return operations


def build_strings_generator(operations):
    """
    Generator function to transform operations to actual text. It builds the document from the list of operations
    (basically applying diffs sequentially). For each operation, it yields the document state at that time.

    :param operations: List of operations for which to build the document state.

    :return yields a dict similar to an operation, but with one additional key "cur_string" whose value is the document
        state (as a string).
    """

    cur_string = []
    x_keys = operations
    for x in x_keys:
        yielded_row = {}
        if x["type"] == "is":
            char_content = list(x["content"])
            cur_string[x["start_index"]: x["start_index"]] = char_content
        elif x["type"] == "ds":
            x["content"] = "".join(cur_string[x["start_index"]: x["end_index"]])
            cur_string[x["start_index"]: x["end_index"]] = []
        x["word_count"] = cur_string.count("\n") + cur_string.count(" ")

        yielded_row["word_count"] = x["word_count"]
        yielded_row["cur_string"] = "".join(cur_string)

        yielded_row["date"] = str(datetime.fromtimestamp(x["date"] / 1000))

        yield yielded_row


# Also exports to csv
def build_strings(filename, operations):
    """
    :param filename: what CSV filename to output to.
    :param operations: list of operations to work on.
    """
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


def optimize_operations(operations):
    """
    Mutates the operations list. Coalesces similar operations into one operation. Coalesces multiple deletion operations
        into one.
    :param operations: List of operations (function mutates the dict).
    :return:
    """
    index = 0
    last_time = operations[0]["date"]
    while index < len(operations) - 1:
        cur_op = operations[index]
        next_op = operations[index + 1]

        # Coalesce multiple insert operations into one
        if (
                next_op["type"] == cur_op["type"]
                and next_op["date"] - cur_op["date"] < 5 * 1000
                and cur_op["date"] - last_time < 60 * 1000
        ):
            if (
                    cur_op["type"] == "is"
                    and cur_op["start_index"] + len(cur_op["content"]) == next_op["start_index"]
            ):
                cur_op["content"] += next_op["content"]
                operations.pop(index + 1)
                index -= 1

            elif cur_op["type"] == "ds" and cur_op["start_index"] == next_op["end_index"]:
                cur_op["content"] = next_op["content"] + cur_op["content"]
                cur_op["start_index"] = next_op["start_index"]
                operations.pop(index + 1)
                index -= 1


        else:
            last_time = cur_op["date"]
        index += 1


def check_valid_file(name):
    return os.path.exists(f"data/{name}.csv")


def write_zip(name):
    """
    Converts a file to a zip file ideal for transferring over web.
    :param name: filename
    :return: zipped filename.
    """
    import zipfile
    with zipfile.ZipFile(
            f"data/{name}.csv.zip", "w", compression=zipfile.ZIP_LZMA
    ) as zip:
        zip.write(f"data/{name}.csv", arcname=f"{name}.csv")
    return f"{name}.csv.zip"


def process_file(id, oauth_token):
    """
    Main entrypoint function to get an optimized array of operations for a given file id.
    Also writes the operations to a CSV file.
    :param id: fileid
    :param oauth_token: authorization token obtained using Google Picker API from browser Javascript.
    :return: condensed list of operations, and an ID to obtain a zipped operations file if the user wants to download
        it later on.
    """
    secret_user_id = f"{id}-{secrets.token_urlsafe(128)}"
    revision_response = download_operations(id, oauth_token)
    operations = process_operations(revision_response)
    build_strings(secret_user_id, operations)
    optimize_operations(operations)
    return operations, secret_user_id


def default_process_file():
    # If there's no fileid given, then call this function to get a default operations. Used for debugging.
    secret_user_id = f"default-{secrets.token_urlsafe(128)}"
    operations = json.load(open("data/default_data.txt", "r"))
    build_strings(secret_user_id, operations)
    optimize_operations(operations)
    return operations, secret_user_id


def _debug_main_test():
    # Debugging function.
    import pickle
    from google.auth.transport.requests import Request
    from datetime import datetime

    token = pickle.load(open("creds2.pickle", "rb"))
    token.refresh(Request())
    id = "1nOVrSDsk_kJG9u6SCvVlE6cLfRmGsAmHP2b2QjtsJh0"
    data = process_file(id, token.token)

    datestr = datetime.now().strftime("%d_%H_%M")
    data = json.dumps(data)
    open(f"/home/henry/gdocs-website/static/js/test_data_{datestr}.json", "w").write(data)


if __name__ == "__main__":
    _debug_main_test()
