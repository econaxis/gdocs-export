from pathlib import Path
import pickle
from flask import render_template, flash, redirect, Blueprint, current_app
import flask
from flask import Flask
from wtforms import StringField, PasswordField
from flaskr.form import Form
import uuid
import google.oauth2.credentials
import google_auth_oauthlib.flow
import os


server = Blueprint('server', __name__)

@server.route("/process/")
@server.route("/process/<_userid>")
def process_data(_userid = None):
    print("received user id: %s"%_userid)

    #function can be called normally from oauth, when user first authenticates
    #or function can be called from URL without authenticate 
    userid = None
    if(_userid is not None):
        userid = _userid
    elif ('userid' in flask.session):
        userid = flask.session['userid']
    elif (flask.request.cookies.get('userid')):
        userid = flask.request.cookies.get('userid')
    else:
        return "no user id found"

    creds = check_signin(userid, load_creds = True)
    if(creds is None or creds is False):
        return "creds not found for this userid, go back to home page"
    else:
        print("creds are valid")
    flask.session['userid'] = userid

    workingPath = current_app.config.get("HOMEPATH") + "data/" + userid + "/"

    flask.session['workingPath'] = workingPath

    print("USERID %s WPATH %s"%(userid, workingPath))


    htmlResponse = flask.make_response()

    if(os.path.exists(workingPath + 'streaming.txt') and not flask.session.get('newsession')):
        data = None
        print("session found")
        data =  open(workingPath + 'streaming.txt', 'r').read()
        DONE = os.path.exists(workingPath+ 'done.txt')

        #TODO: change global url prefix /dash/ to CONFIG file
        htmlResponse.set_data(render_template('process.html', data = data, userid = userid, DONE = DONE,
            DASH_LOC = "/dashapp/" + userid))
    elif ('fileid' in flask.session):
        fileId = flask.session.get("fileid")
        from flaskr.get_files_loader import queueLoad
        flask.session['newsession'] = False
        curJob = queueLoad(userid, workingPath, fileId, creds)
        htmlResponse = redirect(flask.url_for('server.process_data', _userid = userid))
    else:
        return """
            There is no file id found for the requested userid. This may be because you did not enter a fileid in <br>
            the previous page, or you entered the wrong userid
            """

    htmlResponse.set_cookie('userid', userid, max_age  = 60*60*24*30)
    return htmlResponse


@server.route("/form", methods = ["GET", "POST"])
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

    creds = check_signin(userid)

    if(form.validate_on_submit()):
        flask.session["fileid"] = form.fileId.data
        if (check_signin(flask.session['userid']) and flask.session.get('signedin')):
            flask.session['newsession'] = True
            return redirect(flask.url_for('server.process_data', _userid = flask.session["userid"]))
        else:
            return "No credentials found for current user! This may be a bug, \
                you need to go back to the homepage, sign out, then sign in again."

    httpResp = flask.make_response(render_template('main.html', _form = form))
    httpResp.set_cookie('userid', userid, max_age  = 60*60*24*30)
    return httpResp

@server.route("/")
def home():
    return redirect(flask.url_for('server.formValidate'))


@server.route('/dashapp/<userid>')
def dashapp(userid):
    if(os.path.exists(current_app.config['HOMEDATAPATH'] + userid + '/DONE.txt')):
        return redirect("/dash/" + userid)
    else:
        return "cur job not done, don't try to access dash app"



def check_signin(userid, load_creds = False):
    workingPath = current_app.config.get("HOMEPATH") + "data/" + userid + "/"
    if (not os.path.exists(workingPath+"creds.pickle")):
        #Pickle doesn't exist?
        #Reload back to authenticate screen
        print("no creds found, wpath: %s"%workingPath)
        return False
    if (not load_creds):
        return True
    with open(workingPath + "creds.pickle", 'rb') as cr:
        return pickle.load(cr)
