import json
from datetime import datetime

import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_NAME = "wecledger"
USERS_HEADERS = ["user_id", "balance"]
LEDGER_HEADERS = ["timestamp", "user_id", "action", "amount"]
STARTING_BALANCE = 400000
PR_AWARD = 10


def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_credentials"]),
        SCOPE,
    )
    return gspread.authorize(creds)


def _get_or_create_worksheet(spreadsheet, title, headers):
    try:
        worksheet = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=max(len(headers), 10))

    values = worksheet.get_all_values()
    if not values:
        worksheet.append_row(headers)
    elif values[0] != headers:
        worksheet.update("A1", [headers])

    return worksheet


def init_sheets():
    spreadsheet = get_gspread_client().open(SPREADSHEET_NAME)
    _get_or_create_worksheet(spreadsheet, "Users", USERS_HEADERS)
    _get_or_create_worksheet(spreadsheet, "Ledger", LEDGER_HEADERS)


def register_user(user_id):
    worksheet = get_gspread_client().open(SPREADSHEET_NAME).worksheet("Users")
    existing_user_ids = [row[0] for row in worksheet.get_all_values()[1:] if row]
    if user_id in existing_user_ids:
        return False

    worksheet.append_row([user_id, STARTING_BALANCE])
    return True


def post_pr(user_id):
    spreadsheet = get_gspread_client().open(SPREADSHEET_NAME)
    users_ws = spreadsheet.worksheet("Users")
    ledger_ws = spreadsheet.worksheet("Ledger")

    data = users_ws.get_all_records()
    for index, row in enumerate(data, start=2):
        if row["user_id"] == user_id:
            balance = float(row["balance"]) + PR_AWARD
            users_ws.update_cell(index, 2, balance)
            ledger_ws.append_row([datetime.now().isoformat(), user_id, "PR", PR_AWARD])
            return True

    return False


def get_balance(user_id):
    worksheet = get_gspread_client().open(SPREADSHEET_NAME).worksheet("Users")
    data = worksheet.get_all_records()
    for row in data:
        if row["user_id"] == user_id:
            return row["balance"]
    return 0
