"""
Sends notification emails via SMTP. Credentials come from st.secrets["smtp"].
If sending fails (e.g. bad network, wrong credentials), the request itself is
never blocked - the failure is just shown as a warning so the app keeps working.
"""
import smtplib
from email.mime.text import MIMEText

import streamlit as st


def send_email(to_address: str, subject: str, body: str) -> bool:
    if not to_address:
        return False
    try:
        cfg = st.secrets["smtp"]
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = cfg["sender_email"]
        msg["To"] = to_address

        with smtplib.SMTP(cfg["host"], int(cfg["port"])) as server:
            server.starttls()
            server.login(cfg["sender_email"], cfg["sender_password"])
            server.sendmail(cfg["sender_email"], [to_address], msg.as_string())
        return True
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Note: the notification email could not be sent ({exc}). The request itself was saved successfully.")
        return False
