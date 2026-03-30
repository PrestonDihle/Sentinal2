"""
SENTINEL2 — Report Dissemination
Handles delivery of reports via Google Drive upload and email dispatch.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.db.connection import execute_query, get_cursor
from src.utils.config import get_config

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
      2. Send email with Drive link to recipients
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

    # Step 2: Send email
    if drive_result.get("drive_view_link"):
        email_result = _send_email(
            run_date, report_type,
            drive_result["drive_view_link"],
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


# ── Google Drive Upload ───────────────────────────────────────────────

def _upload_to_drive(pdf_path: str, report_type: str, run_date: str) -> dict:
    """Upload PDF to Google Drive."""
    config = get_config()
    drive_cfg = config.get("delivery", {}).get("google_drive", {})

    if not drive_cfg.get("enabled", False):
        logger.info("Google Drive upload disabled in config")
        return {"drive_upload_status": "disabled"}

    folder_id = os.environ.get(
        drive_cfg.get("folder_id_env", "SENTINEL_DRIVE_FOLDER_ID"), ""
    )
    if not folder_id:
        logger.warning("No Drive folder ID configured")
        return {"drive_upload_status": "no_folder_id"}

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds_path = os.environ.get(
            drive_cfg.get("credentials_env", "GOOGLE_APPLICATION_CREDENTIALS"), ""
        )
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
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


# ── Email Dispatch ────────────────────────────────────────────────────

def _send_email(
    run_date: str,
    report_type: str,
    drive_link: str,
    pdf_path: str,
) -> dict:
    """Send report notification email to recipients."""
    config = get_config()
    email_cfg = config.get("delivery", {}).get("email", {})

    if not email_cfg.get("enabled", False):
        logger.info("Email dispatch disabled in config")
        return {"email_send_status": "disabled"}

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

    body = (
        f"SENTINEL2 {report_type.replace('_', ' ').title()} Report\n"
        f"Date: {run_date}\n\n"
        f"View report: {drive_link}\n\n"
        f"Classification: UNCLASSIFIED // AI GENERATED\n"
        f"Objective. Non-Partisan. Actionable."
    )

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.application import MIMEApplication

        smtp_host = os.environ.get(email_cfg.get("smtp_host_env", ""), "")
        smtp_port = int(os.environ.get(email_cfg.get("smtp_port_env", ""), "587"))
        smtp_user = os.environ.get(email_cfg.get("smtp_user_env", ""), "")
        smtp_pass = os.environ.get(email_cfg.get("smtp_password_env", ""), "")
        from_addr = email_cfg.get("from_address", smtp_user)

        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_list)
        msg.attach(MIMEText(body, "plain"))

        # Attach PDF
        if Path(pdf_path).exists():
            with open(pdf_path, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header(
                    "Content-Disposition", "attachment",
                    filename=Path(pdf_path).name,
                )
                msg.attach(attachment)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(from_addr, to_list, msg.as_string())

        logger.info(f"Email sent to {len(to_list)} recipients")
        return {
            "email_send_status": "ok",
            "email_recipients": to_list,
            "email_send_timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Email dispatch failed: {e}")
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
