import ujson as json
import flask
from flask_cors import CORS
import get_files

from datetime import datetime

app = flask.Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers = 'user-id')
SERVER_START = datetime.now()


# Get the data for specific user id


def get_word_counts(session_id):
    pass


def get_insertions_deletions(session_id):
    pass


def get_default_data():
    pass


@app.route("/")
def print_default():
    return "The app is working!"


@app.route("/start", methods=["POST"])
def start_processing_file():
    request_parameters = flask.request.json
    if not request_parameters or "file_id" not in request_parameters:
        print("no request id found, defaulting")
        request_parameters = dict(file_id=get_files.GDOCS_FILE_ID)
        operations = get_files.default_process_file()
    else:
        operations = get_files.process_file(
            request_parameters["file_id"], request_parameters["oauth_token"]
        )
    response = flask.make_response(json.dumps(operations))
    response.headers["user-id"] = request_parameters["file_id"]
    return response


@app.route("/downloadcsv", methods=["POST", "GET"])
def download_zipped_csv():
    user_id = None
    if flask.request.method == 'POST':
        if not flask.request.json or "user-id" not in flask.request.json:
            return "User id must be present in request body"
        else:
            user_id = flask.request.json["user-id"]
    elif flask.request.method == 'GET':
        if flask.request.args.get('user-id'):
            user_id = flask.request.args.get('user-id')
        else:
            return "User id not present in URL params"
    return flask.send_from_directory(
        app.root_path + "/data", get_files.write_zip(user_id), as_attachment=True
    )


@app.route("/prime")
def prime_server():
    return f"Response received at {datetime.now()}. Server started at {SERVER_START}"
