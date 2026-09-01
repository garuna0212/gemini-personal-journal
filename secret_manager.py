import os
from pathlib import Path

import google.auth
from dotenv import load_dotenv
from google.cloud import secretmanager


env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")

if not PROJECT_ID:
    _, PROJECT_ID = google.auth.default()

if not PROJECT_ID:
    raise ValueError("Google Cloud project ID could not be determined")


GEMINI_SECRET_NAME = "GEMINI_API_KEY"

def get_gemini_api_key():
    local_key = os.getenv("GEMINI_API_KEY")

    if local_key:
        return local_key

    client = secretmanager.SecretManagerServiceClient()

    secret_path = (
        f"projects/{PROJECT_ID}/secrets/"
        f"{GEMINI_SECRET_NAME}/versions/latest"
    )

    response = client.access_secret_version(
        request={"name": secret_path}
    )

    return response.payload.data.decode("UTF-8")
def get_session_secret():
    local_secret = os.getenv("SESSION_SECRET")

    if local_secret:
        return local_secret

    client = secretmanager.SecretManagerServiceClient()

    secret_path = (
        f"projects/{PROJECT_ID}/secrets/"
        f"SESSION_SECRET/versions/latest"
    )

    response = client.access_secret_version(
        request={"name": secret_path}
    )

    return response.payload.data.decode("UTF-8")