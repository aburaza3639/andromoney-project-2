"""
Google Drive authentication and CSV download for AndroMoney pipeline.
"""
import io
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseDownload
import AndroMoney.settings as settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def authenticate() -> Credentials:
    """Return valid OAuth credentials, running browser flow on first use.

    Loads token from settings.TOKEN_PATH if present. On expiry, refreshes
    automatically. On first run (no token), opens a browser for consent and
    saves the new token to settings.TOKEN_PATH.
    """
    creds = None
    if os.path.exists(settings.TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(settings.TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(settings.TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
        os.chmod(settings.TOKEN_PATH, 0o600)
    return creds


def search_file(service, filename: str) -> str:
    """Return the Drive file ID of the first file matching filename.

    Args:
        service:  Authenticated Drive API service client.
        filename: Exact filename to search for (e.g. 'AndroMoney.csv').

    Raises:
        FileNotFoundError: If no file with that name exists in Drive.
    """
    results = service.files().list(
        q=f"name='{filename}' and trashed=false",
        fields="files(id, name)",
    ).execute()
    files = results.get("files", [])
    if not files:
        raise FileNotFoundError(f"No file named '{filename}' found in Google Drive")
    return files[0]["id"]


def download_csv(service, file_id: str) -> io.StringIO:
    """Download a Drive file and return its content as a StringIO.

    Args:
        service:  Authenticated Drive API service client.
        file_id:  Drive file ID to download.

    Returns:
        io.StringIO with the file content decoded as UTF-8.
    """
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    return io.StringIO(buffer.read().decode("utf-8-sig"))
