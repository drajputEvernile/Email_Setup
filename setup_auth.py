"""Generate Gmail API credentials + token (read and write access) for an email id.

Usage:
    python setup_auth.py                      # prompts for the email id
    python setup_auth.py you@gmail.com        # email id as argument

Takes the Google OAuth client secret JSON (client_secret*.json / credentials.json)
found in the project root, runs the Google sign-in for the given email id, and saves:

    Creds/credentials.json   - the OAuth client secret (copied from the root)
    Creds/token.json         - the authorized user token (access + refresh token)

The token carries these scopes:
    gmail.modify  - read inbox/messages, track them, mark read/unread, labels, trash
    gmail.send    - send emails
"""
import shutil
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]
BASE_DIR = Path(__file__).resolve().parent
CREDS_DIR = BASE_DIR / "Creds"
CREDENTIALS_PATH = CREDS_DIR / "credentials.json"
TOKEN_PATH = CREDS_DIR / "token.json"


def find_client_secret():
  """Locate the client secret JSON in the project root."""
  candidates = [BASE_DIR / "credentials.json"]
  candidates += sorted(BASE_DIR.glob("client_secret*.json"))
  for path in candidates:
    if path.is_file():
      return path
  sys.exit("No credentials.json / client_secret*.json found in the project root.")


def token_is_usable():
  if not TOKEN_PATH.exists():
    return None
  try:
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
  except (ValueError, KeyError):
    return None
  if creds.valid:
    return creds
  if creds.expired and creds.refresh_token:
    try:
      creds.refresh(Request())
      TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
      return creds
    except Exception:  # revoked/expired refresh token -> re-authorize
      return None
  return None


def main():
  email = sys.argv[1] if len(sys.argv) > 1 else input("Gmail address to authorize: ").strip()
  if not email or "@" not in email:
    sys.exit("A valid email id is required.")

  CREDS_DIR.mkdir(exist_ok=True)
  shutil.copyfile(find_client_secret(), CREDENTIALS_PATH)

  creds = token_is_usable()
  if creds:
    print("Existing token in Creds/ is still valid.")
  else:
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(
        port=0,
        login_hint=email,
        access_type="offline",
        prompt="consent",  # forces a refresh_token to be issued
    )
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

  # Verify which account was actually authorized.
  profile = build("gmail", "v1", credentials=creds).users().getProfile(userId="me").execute()
  authorized = profile["emailAddress"]
  print(f"Authorized account : {authorized}")
  print(f"Messages in mailbox: {profile.get('messagesTotal')}")
  if authorized.lower() != email.lower():
    print(f"WARNING: you signed in as {authorized}, not {email}.")
  print(f"Saved: {CREDENTIALS_PATH}")
  print(f"Saved: {TOKEN_PATH}")


if __name__ == "__main__":
  main()
