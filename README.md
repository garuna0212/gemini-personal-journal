# Gemini Personal Journal

A privacy-focused AI journaling application built with **FastAPI, Google Gemini, Firebase Authentication, Cloud Firestore, Google Cloud Secret Manager, and Google Cloud Run**.

Gemini Personal Journal lets users write private journal entries, receive AI-generated reflections, continue thoughts through multi-turn chat, and protect sensitive entries in a PIN-protected Vault.

The project was built with a security-first approach: authenticated sessions, per-user data isolation, server-side Firebase token verification, CSRF protection for form actions, Secret Manager for production secrets, and sensitive-data masking before content is sent to Gemini.

---

## Live Demo

**Application:**  
https://gemini-personal-journal-767164856928.asia-south1.run.app

**GitHub:**  
https://github.com/garuna0212/gemini-personal-journal

---

## What the App Does

### Journal + Gemini Reflection

Users can write journal entries and optionally analyze them with Gemini.

Gemini returns a structured reflection containing:

- Mood
- Summary
- Reflection
- Follow-up questions

Entries and their AI-generated analysis are stored in Cloud Firestore under the authenticated user's UID.

### AI Guardian

Before journal content is sent to Gemini, the **AI Guardian** checks for supported sensitive information and masks it.

Examples include:

- Email addresses
- Indian phone numbers
- Aadhaar-like sensitive IDs
- URLs

Example:

```text
Original:
My email is example@gmail.com

Sent to Gemini:
My email is [EMAIL]
```

The original entry remains associated with the authenticated user, while Gemini receives the protected version.

### Multi-Turn Journal Chat

The application includes persistent Gemini chat for reflection and brainstorming.

Features include:

- Multi-turn Gemini conversations
- Previous messages used as context
- Persistent Firestore-backed history
- Automatic conversation titles
- Conversation summaries
- Select-and-delete conversations

When the user ends a conversation, Gemini generates a structured summary containing:

- Summary
- Key themes
- Important takeaways
- Possible next steps

The summary is saved with the conversation in Firestore.

### Private Vault

Users can move sensitive journal entries into a separate **Private Vault**.

Vault features include:

- Per-user PIN
- PBKDF2-based PIN hashing
- Random salt generation
- Session-specific unlock state
- Manual Vault locking
- Edit and re-analyze Vault entries
- Remove entries from the Vault
- Protected backend Vault actions
- Secure PIN reset flow

The Vault PIN is never stored in plaintext.

> **Important:** The Vault is an application-level PIN-protected privacy layer. It does not provide separate client-side encryption of journal content.

### Secure Vault PIN Recovery

A forgotten Vault PIN cannot be reset directly.

The reset flow requires:

1. An authenticated journal session
2. Fresh Google re-authentication
3. Backend verification of the Firebase ID token
4. Verification that the re-authenticated Firebase UID matches the active journal session
5. Temporary reset authorization
6. Creation of a new Vault PIN

The reset authorization expires after a short period and is invalidated after use.

### Archive

Journal entries can be archived and later restored without deleting them.

---

## Security Features

The project includes:

- Firebase Authentication with Google Sign-In
- Server-side Firebase ID token verification
- Backend-derived user identity
- Per-user Firestore paths
- Firestore Security Rules
- Cloud Secret Manager integration
- HTTPS-only production session cookies
- Signed application sessions
- CSRF protection for form-based state-changing actions
- AI Guardian sensitive-data masking
- PBKDF2 Vault PIN hashing
- Vault backend authorization checks
- Fresh Google re-authentication for Vault PIN recovery
- Graceful Gemini API error handling
- Sanitized Markdown rendering for Gemini output
- Minimal exposure of sensitive error details to users

---

## Authentication

The application uses **Firebase Authentication with Google Sign-In**.

```text
Browser
   |
   | Google Sign-In
   v
Firebase Authentication
   |
   | Firebase ID token
   v
FastAPI backend
   |
   | Verify token with Firebase Admin SDK
   v
Signed application session
```

The backend derives the user's UID from the verified Firebase session rather than trusting a UID supplied by the browser.

---

## Per-User Data Isolation

Firestore data is organized under each Firebase UID.

```text
users/
  {uid}/
    entries/
      {entryId}

    conversations/
      {conversationId}/
        messages/
          {messageId}
```

This keeps journal entries, archived entries, Vault entries, conversations, messages, and summaries scoped to the authenticated user.

The application was manually tested with separate Google accounts to verify cross-user isolation.

---

## Firestore Security Rules

```rules
rules_version = '2';

service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId}/{document=**} {
      allow read, write:
        if request.auth != null
        && request.auth.uid == userId;
    }
  }
}
```

The backend also performs UID-based authorization because Firebase Admin SDK operations are trusted server operations and are not governed by client Firestore Security Rules.

---

## Secret Management

Production secrets are stored in **Google Cloud Secret Manager**.

```text
GEMINI_API_KEY
SESSION_SECRET
```

The Cloud Run runtime service account is granted only the permissions needed to access the required secrets and Firestore data.

Production secrets are not hardcoded in the repository.

For local development, the application can use local environment variables or Secret Manager depending on configuration.

The `.env` file is excluded from Git and Docker builds.

---

## CSRF Protection

State-changing HTML form actions use per-session CSRF tokens.

Protected actions include:

- Save
- Analyze
- Edit
- Delete
- Archive / Restore
- Move to / Remove from Vault
- Vault setup / unlock / reset / lock
- Vault edit / re-analyze
- Chat creation
- Chat sending
- Conversation summarization
- Conversation deletion
- Logout

Firebase JSON authentication flows use verified Firebase ID tokens instead of normal HTML form submission.

---

## Safe Gemini Output Rendering

Gemini responses are stored as Markdown text.

Before rendering in the UI, Markdown is:

1. Converted to HTML
2. Sanitized using `bleach`
3. Rendered only with an allowlist of safe HTML tags

This avoids directly trusting model-generated HTML.

---

## Architecture

```text
User Browser
    |
    v
Firebase Authentication
    |
    v
FastAPI Backend on Cloud Run
    |
    +----> AI Guardian ----> Gemini API
    |
    +----> Cloud Firestore
    |
    +----> Google Cloud Secret Manager
```

---

## Technology Stack

### Backend
- Python
- FastAPI
- Uvicorn
- Jinja2

### AI
- Google Gemini API
- Google Gen AI Python SDK

### Authentication
- Firebase Authentication
- Google Sign-In
- Firebase Admin SDK

### Database
- Cloud Firestore

### Security
- Google Cloud Secret Manager
- Firebase ID token verification
- Signed sessions
- CSRF tokens
- PBKDF2 Vault PIN hashing
- Sanitized Markdown rendering

### Deployment
- Docker
- Google Cloud Run
- Cloud Build
- Artifact Registry

---

## Project Structure

```text
gemini-personal-journal/
│
├── app.py
├── firebase_auth.py
├── firestore_db.py
├── gemini_ai.py
├── guardian.py
├── conversation_ai.py
├── conversation_db.py
├── vault_security.py
├── secret_manager.py
│
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .gitignore
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── archive.html
│   ├── vault.html
│   ├── vault_login.html
│   ├── vault_setup.html
│   ├── vault_reset.html
│   ├── vault_reauth.html
│   └── chat.html
│
└── static/
    └── style.css
```

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/garuna0212/gemini-personal-journal.git
cd gemini-personal-journal
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure the project

Create a local `.env` file for non-production configuration as needed.

```env
GOOGLE_CLOUD_PROJECT=your_google_cloud_project_id
ENVIRONMENT=development
```

If you choose to use local secrets during development:

```env
GEMINI_API_KEY=your_gemini_api_key
SESSION_SECRET=your_long_random_session_secret
```

Do not commit `.env`.

### 4. Authenticate Google Application Default Credentials

```bash
gcloud auth application-default login
```

Optionally set the quota project:

```bash
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

### 5. Run the application

```bash
python app.py
```

Open:

```text
http://127.0.0.1:8000
```

---

## Docker

```bash
docker build -t gemini-personal-journal .
docker run -p 8080:8080 gemini-personal-journal
```

---

## Cloud Run Deployment

```bash
gcloud run deploy gemini-personal-journal \
  --source . \
  --project YOUR_PROJECT_ID \
  --region asia-south1 \
  --service-account YOUR_SERVICE_ACCOUNT \
  --set-env-vars ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID \
  --allow-unauthenticated
```

The Cloud Run service is publicly reachable so users can reach the login page, but application data remains protected behind Firebase authentication and backend authorization.

Production secrets are retrieved from Google Cloud Secret Manager.

---

## Original Enhancements

### AI Guardian
Masks supported sensitive information before journal content is sent to Gemini.

### Private Vault
Provides a separate PIN-protected area for sensitive entries, with hashed PINs, session locking, backend access checks, and Google re-authentication for PIN recovery.

### Conversation Summaries
Multi-turn Gemini conversations can be ended and automatically summarized into structured insights saved in Firestore.

### Security Hardening
Additional improvements include:

- CSRF protection
- Backend Vault authorization
- Safe Markdown sanitization
- Secure session configuration
- Gemini failure handling

---

## Security Testing

The application has been manually tested for:

- Authentication enforcement
- Cross-user journal isolation
- Cross-user conversation isolation
- Journal persistence
- Archive / restore flow
- Vault PIN creation
- Incorrect Vault PIN rejection
- Vault session locking
- Vault backend action protection
- Vault PIN reset through Google re-authentication
- Firestore persistence
- Secret Manager access
- Production Firebase Google Sign-In
- Multi-turn Gemini context
- Persistent Gemini conversation summaries
- CSRF-protected form actions
- Cloud Run production deployment

---

## Demo / Submission

This project was built as part of a Google Cloud / Gemini challenge submission.

Required social hashtag:

```text
#AccelerateAIwithCloudRun
```

Live application:

https://gemini-personal-journal-767164856928.asia-south1.run.app

---

## Screenshots

Recommended screenshots:

1. Google Sign-In
2. Journal dashboard
3. Gemini journal analysis
4. AI Guardian masking
5. Private Vault
6. Journal Chat
7. Conversation summary
8. Firebase Authentication
9. Firestore UID-based data structure
10. Firestore Security Rules
11. Secret Manager secret names
12. Cloud Run deployment

> Never publish API keys, session secrets, Firebase tokens, or Secret Manager secret values in screenshots.

---

## Limitations

This is a challenge prototype rather than a production-ready mental-health or secure-notes platform.

Current limitations include:

- The Vault is PIN-protected but does not provide client-side content encryption
- No dedicated rate-limiting layer
- No comprehensive automated security test suite
- No formal penetration test
- No abuse-detection system
- No formal privacy/legal compliance review

---

## Disclaimer

Gemini Personal Journal is an educational and challenge demonstration project.

AI-generated reflections should not be treated as medical, psychological, legal, or other professional advice.

The application should undergo additional security testing, monitoring, abuse protection, privacy review, and operational hardening before being used for highly sensitive real-world data.
