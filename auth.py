from google_auth_oauthlib import flow


def run_auth_flow():
    # TODO: Uncomment the line below to set the `launch_browser` variable.
    appflow = flow.InstalledAppFlow.from_client_secrets_file(
        "secret/credentials.json",
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )

    appflow.run_local_server()

    return appflow.credentials
