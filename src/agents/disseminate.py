"""
SENTINEL2 — Report Dissemination
Handles delivery of reports via Google Drive upload and email dispatch.
Uses Gmail API (OAuth) for email — no SMTP or App Passwords needed.
"""

import base64
import json
import logging
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Optional

from src.db.connection import execute_query, get_cursor
from src.utils.config import get_config, get_project_root

logger = logging.getLogger("sentinel2.disseminate")


def disseminate_report(
    run_date: str,
    pdf_path: str,
    report_type: str = "daily",
) -> dict:
    """
    Disseminate a report via Google Drive and email.

    Steps:
      1. Upload PDF to Google Drive
      2. Send email with Drive link (or without) to recipients
      3. Log delivery

    Returns delivery status dict.
    """
    logger.info(f"Disseminating {report_type} report for {run_date}")

    result = {
        "run_date": run_date,
        "report_type": report_type,
        "pdf_path": pdf_path,
    }

    # Step 1: Upload to Google Drive
    drive_result = _upload_to_drive(pdf_path, report_type, run_date)
    result.update(drive_result)

    # Step 2: Send email (with or without Drive link)
    email_result = _send_email(
        run_date, report_type,
        drive_result.get("drive_view_link", ""),
        pdf_path,
    )
    result.update(email_result)

    # Step 3: Log delivery
    _log_delivery(result)

    logger.info(f"Dissemination complete: {result.get('drive_upload_status', 'N/A')}")
    return result


def disseminate_black_swan_alert(
    run_date: str,
    pdf_path: str,
    event_name: str = "",
) -> dict:
    """Disseminate a Black Swan alert with IMMEDIATE precedence."""
    logger.info(f"DISSEMINATING BLACK SWAN ALERT: {event_name}")
    result = disseminate_report(run_date, pdf_path, report_type="black_swan_alert")
    result["event_name"] = event_name
    return result


# ── Google OAuth Credentials ─────────────────────────────────────────

_cached_creds = None


def _get_google_creds():
    """
    Load OAuth credentials from auth/token.json + auth/credentials.json.
    Auto-refreshes expired tokens using the refresh_token.
    """
    global _cached_creds
    if _cached_creds and _cached_creds.valid:
        return _cached_creds

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    auth_dir = get_project_root() / "auth"
    token_path = auth_dir / "token.json"
    creds_path = auth_dir / "credentials.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(
            str(token_path),
            scopes=[
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/drive.file",
            ],
        )

    if creds and creds.expired and creds.refresh_token:
        logger.info("Refreshing expired Google OAuth token")
        creds.refresh(Request())
        # Persist refreshed token
        token_path.write_text(creds.to_json())
        logger.info("Token refreshed and saved")

    if not creds or not creds.valid:
        raise RuntimeError(
            "Google OAuth token missing or invalid. "
            "Run: python -m src.utils.google_auth to re-authenticate."
        )

    _cached_creds = creds
    return creds


# ── Google Drive Upload ───────────────────────────────────────────────

def _upload_to_drive(pdf_path: str, report_type: str, run_date: str) -> dict:
    """Upload PDF to Google Drive using OAuth credentials."""
    config = get_config()
    drive_cfg = config.get("delivery", {}).get("google_drive", {})

    # Look up the folder ID env var for this report type
    folder_env_key = drive_cfg.get(
        f"{report_type}_folder_id_env",
        drive_cfg.get("daily_folder_id_env", "SENTINEL_DRIVE_DAILY_FOLDER_ID"),
    )
    folder_id = os.environ.get(folder_env_key, "")
    if not folder_id:
        logger.info(f"No Drive folder ID for {report_type} (env: {folder_env_key})")
        return {"drive_upload_status": "no_folder_id"}

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = _get_google_creds()
        service = build("drive", "v3", credentials=creds)

        file_name = Path(pdf_path).name
        file_metadata = {
            "name": file_name,
            "parents": [folder_id],
        }
        media = MediaFileUpload(pdf_path, mimetype="application/pdf")

        uploaded = service.files().create(
            body=file_metadata, media_body=media, fields="id,webViewLink"
        ).execute()

        logger.info(f"Uploaded to Drive: {uploaded.get('webViewLink')}")
        return {
            "drive_file_id": uploaded.get("id", ""),
            "drive_view_link": uploaded.get("webViewLink", ""),
            "drive_upload_status": "ok",
            "drive_upload_timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Drive upload failed: {e}")
        return {"drive_upload_status": f"failed: {e}"}


# ── Email Dispatch (Gmail API) ───────────────────────────────────────

def _send_email(
    run_date: str,
    report_type: str,
    drive_link: str,
    pdf_path: str,
) -> dict:
    """
    Send report email via Gmail API (OAuth).
    No SMTP, no App Passwords — uses auth/token.json credentials.
    """
    config = get_config()
    gmail_cfg = config.get("delivery", {}).get("gmail", {})
    sender = gmail_cfg.get("sender_email", "")
    if not sender:
        logger.warning("No sender_email in delivery.gmail config")
        return {"email_send_status": "no_sender_configured"}

    # Fetch active recipients
    recipients = execute_query(
        """SELECT email, name FROM email_recipients
           WHERE status = 'active'
           AND (report_types LIKE %s OR report_types LIKE '%%all%%')""",
        (f"%{report_type}%",),
    )

    if not recipients:
        logger.warning("No active email recipients found")
        return {"email_send_status": "no_recipients"}

    to_list = [r["email"] for r in recipients]

    subject_map = {
        "daily": f"SENTINEL2 Daily Intelligence Brief — {run_date}",
        "black_swan_alert": f"SENTINEL2 BLACK SWAN ALERT — {run_date} — IMMEDIATE",
        "weekly": f"SENTINEL2 Weekly Summary — {run_date}",
        "monthly": f"SENTINEL2 Monthly Summary — {run_date}",
    }
    subject = subject_map.get(report_type, f"SENTINEL2 Report — {run_date}")

    body_lines = [
        f"SENTINEL2 {report_type.replace('_', ' ').title()} Report",
        f"Date: {run_date}",
        "",
    ]
    if drive_link:
        body_lines.append(f"View report: {drive_link}")
        body_lines.append("")
    body_lines.extend([
        "Classification: UNCLASSIFIED // AI GENERATED",
        "Objective. Non-Partisan. Actionable.",
    ])
    body = "\n".join(body_lines)

    try:
        from googleapiclient.discovery import build

        creds = _get_google_creds()
        service = build("gmail", "v1", credentials=creds)

        # Build MIME message
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(to_list)
        msg.attach(MIMEText(body, "plain"))

        # Attach PDF if it exists
        if pdf_path and Path(pdf_path).exists():
            with open(pdf_path, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header(
                    "Content-Disposition", "attachment",
                    filename=Path(pdf_path).name,
                )
                msg.attach(attachment)

        # Encode and send via Gmail API
        raw_message = base64.urlsafe_b64encode(
            msg.as_bytes()
        ).decode("ascii")

        sent = service.users().messages().send(
            userId="me",
            body={"raw": raw_message},
        ).execute()

        message_id = sent.get("id", "")
        logger.info(
            f"Email sent via Gmail API to {len(to_list)} recipients "
            f"(message ID: {message_id})"
        )
        return {
            "email_send_status": "ok",
            "email_message_id": message_id,
            "email_recipients": to_list,
            "email_send_timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Gmail API dispatch failed: {e}")
        return {"email_send_status": f"failed: {e}"}


# ── Delivery Logging ─────────────────────────────────────────────────

def _log_delivery(result: dict):
    """Log delivery to delivery_log table."""
    pdf_path = result.get("pdf_path", "")
    pdf_size = 0
    if pdf_path and Path(pdf_path).exists():
        pdf_size = Path(pdf_path).stat().st_size // 1024

    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO delivery_log
                   (run_date, report_type, pdf_path, pdf_size_kb,
                    drive_file_id, drive_view_link, drive_upload_status,
                    email_recipients, email_send_status, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                result.get("run_date"),
                result.get("report_type"),
                pdf_path,
                pdf_size,
                result.get("drive_file_id", ""),
                result.get("drive_view_link", ""),
                result.get("drive_upload_status", ""),
                json.dumps(result.get("email_recipients", [])),
                result.get("email_send_status", ""),
                "",
            ),
        )
