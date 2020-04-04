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

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

sys.path.insert(1, '../')
user_id = str(uuid.uuid4())
class Config:
    SECRET_KEY = user_id

CONF = Config()

homePath = "/mnt/c/users/henry/documents/pydocs/"
app = Flask(__name__)
app.config.from_object(CONF)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
        'https://www.googleapis.com/auth/drive.activity.readonly']

@app.route('/authorize/')
def authorize():
    print("Starting authorization method")

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

    workingPath = homePath + "data/" + user_id + "/"
    Path(workingPath).mkdir(exist_ok = True)

    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      homePath + 'secret/credentials.json', scopes=SCOPES, state=state)

    flow.redirect_uri = flask.url_for('oauth', _external=True)

    authorization_response = flask.request.url

    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    print ("saving creds")

    with open(workingPath + "creds.pickle", 'wb') as c:
      pickle.dump(credentials, c)

    flask.session["workingPath"] = workingPath
    #Store userId in a session variable for process data method
    flask.session["userId"] = user_id

    return flask.redirect(flask.url_for('process_data'))

@app.route("/process/")
@app.route("/process/<userid>")
def process_data(userid = None):

    #function can be called normally from oauth, when user first authenticates
    #or function can be called from URL without authenticate 


    #Get working path from session, or create from homePath
    #Gets userId either from flask session or from params
    workingPath = None
    if(flask.session.get("workingPath") != None):
        workingPath = flask.session.get("workingPath")
        userid = flask.session.get("userId")
    else:
        workingPath = homePath + "data/" + userid + "/"
        #Implicit userid is from params

    print("USERID %s WPATH %s"%(userid, workingPath))

    #Check if there exists a creds.pickle file at USERID
    if (not os.path.exists(workingPath+"creds.pickle")):
        #Pickle doesn't exist?
        #Reload back to authenticate screen
        print("no creds found, wpath: %s"%workingPath)
        return flask.redirect(flask.url_for('authorize'))
    else:
        print("Nothing wrong")

    import test
    print("processing data...")
    print("user id is %s"%user_id)
    #test.main( user_id, homePath)
    return "w"


@app.route("/form", methods = ["GET", "POST"])
def formValidate():
    form = Form()
    print("submitting")
    #if(form.validate_on_submit()):
    return render_template('form.html', form = form)

if __name__ == "__main__":
    app.run(debug = True)
