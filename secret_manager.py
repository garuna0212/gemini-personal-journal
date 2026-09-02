import os
from pathlib import Path

import google.auth
from dotenv import load_dotenv
from google.cloud import secretmanager


# ---------------------------------------------------------
# Load local environment variables
# ---------------------------------------------------------

env_path = Path(__file__).parent / ".env"

load_dotenv(
    dotenv_path=env_path
)


# ---------------------------------------------------------
# Determine Google Cloud project
# ---------------------------------------------------------

PROJECT_ID = os.getenv(
    "GOOGLE_CLOUD_PROJECT"
)

if not PROJECT_ID:

    _, PROJECT_ID = google.auth.default()


if not PROJECT_ID:

    raise ValueError(
        "Google Cloud project ID could not be determined"
    )


# ---------------------------------------------------------
# Secret names
# ---------------------------------------------------------

GEMINI_SECRET_NAME = "GEMINI_API_KEY"
SESSION_SECRET_NAME = "SESSION_SECRET"


# ---------------------------------------------------------
# Read Secret Manager value
# ---------------------------------------------------------

def get_secret(secret_name):

    client = (
        secretmanager
        .SecretManagerServiceClient()
    )

    secret_path = (
        f"projects/{PROJECT_ID}/secrets/"
        f"{secret_name}/versions/latest"
    )

    response = client.access_secret_version(
        request={
            "name": secret_path
        }
    )

    return (
        response
        .payload
        .data
        .decode("UTF-8")
        .strip()
    )


# ---------------------------------------------------------
# Gemini API key
# ---------------------------------------------------------

def get_gemini_api_key():

    environment = os.getenv(
        "ENVIRONMENT",
        "development"
    )

    # Production must always use Secret Manager
    if environment == "production":

        return get_secret(
            GEMINI_SECRET_NAME
        )


    # Local development may optionally use .env
    local_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if local_key:

        return local_key.strip()


    # Otherwise use Secret Manager locally too
    return get_secret(
        GEMINI_SECRET_NAME
    )


# ---------------------------------------------------------
# Session secret
# ---------------------------------------------------------

def get_session_secret():

    environment = os.getenv(
        "ENVIRONMENT",
        "development"
    )

    # Production must always use Secret Manager
    if environment == "production":

        return get_secret(
            SESSION_SECRET_NAME
        )


    # Optional local development secret
    local_secret = os.getenv(
        "SESSION_SECRET"
    )

    if local_secret:

        return local_secret.strip()


    return get_secret(
        SESSION_SECRET_NAME
    )