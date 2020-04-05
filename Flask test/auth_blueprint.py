import flask
from flask import Flask, Blueprint
import uuid
import google.oauth2.credentials
import google_auth_oauthlib.flow


auth_blueprint = Blueprint('auth_blueprint', __name__)

@auth_blueprint.route('/authorize/')
def authorize():

    #Expected point for start of authorization chain


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

@auth_blueprint.route('/oauth')
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
