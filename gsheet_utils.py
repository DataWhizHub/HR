"""
All Google Sheets I/O lives here. Every other module talks to the sheet
through these functions only, so the storage layer can be swapped later
(e.g. for a real database) without touching the UI code.
"""
import uuid
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

from config import USERS_TAB, REQUESTS_TAB, USER_COLUMNS, REQUEST_COLUMNS, SHEET_NAME

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource(show_spinner=False)
def _get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheet():
    return _get_client().open(SHEET_NAME)


def _get_worksheet(tab_name: str, columns: list):
    sheet = _get_sheet()
    try:
        ws = sheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=tab_name, rows=1000, cols=len(columns) + 2)
        ws.append_row(columns)
    return ws


def get_users_df() -> pd.DataFrame:
    ws = _get_worksheet(USERS_TAB, USER_COLUMNS)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=USER_COLUMNS)
    for col in USER_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df


def get_requests_df() -> pd.DataFrame:
    ws = _get_worksheet(REQUESTS_TAB, REQUEST_COLUMNS)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=REQUEST_COLUMNS)
    for col in REQUEST_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df


def append_request(row: dict) -> str:
    """Adds a new leave request row. Returns the generated RequestID."""
    ws = _get_worksheet(REQUESTS_TAB, REQUEST_COLUMNS)
    row = dict(row)
    row["RequestID"] = str(uuid.uuid4())[:8].upper()
    row["RequestedOn"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    row.setdefault("Status", "Pending")
    row.setdefault("HRRemarks", "")
    row.setdefault("DecidedOn", "")
    ordered = [str(row.get(c, "")) for c in REQUEST_COLUMNS]
    ws.append_row(ordered)
    return row["RequestID"]


def update_request_status(request_id: str, status: str, remarks: str = "") -> bool:
    ws = _get_worksheet(REQUESTS_TAB, REQUEST_COLUMNS)
    cell = ws.find(request_id)
    if not cell:
        return False
    header = ws.row_values(1)
    row_idx = cell.row
    ws.update_cell(row_idx, header.index("Status") + 1, status)
    ws.update_cell(row_idx, header.index("HRRemarks") + 1, remarks)
    ws.update_cell(row_idx, header.index("DecidedOn") + 1, datetime.now().strftime("%Y-%m-%d %H:%M"))
    return True
