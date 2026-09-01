from firebase_admin import firestore

db = firestore.client()


def add_entry(uid, content, analysis=None):
    entry = {
        "content": content,
        "analysis": analysis,
        "archived": False,
        "vaulted": False,
        "created_at": firestore.SERVER_TIMESTAMP
    }

    db.collection("users") \
        .document(uid) \
        .collection("entries") \
        .add(entry)


def get_entries(uid):
    docs = (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .where("archived", "==", False)
        .where("vaulted", "==", False)
        .stream()
    )

    entries = []

    for doc in docs:
        data = doc.to_dict()

        entries.append({
            "id": doc.id,
            "content": data.get("content"),
            "analysis": data.get("analysis"),
            "created_at": data.get("created_at")
        })

    return entries
def get_entry(uid, entry_id):
    doc = (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .document(entry_id)
        .get()
    )

    if not doc.exists:
        return None

    data = doc.to_dict()

    return {
        "id": doc.id,
        "content": data.get("content"),
        "analysis": data.get("analysis"),
        "created_at": data.get("created_at"),
        "archived": data.get("archived", False),
        "vaulted": data.get("vaulted", False)
    }


def update_analysis(uid, entry_id, analysis):
    (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .document(entry_id)
        .update({
            "analysis": analysis
        })
    )
def update_entry(uid, entry_id, content):
    (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .document(entry_id)
        .update({
            "content": content,
            "analysis": None
        })
    )


def delete_entry(uid, entry_id):
    (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .document(entry_id)
        .delete()
    )
def archive_entry(uid, entry_id):
    (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .document(entry_id)
        .update({
            "archived": True
        })
    )


def restore_entry(uid, entry_id):
    (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .document(entry_id)
        .update({
            "archived": False
        })
    )


def get_archived_entries(uid):
    docs = (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .where("archived", "==", True)
        .stream()
    )

    entries = []

    for doc in docs:
        data = doc.to_dict()

        entries.append({
            "id": doc.id,
            "content": data.get("content"),
            "analysis": data.get("analysis"),
            "created_at": data.get("created_at")
        })

    return entries
def move_to_vault(uid, entry_id):
    (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .document(entry_id)
        .update({
            "vaulted": True,
            "archived": False
        })
    )


def remove_from_vault(uid, entry_id):
    (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .document(entry_id)
        .update({
            "vaulted": False
        })
    )


def get_vault_entries(uid):
    docs = (
        db.collection("users")
        .document(uid)
        .collection("entries")
        .where("vaulted", "==", True)
        .stream()
    )

    entries = []

    for doc in docs:
        data = doc.to_dict()

        entries.append({
            "id": doc.id,
            "content": data.get("content"),
            "analysis": data.get("analysis"),
            "created_at": data.get("created_at")
        })

    return entries
def set_vault_pin(uid, salt, pin_hash):
    db.collection("users").document(uid).set(
        {
            "vault_pin_salt": salt,
            "vault_pin_hash": pin_hash
        },
        merge=True
    )


def get_vault_pin(uid):
    doc = db.collection("users").document(uid).get()

    if not doc.exists:
        return None

    data = doc.to_dict()

    salt = data.get("vault_pin_salt")
    pin_hash = data.get("vault_pin_hash")

    if not salt or not pin_hash:
        return None

    return {
        "salt": salt,
        "hash": pin_hash
    }