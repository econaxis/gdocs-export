import pickle
from flask import render_template, redirect, Blueprint, current_app
import flask
from flaskr.form import Form
import uuid
import os


server = Blueprint('server', __name__)


@server.route("/process/")
@server.route("/process/<_userid>")
def process_data(_userid=None):
    print("received user id: %s" % _userid)

    # function can be called normally from oauth, when user first authenticates
    # or function can be called from URL without authenticate
    userid = None
    if(_userid is not None):
        userid = _userid
    elif ('userid' in flask.session):
        userid = flask.session['userid']
    elif (flask.request.cookies.get('userid')):
        userid = flask.request.cookies.get('userid')
    else:
        return "no user id found"

    creds = check_signin(userid, load_creds=True)
    if(not creds and userid != 'a'):
        pass
        #return "creds not found for this userid, go back to home page"
    else:
        print("creds are valid")
    flask.session['userid'] = userid

    workingPath = current_app.config.get("HOMEDATAPATH") + userid + "/"

    flask.session['workingPath'] = workingPath

    print("USERID %s WPATH %s" % (userid, workingPath))

    htmlResponse = flask.make_response()

    if ('fileid' in flask.session):
        #This is called when a NEW task is contributed

        fileId = flask.session["fileid"]
        flask.session.pop("fileid")
        print("starting new task")
        from flaskr.get_files_loader import queueLoad
        queueLoad(userid, workingPath, fileId, creds)
        htmlResponse = redirect(
            flask.url_for(
                'server.process_data',
                _userid=userid))
    elif (os.path.exists(workingPath + 'streaming.txt')):
        data = None
        print("session found")
        data = open(workingPath + 'streaming.txt', 'r').read()
        DONE = os.path.exists(workingPath + 'done.txt')

        htmlResponse.set_data(render_template('process.html', data=data, userid=userid, DONE=DONE,
                                              DASH_LOC="/dashapp/" + userid))
    else:
        return """
            There is no file id found for the requested userid. This may be because you did not enter a fileid in <br>
            the previous page, or you entered the wrong userid. Your job may have not started processing yet.
            """

    htmlResponse.set_cookie('userid', userid, max_age=60 * 60 * 24 * 30)
    return htmlResponse


@server.route("/form", methods=["GET", "POST"])
def formValidate():
    form = Form()

    userid = None

    if ('userid' in flask.session):
        userid = flask.session['userid']
    elif (flask.request.cookies.get('userid')):
        userid = flask.request.cookies.get('userid')
    else:
        userid = str(uuid.uuid4())

    flask.session["userid"] = userid

    check_signin(userid)

    if(form.validate_on_submit()):
        flask.session["fileid"] = form.fileId.data
        if (check_signin(flask.session['userid'])
                and flask.session.get('signedin')):
            return redirect(flask.url_for('server.process_data',
                                          _userid=flask.session["userid"]))
        else:
            return "No credentials found for current user! This may be a bug, \
                you need to go back to the homepage, sign out, then sign in again."

    httpResp = flask.make_response(render_template('main.html', _form=form))
    httpResp.set_cookie('userid', userid, max_age=60 * 60 * 24 * 30)
    return httpResp


@server.route("/")
def home():
    return redirect(flask.url_for('server.formValidate'))


@server.route('/dashapp/<userid>')
def dashapp(userid):
    if(os.path.exists(current_app.config['HOMEDATAPATH'] + userid + '/done.txt')):
        return redirect("/dash/" + userid)
    else:
        return "cur job not done, don't try to access dash app"


@server.route('/debug')
def dbg():
    return flask.send_from_directory(
        directory=current_app.config["HOMEPATH"], filename='streaming.txt')


@server.route('/errors')
def dbg1():
    return flask.send_from_directory(
        directory=current_app.config["HOMEPATH"], filename='errors.txt')


def check_signin(userid, load_creds=False):
    workingPath = current_app.config.get("HOMEDATAPATH") + userid + "/"
    if (not os.path.exists(workingPath + "creds.pickle")):
        # Pickle doesn't exist?
        # Reload back to authenticate screen
        print("no creds found, wpath: %s" % workingPath)
        return False
    if (not load_creds):
        return True
    with open(workingPath + "creds.pickle", 'rb') as cr:
        return pickle.load(cr)


@server.route('/favicon.ico')
def favicon():
    return redirect(flask.url_for('static', filename='favicon.ico'))


@server.route('/wakemydyno.txt')
def wakedyno():
    return redirect(flask.url_for('static', filename='wakemydyno.txt'))


@server.route('/google41579b1449e3ad61.html')
def gver():
    print(current_app.root_path)
    return flask.send_from_directory(directory=current_app.root_path
                                     + '/static', filename='google41579b1449e3ad61.html')
