# Gemini Personal Journal

A secure AI-powered personal journaling application built with **FastAPI, Gemini, Firebase Authentication, Cloud Firestore, Google Cloud Secret Manager, and Cloud Run**.

The project was designed around privacy, per-user isolation, secure secret handling, and responsible AI usage.

## Live Application

Deployed on Google Cloud Run:

https://gemini-personal-journal-767164856928.asia-south1.run.app

## Features

### AI Journal Analysis

Users can write journal entries and analyze them with Gemini.

The AI provides:

- Mood
- Summary
- Reflection
- Follow-up questions

Journal entries and AI analysis are stored persistently in Cloud Firestore.

### AI Guardian

Before journal content is sent to Gemini, the AI Guardian checks for sensitive information and masks supported data types.

Examples include:

- Email addresses
- Indian phone numbers
- Aadhaar-like sensitive IDs
- URLs

Example:

Original:
My email is example@gmail.com

Sent to Gemini:
My email is [EMAIL]

The original journal entry remains stored for the authenticated user while Gemini receives the protected version.

### Journal Chat

The application includes a multi-turn Gemini chat experience for journaling and brainstorming.

Features include:

- Persistent conversations
- Previous messages used as context
- Automatic conversation titles
- Conversation summaries
- Select-and-delete conversations
- Firestore-backed conversation history

When a user ends a conversation, Gemini automatically generates a structured summary containing:

- Summary
- Key themes
- Important takeaways
- Possible next steps

The generated summary is saved in Firestore.

### Private Vault

Sensitive journal entries can be moved into a private Vault.

Vault features include:

- Per-user Vault PIN
- PBKDF2-based PIN hashing
- Random salt generation
- Session-specific Vault unlocking
- Manual Vault locking
- Edit and re-analyze Vault entries
- Remove entries from Vault
- Delete Vault entries

The Vault PIN itself is never stored in plaintext.

### Secure Vault PIN Recovery

If a user forgets the Vault PIN, they cannot simply reset it directly.

The recovery flow requires:

1. An authenticated journal session
2. Fresh Google re-authentication
3. Backend verification of the Firebase ID token
4. Matching Firebase UID
5. Temporary reset authorization
6. Creation of a new Vault PIN

The reset authorization expires after a short period and is removed after use.

### Archive

Journal entries can be archived and restored without deleting them.

## Authentication

The application uses **Firebase Authentication with Google Sign-In**.

The frontend obtains a Firebase ID token, which is verified by the FastAPI backend using the Firebase Admin SDK.

The backend derives the authenticated user's UID from the verified session instead of trusting a UID supplied by the browser.

## Per-User Data Isolation

Firestore data is organized by Firebase UID.

Example structure:

users/
  {uid}/
    entries/
      {entryId}

    conversations/
      {conversationId}/
        messages/
          {messageId}

This ensures each user's journal entries, Vault data, archives, conversations, and summaries remain isolated.

The application was manually tested using two separate Google accounts to verify that one user cannot view another user's journal data.

## Firestore Security Rules

Firestore rules restrict access to the authenticated user's own document hierarchy.

Example:

rules_version = '2';

service cloud.firestore {
  match /databases/{database}/documents {

    match /users/{userId}/{document=**} {

      allow read, write: if request.auth != null
                         && request.auth.uid == userId;
    }
  }
}

The backend additionally performs UID-based authorization because Firebase Admin SDK operations bypass Firestore Security Rules.

## Secret Management

Sensitive production secrets are stored in **Google Cloud Secret Manager**.

Secrets include:

GEMINI_API_KEY
SESSION_SECRET

The Cloud Run runtime service account has only the permissions required to access the necessary secrets and Firestore data.

Local development uses environment variables from `.env`.

The `.env` file is excluded from Git and Docker builds.

## Session Security

Application sessions use a high-entropy secret.

Local development:

ENVIRONMENT=development

Production:

ENVIRONMENT=production

In production, session cookies are configured for HTTPS.

Vault unlock state is stored per session instead of using a global server variable.

## Security Principles

The project follows a security-first development approach.

Key principles include:

- Threat modeling before implementation
- No hardcoded production secrets
- Firebase Authentication
- Server-side token verification
- Per-user Firestore isolation
- Least-privilege IAM
- Sensitive-data minimization before AI processing
- Hashed Vault PINs
- Secure session management
- Safe error handling
- Minimal sensitive logging
- HTTPS deployment
- Secret Manager integration
- Authentication before sensitive account actions

## Architecture

User Browser
    |
    v
Firebase Google Authentication
    |
    v
FastAPI Backend
    |
    +------> AI Guardian
    |            |
    |            v
    |        Gemini API
    |
    +------> Cloud Firestore
    |
    +------> Secret Manager
    |
    v
Google Cloud Run

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
- PBKDF2 PIN hashing
- Firebase ID token verification
- Signed application sessions

### Deployment

- Docker
- Google Cloud Run
- Cloud Build
- Artifact Registry

## Project Structure

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

## Local Setup

Clone the repository:

git clone https://github.com/garuna0212/gemini-personal-journal.git
cd gemini-personal-journal

Install dependencies:

python -m pip install -r requirements.txt

Create a local `.env` file:

GEMINI_API_KEY=your_gemini_api_key
SESSION_SECRET=your_long_random_session_secret
GOOGLE_CLOUD_PROJECT=your_google_cloud_project_id
ENVIRONMENT=development

Do not commit `.env`.

Authenticate local Google Application Default Credentials if using Firebase Admin and Firestore locally:

gcloud auth application-default login

Set the quota project:

gcloud auth application-default set-quota-project YOUR_PROJECT_ID

Run the application:

python app.py

Then open:

http://127.0.0.1:8000

## Docker

Build the container:

docker build -t gemini-personal-journal .

Run locally:

docker run -p 8080:8080 gemini-personal-journal

## Cloud Run Deployment

Example deployment:

gcloud run deploy gemini-personal-journal \
  --source . \
  --region asia-south1 \
  --service-account YOUR_SERVICE_ACCOUNT \
  --set-env-vars ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID \
  --allow-unauthenticated

Production secrets are retrieved from Google Cloud Secret Manager.

## Original Enhancements

### AI Guardian

Protects supported sensitive information before journal content is sent to Gemini.

### Secure Vault

Provides PIN-protected storage for private journal entries with hashed PINs and Google re-authentication for recovery.

### Conversation Summaries

Multi-turn Gemini conversations can be ended and automatically summarized into structured insights saved in Firestore.

## Security Testing

The application was tested for:

- Authentication enforcement
- Cross-user journal isolation
- Cross-user conversation isolation
- Vault session locking
- Incorrect PIN rejection
- Vault PIN reset through Google re-authentication
- Firestore persistence
- Secret Manager access from Cloud Run
- Production Firebase Google Sign-In
- Multi-turn Gemini context
- Persistent Gemini conversation summaries

## Screenshots

Screenshots can be added here for:

- Journal dashboard
- Gemini analysis
- AI Guardian
- Journal Chat
- Conversation summary
- Vault
- Google re-authentication
- Firebase Authentication
- Firestore data model
- Firestore Security Rules
- Secret Manager
- Cloud Run deployment

## Disclaimer

This project is a prototype built for learning and challenge demonstration purposes.

It should undergo additional penetration testing, monitoring, rate limiting, abuse protection, security review, and privacy/legal review before handling sensitive production data at scale.