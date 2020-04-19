import flask
from flask import Flask, Blueprint
from flask import current_app, redirect
import uuid
from pathlib import Path
import google.oauth2.credentials
import pickle
import google_auth_oauthlib.flow


auth_bp = Blueprint('auth_bp', __name__)


@auth_bp.route('/authorize')
def authorize():
    if(not flask.session.get('signedin')):
        return redirect(flask.url_for('auth_bp.glogin'))
    else:
        # Sign out called
        flask.session.clear()
        request = redirect(flask.url_for('server.home'))
        request.set_cookie('userid', value="", max_age=0)
        return request


@auth_bp.route('/glogin')
def glogin():
    # Expected point for start of authorization chain
    print("Starting authorization method")

    # Use server secret file
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        current_app.config["HOMEPATH"] + 'secret/credentials.json', current_app.config["SCOPES"])

    # Set redirect URI for when authentication starts
    flow.redirect_uri = flask.url_for('auth_bp.oauth', _external=True)

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true', prompt='consent')
    print("requesting")

    flask.session['state'] = state

    return flask.redirect(authorization_url)


@auth_bp.route('/oauth')
def oauth():
    # Second part of authorizatoin cycle

    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        current_app.config["HOMEPATH"] + 'secret/credentials.json', scopes=current_app.config["SCOPES"], state=state)

    flow.redirect_uri = flask.url_for('auth_bp.oauth', _external=True)

    authorization_response = flask.request.url

    flow.fetch_token(authorization_response=authorization_response)

    userid = flask.session["userid"]

    workingPath = current_app.config["HOMEPATH"] + "data/" + userid + "/"
    Path(workingPath).mkdir(exist_ok=True)

    credentials = flow.credentials
    with open(workingPath + "creds.pickle", 'wb') as c:
        pickle.dump(credentials, c)
        print("auth_bp dumped credentials at ", workingPath + "creds.pickle")

    flask.session['signedin'] = True

    return flask.redirect(flask.url_for('server.formValidate'))
