from pathlib import Path
import pickle
from flask import render_template, flash, redirect, Blueprint
import flask
from flask import Flask
from wtforms import StringField, PasswordField
from form import Form
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

    if(_userid != None):
        userid = _userid
    elif ('userid' in flask.session):
        userid = flask.session['userid']
    elif (flask.request.cookies.get('userid')):
        userid = flask.request.cookies.get('userid')
    else:
        print("No cookie nor userid entered, redirecting to auth page")
        return flask.redirect(flask.url_for('server.glogin'))


    flask.session['userid'] = userid

    if(not check_signin(userid)):
        return "invalid signin"
    #Store cookie for 30 days

    #Get working path from session, or create from homePath
    #Gets userId either from flask session or from params

    workingPath = current_app.config.get("HOMEPATH") + "data/" + userid + "/"
    Path(workingPath).mkdir(exist_ok = True)

    print("USERID %s WPATH %s"%(userid, workingPath))

    #Check if there exists a creds.pickle file at USERID


    from get_files_loader import queueLoad

    #curJob is not used for now
    data = None
    htmlResponse = flask.make_response()


    fileId = None
    if 'fileid' in flask.session:
        fileId = flask.session["fileid"]
    else:
        return "Invalid file ID"


    if(os.path.exists(workingPath + 'streaming.txt') and not flask.session.get('newsession')):
        print("session found")
        data =  open(workingPath + 'streaming.txt', 'r').read()
        DONE = os.path.exists(workingPath+ 'done.txt')
        htmlResponse.set_data(render_template('process.html', data = data, userid = userid, DONE = DONE))
    else:
        print("new session started")
        flask.session['newsession'] = False
        curJob = queueLoad(userid, workingPath, fileId)
        htmlResponse = redirect(flask.url_for('server.process_data', _userid = userid))


    htmlResponse.set_cookie('userid', userid, max_age  = 60*60*24*30)
    return htmlResponse

@server.route("/form", methods = ["GET", "POST"])
def formValidate():
    form = Form()
    if(form.validate_on_submit()):
        print(form.fileId.data)
        flask.session["fileid"] = form.fileId.data
        if ('userid' in flask.session and check_signin(flask.session['userid'])):
            flask.session['newsession'] = True
            return redirect(flask.url_for('server.process_data', _userid = flask.session["userid"]))
        else:
            return "have to sign in"

    print("signed in :" , flask.session.get('signedin'))
    return render_template('main.html', _form = form, SIGNED_IN = flask.session.get('signedin'))

@server.route("/")
def home():
    return redirect(flask.url_for('server.formValidate'))


@server.route("/jek")
def jek_serve():
    print("strating")
    return render_template('from_jekyll/test.html')


@server.route('/dashapp')
def dashapp():
    return 'w'

def check_signin(userid):
    workingPath = current_app.config.get("HOMEPATH") + "data/" + userid + "/"
    if (not os.path.exists(workingPath+"creds.pickle")):
        #Pickle doesn't exist?
        #Reload back to authenticate screen
        print("no creds found, wpath: %s"%workingPath)
        return False
    return True
if __name__ == "__main__":
    app.run(debug = True)
