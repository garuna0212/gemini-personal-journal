import firebase_admin
from firebase_admin import auth

PROJECT_ID = "gen-lang-client-0715483676"

if not firebase_admin._apps:
    firebase_admin.initialize_app(
        options={
            "projectId": PROJECT_ID
        }
    )


def verify_firebase_token(id_token):
    decoded_token = auth.verify_id_token(id_token)

    return {
        "uid": decoded_token["uid"],
        "email": decoded_token.get("email"),
        "name": decoded_token.get("name")
    }