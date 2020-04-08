# app.py
from pathlib import Path
import pickle
from flask import render_template, flash, redirect
import flask
from flask import Flask
from wtforms import StringField, PasswordField
from form import Form
import uuid
import google.oauth2.credentials
import google_auth_oauthlib.flow
import sys
import os
#from config import Config


#Necessary for non HTTPS OAUTH calls
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

#Adds pydoc path to import directory
sys.path.insert(1, '../')


class Config:
    SECRET_KEY = "dsfjslkfdsjflkdsa;fsajl;fakj"

CONF = Config()

homePath = "/mnt/c/users/henry/documents/pydocs/"
app = Flask(__name__)
app.config.from_object(CONF)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
        'https://www.googleapis.com/auth/drive.activity.readonly']


@app.route('/authorize')
def authorize():
    if(not flask.session.get('signedin')):
        return redirect(flask.url_for('glogin'))
    else:
        #Sign out called
        flask.session.clear()

        request = redirect(flask.url_for('home'))
        request.set_cookie('userid', value = "", max_age = 0)
        return request


@app.route('/glogin')
def glogin():
    #Expected point for start of authorization chain
    print("Starting authorization method")

    #config = Config(homePath = homePath)
#    config.generate_id()
    #app.config.from_object(config.get_flask_config())
    #app.config.from_ob


    #Use server secret file
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        homePath + 'secret/credentials.json', scopes=SCOPES)


    #Set redirect URI for when authentication starts
    flow.redirect_uri = flask.url_for('oauth', _external=True)



    authorization_url, state = flow.authorization_url(
      access_type='offline',
      include_granted_scopes='true', prompt = 'consent')

    flask.session['state'] = state

    return flask.redirect(authorization_url)

@app.route('/oauth')
def oauth():
    #Second part of authorizatoin cycle

    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      homePath + 'secret/credentials.json', scopes=SCOPES, state=state)

    flow.redirect_uri = flask.url_for('oauth', _external=True)

    authorization_response = flask.request.url

    flow.fetch_token(authorization_response=authorization_response)


    userid = str(uuid.uuid4())
    workingPath = homePath + "data/" + userid + "/"
    Path(workingPath).mkdir(exist_ok = True)

    credentials = flow.credentials
    with open(workingPath + "creds.pickle", 'wb') as c:
      pickle.dump(credentials, c)

    flask.session['signedin'] = True
    flask.session['userid'] = userid

    return flask.redirect(flask.url_for('formValidate'))

@app.route("/process/")
@app.route("/process/<_userid>")
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
        return flask.redirect(flask.url_for('glogin'))


    flask.session['userid'] = userid

    if(not check_signin(userid)):
        return "invalid signin"
    #Store cookie for 30 days

    #Get working path from session, or create from homePath
    #Gets userId either from flask session or from params

    workingPath = homePath + "data/" + userid + "/"
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
        htmlResponse = redirect(flask.url_for('process_data', _userid = userid))


    htmlResponse.set_cookie('userid', userid, max_age  = 60*60*24*30)
    return htmlResponse

@app.route("/form", methods = ["GET", "POST"])
def formValidate():
    form = Form()
    if(form.validate_on_submit()):
        print(form.fileId.data)
        flask.session["fileid"] = form.fileId.data
        if ('userid' in flask.session and check_signin(flask.session['userid'])):
            flask.session['newsession'] = True
            return redirect(flask.url_for('process_data', _userid = flask.session["userid"]))
        else:
            return "have to sign in"

    print("signed in :" , flask.session.get('signedin'))
    return render_template('main.html', _form = form, SIGNED_IN = flask.session.get('signedin'))

@app.route("/")
def home():
    return redirect(flask.url_for('formValidate'))


@app.route("/jek")
def jek_serve():
    print("strating")
    return render_template('from_jekyll/test.html')


@app.route('/dashapp')
def dashapp():
    return 'w'

def check_signin(userid):
    workingPath = homePath + "data/" + userid + "/"
    if (not os.path.exists(workingPath+"creds.pickle")):
        #Pickle doesn't exist?
        #Reload back to authenticate screen
        print("no creds found, wpath: %s"%workingPath)
        return False
    return True
if __name__ == "__main__":
    app.run(debug = True)
