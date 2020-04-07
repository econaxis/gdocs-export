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

@app.route('/authorize/')
def authorize():
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


    credentials = flow.credentials
    with open(workingPath + "creds.pickle", 'wb') as c:
      pickle.dump(credentials, c)


    return flask.redirect(flask.url_for('process_data', userid = userid))

@app.route("/process/")
@app.route("/process/<userid>")
def process_data(userid = None):

    #function can be called normally from oauth, when user first authenticates
    #or function can be called from URL without authenticate 


    #Set cookie for process
    htmlResponse = flask.make_response("Processing data")

    #If there is a cookie and no userid is entered
    if(flask.request.cookies.get('userid') and userid is None):
        userid = flask.request.cookies.get('userid')
    elif (not flask.request.cookies.get('userid') and userid is None):
        print("No cookie nor userid entered, redirecting to auth page")
        return flask.redirect(flask.url_for('authorize'))

    htmlResponse.set_data(htmlResponse.get_data(as_text = True) + "user id: \n"+userid)
    #Store cookie for 30 days
    htmlResponse.set_cookie('userid', userid, max_age  = 60*60*24*30)

    #Get working path from session, or create from homePath
    #Gets userId either from flask session or from params

    workingPath = homePath + "data/" + userid + "/"
    Path(workingPath).mkdir(exist_ok = True)

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
    #test.main( userid, homePath, workingPath)



    return htmlResponse


@app.route("/form", methods = ["GET", "POST"])
def formValidate():
    form = Form()
    print("submitting")
    #if(form.validate_on_submit()):
    return render_template('form.html', form = form)

if __name__ == "__main__":
    app.run(debug = True)
