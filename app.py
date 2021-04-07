import json
import os
import requests

from flask import Flask, redirect, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from oauthlib.oauth2 import WebApplicationClient

from user import User
from flask import Flask, render_template
from jinja2 import Template

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)

GOOGLE_DISCOVERY_URL = ("https://accounts.google.com/.well-known/openid-configuration")
GOOGLE_AUTHORIZATION_ENDPOINT =  "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT =  "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT =  "https://openidconnect.googleapis.com/v1/userinfo"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

login_manager = LoginManager()
login_manager.init_app(app)

oauth_client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Very volatile userdb
userdb = {}

# This is required for Flask login
@login_manager.user_loader
def load_user(user_id):
    if user_id in userdb:
        return userdb[user_id]
    else:
        return None

@app.route("/", methods=['GET'])
def index():
    return render_template('index.html')

@app.route("/login", methods=['GET'])
def login():

    # Create the OAuth AuthZ request
    auth_uri = oauth_client.prepare_request_uri(
        GOOGLE_AUTHORIZATION_ENDPOINT,
        redirect_uri=f"{ request.url_root }callback",
        scope=["openid", "profile", "email"]
    )
    return redirect(auth_uri, code=302)

@app.route("/callback", methods=['GET'])
def callback():

    # AuthZ Grant from Google
    code = request.args.get("code")

    # Prepare request for Access token
    url, headers, body = oauth_client.prepare_token_request(
        GOOGLE_TOKEN_ENDPOINT,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )

    # Change AuthZ token for Access Token
    access_token_response = requests.post(
        url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
    )
    
    # Parse the request body out of
    r = access_token_response.json()
    oauth_client.parse_request_body_response(json.dumps(r))

    # Debug to stdout
    print("oauth access:token: ", r.get('access_token'))
    print("oidc id_token: ", r.get('id_token'))

    uri, headers, body = oauth_client.add_token(GOOGLE_USERINFO_ENDPOINT)

    # Send request to IdP
    userinfo = requests.get(uri, headers=headers, data=body)
    

    # Create User based on IdP response    
    user = User(
        id_=userinfo.json()["sub"],
        given_name=userinfo.json()["given_name"],
        family_name=userinfo.json()["family_name"],
        email=userinfo.json()["email"],
        picture=userinfo.json()["picture"],
        email_verified=userinfo.json()["email_verified"],
        locale=userinfo.json()["locale"]
    )

    # Add user to DB indexed by sub / user_id
    userdb[userinfo.json()["sub"]] = user

    # Flask-Login with user created
    login_user(user)

    # Redirect to front page, now user succcesfully logged in
    return redirect(url_for("index"), code=302)
 

@app.route("/logout", methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(ssl_context="adhoc", debug=True)
