"""
SENTINEL2 — Google OAuth Helper
Run this script to create or refresh auth/token.json.

Usage:
    python -m src.utils.google_auth

Requires auth/credentials.json (OAuth client ID from Google Cloud Console).
Grants scopes: gmail.send, drive.file
"""

import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file",
]

AUTH_DIR = Path(__file__).resolve().parent.parent.parent / "auth"
CREDS_FILE = AUTH_DIR / "credentials.json"
TOKEN_FILE = AUTH_DIR / "token.json"


def authenticate():
    """Run OAuth flow and save token.json."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        print("Refreshing expired token...")
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not CREDS_FILE.exists():
            print(f"ERROR: {CREDS_FILE} not found.")
            print("Download OAuth client credentials from Google Cloud Console.")
            return
        print("Opening browser for Google sign-in...")
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    print(f"Token saved to {TOKEN_FILE}")
    print(f"Scopes: {creds.scopes}")
    print(f"Expiry: {creds.expiry}")


if __name__ == "__main__":
    authenticate()
