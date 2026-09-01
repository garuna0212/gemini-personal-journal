from firebase_admin import firestore

db = firestore.client()


def create_conversation(uid, title="New Conversation"):
    conversation_ref = (
        db.collection("users")
        .document(uid)
        .collection("conversations")
        .document()
    )

    conversation_ref.set({
        "title": title,
        "summary": None,
        "created_at": firestore.SERVER_TIMESTAMP
    })

    return conversation_ref.id


def add_message(uid, conversation_id, role, content):
    (
        db.collection("users")
        .document(uid)
        .collection("conversations")
        .document(conversation_id)
        .collection("messages")
        .add({
            "role": role,
            "content": content,
            "created_at": firestore.SERVER_TIMESTAMP
        })
    )


def get_messages(uid, conversation_id):
    docs = (
        db.collection("users")
        .document(uid)
        .collection("conversations")
        .document(conversation_id)
        .collection("messages")
        .order_by("created_at")
        .stream()
    )

    messages = []

    for doc in docs:
        data = doc.to_dict()

        messages.append({
            "id": doc.id,
            "role": data.get("role"),
            "content": data.get("content"),
            "created_at": data.get("created_at")
        })

    return messages


def get_conversations(uid):
    docs = (
        db.collection("users")
        .document(uid)
        .collection("conversations")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .stream()
    )

    conversations = []

    for doc in docs:
        data = doc.to_dict()

        conversations.append({
            "id": doc.id,
            "title": data.get("title"),
            "summary": data.get("summary"),
            "created_at": data.get("created_at")
        })

    return conversations


def update_conversation_summary(uid, conversation_id, summary):
    (
        db.collection("users")
        .document(uid)
        .collection("conversations")
        .document(conversation_id)
        .update({
            "summary": summary
        })
    )
def update_conversation_title(uid, conversation_id, title):
    (
        db.collection("users")
        .document(uid)
        .collection("conversations")
        .document(conversation_id)
        .update({
            "title": title
        })
    )
def delete_conversation(uid, conversation_id):
    conversation_ref = (
        db.collection("users")
        .document(uid)
        .collection("conversations")
        .document(conversation_id)
    )

    # Delete all messages first
    messages = conversation_ref.collection("messages").stream()

    for message in messages:
        message.reference.delete()

    # Delete the conversation document
    conversation_ref.delete()