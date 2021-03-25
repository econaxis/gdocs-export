import requests
import auth
import csv
import pickle
import ujson as json

from requests.adapters import HTTPAdapter
from google.auth.transport.requests import Request

from requests.packages.urllib3.util.retry import Retry

from datetime import datetime

GDOCS_FILE_ID = "1nOVrSDsk_kJG9u6SCvVlE6cLfRmGsAmHP2b2QjtsJh0"

retry_strategy = Retry(
    total=1,
    status_forcelist=[413, 429, 500],
    allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
    backoff_factor=0.5
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

revision_data_url = 'https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start=1&end={end}'
revision_url = 'https://www.googleapis.com/drive/v3/files/{}/revisions'


def download_operations(file_id, token):
    auth_header = dict(authorization=f"Bearer {token}")
    # auth_header = dict()
    rev_id_response = requests.get(url=revision_url.format(file_id), headers=auth_header)
    if rev_id_response.status_code != 200:
        print(rev_id_response.text)
        raise RuntimeError("not 200")
    rev_id_response = json.loads(rev_id_response.text)
    last_rev_id = rev_id_response["revisions"][-1]["id"]

    revision_response = http.get(url=revision_data_url.format(file_id=file_id, end=last_rev_id),
                                 headers=auth_header).text[5:]
    revision_response = json.loads(revision_response)

    operations = []

    for x in revision_response['changelog']:
        if x[0]['ty'] not in {'is', 'ds', 'mlti'}:
            continue

        if x[0]['ty'] == 'mlti':
            for i in x[0]['mts']:
                revision_response['changelog'].append([i, x[1]])
            continue

        if x[0]['ty'] == 'is':
            content = x[0]['s']
            index = x[0]['ibi'] - 1
        elif x[0]['ty'] == 'ds':
            index = [x[0]['si'], x[0]['ei'] + 1]

        if content:
            operations.append(
                dict(date=datetime.utcfromtimestamp(x[1] / 1e3), content=content, index=index, type=x[0]['ty']))

    operations = sorted(operations, key=lambda k: k['date'])

    cur_string = []
    for x in operations:
        if x["type"] == "is":
            char_content = list(x["content"])
            cur_string[x["index"]:x["index"]] = char_content
        elif x["type"] == "ds":
            cur_string[x["index"][0]:x["index"][1]] = []
        x["cur_string"] = ''.join(cur_string)
        x["word_count"] = cur_string.count(" ")
    return operations


def export_csv(name, operations):
    with open(name, 'w') as f:
        csvwriter = csv.DictWriter(f, dialect="excel", extrasaction="ignore",
                                   fieldnames=["date", "cur_string", "word_count"], escapechar='\\', doublequote=False)
        csvwriter.writeheader()
        for x in operations:
            csvwriter.writerow(x)


if __name__ == "__main__":
    try:
        creds = pickle.load(open("data/creds2.pickle", "rb"))
    except FileNotFoundError:
        creds = auth.run_auth_flow()
        pickle.dump(creds, open('data/creds2.pickle', 'wb'))
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError("creds not valid")
    operations = download_operations(GDOCS_FILE_ID, creds.token)
    export_csv('operations.csv', operations)
    print(operations[-1]["cur_string"])
    print(len(operations))
