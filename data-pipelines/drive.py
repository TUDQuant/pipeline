"""Google Drive client for the nightly pipeline.

Two things that will otherwise cost an evening:

1. A service account has no Drive storage quota of its own. It can only write
   into a SHARED DRIVE, never into "My Drive". Create the Shared Drive first,
   then share it with the service account email as Content manager.
2. Every Drive API call against a Shared Drive needs supportsAllDrives=True,
   and every list call additionally needs includeItemsFromAllDrives=True.
   Omit either and you get a confusing empty result rather than an error.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _credentials():
    from google.oauth2 import service_account

    raw = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise RuntimeError("GDRIVE_SERVICE_ACCOUNT_JSON secret is not set")

    # Accept either raw JSON or base64, because pasting raw JSON into a GitHub
    # secret works but is easy to mangle.
    try:
        info = json.loads(raw)
    except json.JSONDecodeError:
        info = json.loads(base64.b64decode(raw))

    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def client():
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=_credentials(), cache_discovery=False)


def ensure_folder(service, name: str, parent_id: str) -> str:
    """Return the id of `name` under `parent_id`, creating it if needed."""
    query = (
        f"name = '{name}' and '{parent_id}' in parents "
        "and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    found = (
        service.files()
        .list(q=query, fields="files(id)", supportsAllDrives=True,
              includeItemsFromAllDrives=True)
        .execute()
        .get("files", [])
    )
    if found:
        return found[0]["id"]

    created = (
        service.files()
        .create(
            body={
                "name": name,
                "parents": [parent_id],
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )
    return created["id"]


def upload(service, local_path: Path, folder_id: str, mime: str = "application/octet-stream") -> str:
    """Create or replace a file by name. Replacing keeps the id stable, so any
    link a member has saved keeps working."""
    from googleapiclient.http import MediaFileUpload

    name = local_path.name
    query = f"name = '{name}' and '{folder_id}' in parents and trashed = false"
    existing = (
        service.files()
        .list(q=query, fields="files(id)", supportsAllDrives=True,
              includeItemsFromAllDrives=True)
        .execute()
        .get("files", [])
    )

    media = MediaFileUpload(str(local_path), mimetype=mime, resumable=False)

    if existing:
        file_id = existing[0]["id"]
        service.files().update(fileId=file_id, media_body=media,
                               supportsAllDrives=True).execute()
        return file_id

    created = (
        service.files()
        .create(body={"name": name, "parents": [folder_id]}, media_body=media,
                fields="id", supportsAllDrives=True)
        .execute()
    )
    return created["id"]
