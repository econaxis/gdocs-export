import ujson as json
import flask
import get_files

app = flask.Flask(__name__)
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

@app.route('/start', methods = ['GET', 'POST'])
def start_processing_file():
    print(flask.request)

    request_parameters = flask.request.json
    operations = get_files.process_file(request_parameters['file_id'], request_parameters['oauth_token'])

    return json.dumps(operations)


@app.after_request
def after_request_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

