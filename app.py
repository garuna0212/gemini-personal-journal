import os
import time
from datetime import timezone, timedelta
import secrets
import hmac
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from gemini_ai import analyze_journal 
import uvicorn
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from vault_security import hash_pin, verify_pin
from pydantic import BaseModel
from firebase_auth import verify_firebase_token
from starlette.middleware.sessions import SessionMiddleware
from secret_manager import get_session_secret
from typing import List
import markdown
import bleach
from markupsafe import Markup
from firestore_db import (
    add_entry as firestore_add_entry,
    get_entries as firestore_get_entries,
    get_entry as firestore_get_entry,
    update_analysis as firestore_update_analysis,
    update_entry as firestore_update_entry,
    delete_entry as firestore_delete_entry,
    archive_entry as firestore_archive_entry,
    restore_entry as firestore_restore_entry,
    get_archived_entries as firestore_get_archived_entries,
    move_to_vault as firestore_move_to_vault,
    remove_from_vault as firestore_remove_from_vault,
    get_vault_entries as firestore_get_vault_entries,
    set_vault_pin,
    get_vault_pin
    )
from conversation_db import (
    create_conversation,
    add_message,
    get_messages,
    get_conversations,
    update_conversation_summary,
    update_conversation_title,
    delete_conversation
    )

from conversation_ai import (
    generate_chat_reply,
    summarize_conversation
)


app = FastAPI()
load_dotenv()

SESSION_SECRET = get_session_secret()

if not SESSION_SECRET:
    raise ValueError("SESSION_SECRET is not configured")

IS_PRODUCTION = os.getenv("ENVIRONMENT") == "production"

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    https_only=IS_PRODUCTION,
    same_site="lax"
)

templates = Jinja2Templates(directory="templates")
INDIA_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

def format_datetime_india(value):
    if not value:
        return ""

    return value.astimezone(INDIA_TIMEZONE).strftime(
        "%d %b %Y · %I:%M %p"
    )
templates.env.filters["india_datetime"] = format_datetime_india
ALLOWED_MARKDOWN_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "blockquote",
]

def render_markdown(value):
    if not value:
        return ""

    rendered = markdown.markdown(
        value,
        extensions=["nl2br"]
    )

    cleaned = bleach.clean(
        rendered,
        tags=ALLOWED_MARKDOWN_TAGS,
        attributes={},
        strip=True
    )

    return Markup(cleaned)
def require_vault_access(request: Request):
    user = request.session.get("user")

    if not user:
        return None, RedirectResponse(
            url="/login",
            status_code=303
        )

    if not request.session.get(
        "vault_unlocked",
        False
    ):
        return None, RedirectResponse(
            url="/vault",
            status_code=303
        )

    return user, None


templates.env.filters["markdown"] = render_markdown
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_csrf_token(request: Request):
    token = request.session.get("csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token

    return token


def verify_csrf_token(
    request: Request,
    submitted_token: str
):
    session_token = request.session.get(
        "csrf_token"
    )

    if not session_token:
        return False

    if not submitted_token:
        return False

    return hmac.compare_digest(
        session_token,
        submitted_token
    )
templates.env.globals["csrf_token"] = get_csrf_token


def csrf_error_response():
    return HTMLResponse(
        content="Invalid or missing CSRF token.",
        status_code=403
    )


class LoginRequest(BaseModel):
    token: str


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )
@app.post("/auth/login")
def firebase_login(request: Request, data: LoginRequest):
    try:
        user = verify_firebase_token(data.token)

        request.session["user"] = {
            "uid": user["uid"],
            "email": user["email"],
            "name": user["name"]
        }

        return {
            "success": True
        }

    except Exception as e:
        print("Firebase verification error:", e)

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "Invalid Firebase authentication token"
            }
        )


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    uid = user["uid"]

    entries = firestore_get_entries(uid)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "entries": entries,
            "user": user
        }
    )

@app.post("/logout")
def logout(
    request: Request,
    csrf_token: str = Form(...)
):
    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    request.session.clear()

    return RedirectResponse(
        url="/login",
        status_code=303
    )


@app.post("/save", response_class=HTMLResponse)
def save_entry(
    request: Request,
    entry: str = Form(...),
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    firestore_add_entry(
        uid,
        entry
    )

    return RedirectResponse(
        url="/",
        status_code=303
    )


@app.post("/analyze", response_class=HTMLResponse)
def analyze_entry(
    request: Request,
    entry: str = Form(...),
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    result = analyze_journal(entry)

    analysis = result["analysis"]
    detected = result["detected"]
    protected_text = result["protected_text"]
    gemini_error = result.get("error")

    # Only save an analyzed entry when Gemini succeeds.
    # This prevents duplicate blank entries if the user retries after a
    # temporary Gemini service error.
    if analysis:
        firestore_add_entry(
            uid,
            entry,
            analysis
        )

    entries = firestore_get_entries(uid)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "entries": entries,
            "analysis": analysis,
            "detected": detected,
            "protected_text": protected_text,
            "gemini_error": gemini_error,
            "current_entry": entry,
            "user": user
        }
    )


@app.post("/delete/{entry_id}")
def remove_entry(
    request: Request,
    entry_id: str,
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    entry = firestore_get_entry(
        uid,
        entry_id
    )

    if not entry:
        return RedirectResponse(
            url="/",
            status_code=303
        )

    # A vaulted entry may only be deleted while the Vault is unlocked.
    if (
        entry.get("vaulted", False)
        and not request.session.get("vault_unlocked", False)
    ):
        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    firestore_delete_entry(
        uid,
        entry_id
    )

    redirect_url = (
        "/vault"
        if entry.get("vaulted", False)
        else "/"
    )

    return RedirectResponse(
        url=redirect_url,
        status_code=303
    )


@app.post("/edit/{entry_id}")
def edit_entry(
    request: Request,
    entry_id: str,
    content: str = Form(...),
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    entry = firestore_get_entry(
        uid,
        entry_id
    )

    if not entry:
        return RedirectResponse(
            url="/",
            status_code=303
        )

    # Vault entries must use the dedicated Vault edit route.
    if entry.get("vaulted", False):
        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    firestore_update_entry(
        uid,
        entry_id,
        content
    )

    return RedirectResponse(
        url="/",
        status_code=303
    )


@app.post("/chat/delete-selected")
def delete_selected_conversations(
    request: Request,
    conversation_ids: List[str] = Form(...),
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    for conversation_id in conversation_ids:
        delete_conversation(
            uid,
            conversation_id
        )

    return RedirectResponse(
        url="/chat",
        status_code=303
    )


@app.post("/archive/{entry_id}")
def archive(
    request: Request,
    entry_id: str,
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    entry = firestore_get_entry(uid, entry_id)

    if not entry:
        return RedirectResponse(
            url="/",
            status_code=303
        )

    if entry.get("vaulted", False):
        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    firestore_archive_entry(uid, entry_id)

    return RedirectResponse(
        url="/",
        status_code=303
    )


@app.post("/restore/{entry_id}")
def restore(
    request: Request,
    entry_id: str,
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    entry = firestore_get_entry(uid, entry_id)

    if not entry:
        return RedirectResponse(
            url="/archive",
            status_code=303
        )

    if entry.get("vaulted", False):
        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    firestore_restore_entry(uid, entry_id)

    return RedirectResponse(
        url="/archive",
        status_code=303
    )

@app.get("/archive", response_class=HTMLResponse)
def archive_page(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    uid = user["uid"]

    entries = firestore_get_archived_entries(uid)


    return templates.TemplateResponse(
        request=request,
        name="archive.html",
        context={
            "entries": entries,
            "user": user
        }
    )

@app.post("/reanalyze/{entry_id}")
def reanalyze(
    request: Request,
    entry_id: str,
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    entry = firestore_get_entry(uid, entry_id)

    if entry is None:
        return RedirectResponse(
            url="/",
            status_code=303
        )

    if entry.get("vaulted", False):
        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    result = analyze_journal(
        entry["content"]
    )

    if result.get("analysis"):
        firestore_update_analysis(
            uid,
            entry_id,
            result["analysis"]
        )

    return RedirectResponse(
        url="/",
        status_code=303
    )


@app.post("/move-to-vault/{entry_id}")
def vault_entry(
    request: Request,
    entry_id: str,
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    entry = firestore_get_entry(uid, entry_id)

    if not entry:
        return RedirectResponse(
            url="/",
            status_code=303
        )

    firestore_move_to_vault(uid, entry_id)

    return RedirectResponse(
        url="/",
        status_code=303
    )

@app.get("/vault-reauth", response_class=HTMLResponse)
def vault_reauth_page(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="vault_reauth.html",
        context={"user": user}
    )
@app.post("/vault-reauth")
def vault_reauth(request: Request, data: LoginRequest):
    session_user = request.session.get("user")

    if not session_user:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "You are not signed in."
            }
        )

    try:
        verified_user = verify_firebase_token(data.token)

        # Critical security check:
        # The Google account must be the SAME account
        # as the currently signed-in journal user.
        if verified_user["uid"] != session_user["uid"]:
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "message": "Please authenticate with the same Google account."
                }
            )

        request.session["vault_reset_verified_at"] = time.time()

        return {
            "success": True
        }

    except Exception as e:
        print("Vault reauthentication error:", e)

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "Google re-authentication failed."
            }
        )
@app.get("/vault-reset", response_class=HTMLResponse)
def vault_reset_page(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    verified_at = request.session.get("vault_reset_verified_at")

    # No recent Google reauthentication
    if not verified_at:
        return RedirectResponse(
            url="/vault-reauth",
            status_code=303
        )

    # Reauthentication expires after 5 minutes
    if time.time() - verified_at > 300:
        request.session.pop("vault_reset_verified_at", None)

        return RedirectResponse(
            url="/vault-reauth",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="vault_reset.html",
        context={"error": None}
    )

@app.post("/vault-reset", response_class=HTMLResponse)
def vault_reset(
    request: Request,
    pin: str = Form(...),
    confirm_pin: str = Form(...),
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    verified_at = request.session.get(
        "vault_reset_verified_at"
    )

    if not verified_at:
        return RedirectResponse(
            url="/vault-reauth",
            status_code=303
        )

    if time.time() - verified_at > 300:
        request.session.pop(
            "vault_reset_verified_at",
            None
        )

        return RedirectResponse(
            url="/vault-reauth",
            status_code=303
        )

    if pin != confirm_pin:
        return templates.TemplateResponse(
            request=request,
            name="vault_reset.html",
            context={
                "error": "PINs do not match"
            }
        )

    if len(pin) < 4:
        return templates.TemplateResponse(
            request=request,
            name="vault_reset.html",
            context={
                "error": "PIN must be at least 4 digits"
            }
        )

    if not pin.isdigit():
        return templates.TemplateResponse(
            request=request,
            name="vault_reset.html",
            context={
                "error": "PIN must contain only numbers"
            }
        )

    uid = user["uid"]

    result = hash_pin(pin)

    set_vault_pin(
        uid,
        result["salt"],
        result["hash"]
    )

    # Reset permission can only be used once.
    request.session.pop(
        "vault_reset_verified_at",
        None
    )

    request.session["vault_unlocked"] = True

    return RedirectResponse(
        url="/vault",
        status_code=303
    )


@app.post("/remove-from-vault/{entry_id}")
def unvault_entry(
    request: Request,
    entry_id: str,
    csrf_token: str = Form(...)
):
    user, redirect = require_vault_access(
        request
    )

    if redirect:
        return redirect

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    entry = firestore_get_entry(uid, entry_id)

    if not entry or not entry.get("vaulted", False):
        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    firestore_remove_from_vault(
        uid,
        entry_id
    )

    return RedirectResponse(
        url="/vault",
        status_code=303
    )

@app.get("/vault", response_class=HTMLResponse)
def vault_page(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    uid = user["uid"]

    stored_pin = get_vault_pin(uid)

    # No PIN created yet
    if stored_pin is None:
        return templates.TemplateResponse(
            request=request,
            name="vault_setup.html",
            context={"error": None}
        )

    # PIN exists but vault not unlocked in this session
    if not request.session.get("vault_unlocked", False):
        return templates.TemplateResponse(
            request=request,
            name="vault_login.html",
            context={"error": None}
        )

    entries = firestore_get_vault_entries(uid)

    return templates.TemplateResponse(
        request=request,
        name="vault.html",
        context={
            "entries": entries,
            "user": user
        }
    )

@app.post("/vault-setup", response_class=HTMLResponse)
def setup_vault_pin(
    request: Request,
    pin: str = Form(...),
    confirm_pin: str = Form(...),
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    # Never allow the setup endpoint to overwrite an existing PIN.
    # Existing PINs must be changed through the reauthentication/reset flow.
    if get_vault_pin(uid) is not None:
        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    if pin != confirm_pin:
        return templates.TemplateResponse(
            request=request,
            name="vault_setup.html",
            context={
                "error": "PINs do not match"
            }
        )

    if len(pin) < 4:
        return templates.TemplateResponse(
            request=request,
            name="vault_setup.html",
            context={
                "error": "PIN must be at least 4 digits"
            }
        )

    if not pin.isdigit():
        return templates.TemplateResponse(
            request=request,
            name="vault_setup.html",
            context={
                "error": "PIN must contain only numbers"
            }
        )

    result = hash_pin(pin)

    set_vault_pin(
        uid,
        result["salt"],
        result["hash"]
    )

    request.session["vault_unlocked"] = True

    return RedirectResponse(
        url="/vault",
        status_code=303
    )


@app.post("/vault-unlock", response_class=HTMLResponse)
def unlock_vault(
    request: Request,
    pin: str = Form(...),
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    stored_pin = get_vault_pin(uid)

    if stored_pin is None:
        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    if verify_pin(
        pin,
        stored_pin["salt"],
        stored_pin["hash"]
    ):
        request.session["vault_unlocked"] = True

        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="vault_login.html",
        context={
            "error": "Incorrect PIN"
        }
    )


@app.post("/vault-lock")
def lock_vault(
    request: Request,
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    request.session.pop(
        "vault_unlocked",
        None
    )

    return RedirectResponse(
        url="/",
        status_code=303
    )


@app.post("/vault-edit/{entry_id}")
def edit_vault_entry(
    request: Request,
    entry_id: str,
    content: str = Form(...),
    csrf_token: str = Form(...)
):
    user, redirect = require_vault_access(
        request
    )

    if redirect:
        return redirect

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    entry = firestore_get_entry(
        uid,
        entry_id
    )

    if not entry:
        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    if not entry.get("vaulted", False):
        return RedirectResponse(
            url="/",
            status_code=303
        )

    firestore_update_entry(
        uid,
        entry_id,
        content
    )

    return RedirectResponse(
        url="/vault",
        status_code=303
    )


@app.post("/vault-reanalyze/{entry_id}")
def reanalyze_vault_entry(
    request: Request,
    entry_id: str,
    csrf_token: str = Form(...)
):
    user, redirect = require_vault_access(
        request
    )

    if redirect:
        return redirect

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    entry = firestore_get_entry(
        uid,
        entry_id
    )

    if not entry:
        return RedirectResponse(
            url="/vault",
            status_code=303
        )

    if not entry.get("vaulted", False):
        return RedirectResponse(
            url="/",
            status_code=303
        )

    result = analyze_journal(
        entry["content"]
    )

    if result.get("analysis"):
        firestore_update_analysis(
            uid,
            entry_id,
            result["analysis"]
        )

    return RedirectResponse(
        url="/vault",
        status_code=303
    )

@app.get("/chat", response_class=HTMLResponse)
def chat_home(request: Request):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    uid = user["uid"]

    conversations = get_conversations(uid)

    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "conversations": conversations,
            "messages": [],
            "conversation_id": None
        }
    )

@app.post("/chat/{conversation_id}/summarize")
def summarize_chat(
    request: Request,
    conversation_id: str,
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    messages = get_messages(
        uid,
        conversation_id
    )

    if not messages:
        return RedirectResponse(
            url=f"/chat/{conversation_id}",
            status_code=303
        )

    summary = summarize_conversation(messages)

    update_conversation_summary(
        uid,
        conversation_id,
        summary
    )

    return RedirectResponse(
        url=f"/chat/{conversation_id}",
        status_code=303
    )


@app.post("/chat/new")
def new_chat(
    request: Request,
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    conversation_id = create_conversation(
        uid,
        "New Journal Conversation"
    )

    return RedirectResponse(
        url=f"/chat/{conversation_id}",
        status_code=303
    )

@app.get("/chat/{conversation_id}", response_class=HTMLResponse)
def open_chat(
    request: Request,
    conversation_id: str
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    uid = user["uid"]

    messages = get_messages(
        uid,
        conversation_id
    )

    conversations = get_conversations(uid)

    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "conversations": conversations,
            "messages": messages,
            "conversation_id": conversation_id
        }
    )



@app.post("/chat/{conversation_id}/send")
def send_chat_message(
    request: Request,
    conversation_id: str,
    message: str = Form(...),
    csrf_token: str = Form(...)
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if not verify_csrf_token(request, csrf_token):
        return csrf_error_response()

    uid = user["uid"]

    add_message(
        uid,
        conversation_id,
        "user",
        message
    )

    messages_before_reply = get_messages(
        uid,
        conversation_id
    )

    user_messages = [
        m
        for m in messages_before_reply
        if m["role"] == "user"
    ]

    if len(user_messages) == 1:
        title = message.strip()

        if len(title) > 35:
            title = title[:35] + "..."

        update_conversation_title(
            uid,
            conversation_id,
            title
        )

    messages = get_messages(
        uid,
        conversation_id
    )

    reply = generate_chat_reply(messages)

    add_message(
        uid,
        conversation_id,
        "assistant",
        reply
    )

    return RedirectResponse(
        url=f"/chat/{conversation_id}",
        status_code=303
    )

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    ) 