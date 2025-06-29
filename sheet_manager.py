import streamlit as st
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_NAME = "wecledger"

def get_gspread_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(st.secrets["gcp_credentials"]), SCOPE)
    return gspread.authorize(creds)

def init_sheets():
    gc = get_gspread_client()
    sh = gc.open(SPREADSHEET_NAME)
    for name in ["Users", "Ledger"]:
        try:
            sh.worksheet(name)
        except gspread.WorksheetNotFound:
            sh.add_worksheet(title=name, rows=1000, cols=10)

def register_user(user_id):
    ws = get_gspread_client().open(SPREADSHEET_NAME).worksheet("Users")
    if user_id not in [row[0] for row in ws.get_all_values()[1:]]:
        ws.append_row([user_id, 400000])

def post_pr(user_id):
    sh = get_gspread_client().open(SPREADSHEET_NAME)
    users_ws = sh.worksheet("Users")
    ledger_ws = sh.worksheet("Ledger")
    data = users_ws.get_all_records()
    for i, row in enumerate(data):
        if row['user_id'] == user_id:
            balance = float(row['balance']) + 10
            users_ws.update_cell(i + 2, 2, balance)
            break
    ledger_ws.append_row([str(datetime.now()), user_id, "PR", 10])

def get_balance(user_id):
    ws = get_gspread_client().open(SPREADSHEET_NAME).worksheet("Users")
    data = ws.get_all_records()
    for row in data:
        if row['user_id'] == user_id:
            return row['balance']
    return 0
