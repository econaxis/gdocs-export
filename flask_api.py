import ujson as json
import flask
from flask_cors import CORS
import get_files


from datetime import datetime

app = flask.Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
SERVER_START = datetime.now()
# Get the data for specific user id

def get_word_counts(session_id):
    pass

def get_insertions_deletions(session_id):
    pass

def get_default_data():
    pass

@app.route('/')
def print_default():
    return "The app is working!"

@app.route('/start', methods = ['POST'])
def start_processing_file():
    print(flask.request.json)
    request_parameters = flask.request.json
    operations = get_files.process_file(request_parameters['file_id'], request_parameters['oauth_token'])

    return json.dumps(operations)

@app.route('/prime')
def prime_server():
    return f"Response received at {datetime.now()}. Server started at {SERVER_START}"
