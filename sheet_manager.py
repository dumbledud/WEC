import streamlit as st
import json
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import threading
import time
from datetime import datetime

################################################################################
# Constants & Concurrency
################################################################################

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

SPREADSHEET_NAME = "wecledger"  # Make sure your doc is named exactly "wecledger"

# Concurrency lock for all read/write sheet operations
sheet_lock = threading.Lock()

# Simple caches for user data, ledger data, and hour-based simulation data
user_cache = {}
ledger_cache = {"rows": [], "last_fetch": 0}
simulation_cache = {"data": {}, "last_fetch": 0}

# Time-to-live for cache data
MAX_CACHE_AGE_SECONDS = 30
LEDGER_CACHE_TTL = 60
SIM_CACHE_TTL = 30

class SheetError(Exception):
    """Custom error to wrap GSheets connection or operation issues."""
    pass

################################################################################
# GSpread Client from Streamlit Secrets
################################################################################

def get_gspread_client():
    """
    Reads the entire JSON from st.secrets["gcp_credentials"], then builds a
    gspread client for Google Sheets. Make sure your secrets contain:
        gcp_credentials: |
          {
            "type": "service_account",
            "project_id": "...",
            "private_key_id": "...",
            "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
            "client_email": "...@....iam.gserviceaccount.com",
            ...
          }
    """
    try:
        raw_cred_json = st.secrets["gcp_credentials"]  # multi-line JSON from secrets
    except KeyError:
        raise SheetError(
            "No 'gcp_credentials' key found in Streamlit secrets. "
            "Add your service account JSON under that key."
        )

    try:
        cred_dict = json.loads(raw_cred_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, SCOPE)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        raise SheetError(f"Error authorizing gspread via secrets: {e}")

################################################################################
# SheetManager class
################################################################################

class SheetManager:
    """
    Handles connecting to the 'wecledger' spreadsheet, retrieving or creating
    the 'Users', 'Ledger', and 'Simulation' worksheets if not found.
    """
    def __init__(self):
        self.gc = None
        self.sh = None
        self.users_ws = None
        self.ledger_ws = None
        self.sim_ws = None
        self._connect_sheets()

    def _connect_sheets(self):
        """
        Authenticates via get_gspread_client(), attempts to open 'wecledger',
        and ensures 'Users', 'Ledger', and 'Simulation' worksheets exist.
        """
        try:
            self.gc = get_gspread_client()
            self.sh = self.gc.open(SPREADSHEET_NAME)

            # Ensure 'Users' sheet
            try:
                self.users_ws = self.sh.worksheet("Users")
            except gspread.WorksheetNotFound:
                self.users_ws = self.sh.add_worksheet("Users", rows=100, cols=10)
                self.users_ws.update(
                    "A1:F1",
                    [["user_id","balance","daily_earned","daily_pr_count","total_earned_ever","last_daily_reset"]]
                )

            # Ensure 'Ledger' sheet
            try:
                self.ledger_ws = self.sh.worksheet("Ledger")
            except gspread.WorksheetNotFound:
                self.ledger_ws = self.sh.add_worksheet("Ledger", rows=100, cols=10)
                self.ledger_ws.update(
                    "A1:F1",
                    [["timestamp","user_id","action_type","pr_or_ea_id","amount_awarded","notes"]]
                )

            # Ensure 'Simulation' sheet
            try:
                self.sim_ws = self.sh.worksheet("Simulation")
            except gspread.WorksheetNotFound:
                self.sim_ws = self.sh.add_worksheet("Simulation", rows=10, cols=10)
                self.sim_ws.update("A1:C1", [["hour_index","hour_awarding_so_far","current_multiplier"]])
                self.sim_ws.update("A2:C2", [[0, 0.0, 1.0]])

        except Exception as e:
            # Re-raise as SheetError with redacted message
            raise SheetError(f"Error connecting to Google Sheets: {e}")

################################################################################
# Instantiate the global manager
################################################################################

sheet_mgr = SheetManager()

################################################################################
# Access Functions for Each Worksheet
################################################################################

def get_users_ws():
    return sheet_mgr.users_ws

def get_ledger_ws():
    return sheet_mgr.ledger_ws

def get_sim_ws():
    return sheet_mgr.sim_ws

################################################################################
# User Data: find/read/update/create
################################################################################

def find_user_row(user_id):
    """
    Returns 1-based row index of user_id in 'Users', or None if not found.
    """
    with sheet_lock:
        try:
            records = sheet_mgr.users_ws.get_all_records()
        except Exception as e:
            raise SheetError(f"Error reading Users sheet: {e}")

    for idx, rec in enumerate(records, start=2):
        if str(rec["user_id"]) == str(user_id):
            return idx
    return None

def read_user_row(row_num):
    """Reads a single user's data from row_num in 'Users'."""
    try:
        with sheet_lock:
            row_values = sheet_mgr.users_ws.row_values(row_num)
        return {
            "user_id": row_values[0],
            "balance": float(row_values[1]),
            "daily_earned": float(row_values[2]),
            "daily_pr_count": int(row_values[3]),
            "total_earned_ever": float(row_values[4]),
            "last_daily_reset": row_values[5]
        }
    except Exception as e:
        raise SheetError(f"Error reading user row {row_num}: {e}")

def update_user_row(row_num, user_dict):
    """
    Writes updated user data back to 'Users' in row_num.
    """
    row_values = [
        user_dict["user_id"],
        user_dict["balance"],
        user_dict["daily_earned"],
        user_dict["daily_pr_count"],
        user_dict["total_earned_ever"],
        user_dict["last_daily_reset"]
    ]
    cell_range = f"A{row_num}:F{row_num}"
    try:
        with sheet_lock:
            sheet_mgr.users_ws.update(cell_range, [row_values], value_input_option="RAW")
    except Exception as e:
        raise SheetError(f"Error updating user row {row_num}: {e}")

def create_user_row(user_id, starting_balance=400000):
    """
    Appends a new user row with a default daily reset date (today).
    """
    now_date = datetime.now().date().isoformat()
    row_data = [user_id, starting_balance, 0, 0, 0, now_date]
    try:
        with sheet_lock:
            sheet_mgr.users_ws.append_row(row_data, value_input_option="RAW")
    except Exception as e:
        raise SheetError(f"Error creating user row for {user_id}: {e}")

################################################################################
# Caching for Users
################################################################################

def get_user_data(user_id, max_cache_age=MAX_CACHE_AGE_SECONDS):
    """
    Returns the user's data from the local cache if fresh, otherwise from 'Users'.
    If user doesn't exist, create a row. Then cache the data.
    """
    now_ts = time.time()
    cached = user_cache.get(user_id)

    if cached:
        if now_ts - cached["last_fetch"] < max_cache_age:
            return cached["data"]

    # Not cached or stale => check sheet
    row_num = find_user_row(user_id)
    if not row_num:
        create_user_row(user_id)
        row_num = find_user_row(user_id)

    user_dict = read_user_row(row_num)
    user_cache[user_id] = {
        "data": user_dict,
        "row_num": row_num,
        "last_fetch": now_ts
    }
    return user_dict

def update_user_data(user_dict):
    """
    Writes updated user data to 'Users' and refreshes local cache.
    """
    user_id = user_dict["user_id"]
    cached = user_cache.get(user_id)
    if not cached:
        row_num = find_user_row(user_id)
        if not row_num:
            create_user_row(user_id, user_dict["balance"])
            row_num = find_user_row(user_id)
        user_cache[user_id] = {
            "data": user_dict,
            "row_num": row_num,
            "last_fetch": time.time()
        }
    else:
        row_num = cached["row_num"]

    update_user_row(row_num, user_dict)
    user_cache[user_id]["data"] = user_dict
    user_cache[user_id]["last_fetch"] = time.time()

################################################################################
# Ledger Data: get_ledger_data / append_ledger
################################################################################

def get_ledger_data():
    """
    Returns rows from 'Ledger', caching them for LEDGER_CACHE_TTL seconds.
    Each row format: [timestamp, user_id, action_type, pr_or_ea_id, amount_awarded, notes]
    """
    now_ts = time.time()
    if (now_ts - ledger_cache["last_fetch"] < LEDGER_CACHE_TTL) and ledger_cache["rows"]:
        return ledger_cache["rows"]

    try:
        with sheet_lock:
            rows = sheet_mgr.ledger_ws.get_all_values()
        data_rows = rows[1:]  # skip header
        ledger_cache["rows"] = data_rows
        ledger_cache["last_fetch"] = now_ts
        return data_rows
    except Exception as e:
        raise SheetError(f"Error reading Ledger data: {e}")

def append_ledger(user_id, action_type, pr_or_ea_id, amount_awarded, notes=""):
    """
    Appends a row to 'Ledger' with the given user/action/award. Invalidates ledger cache.
    """
    timestamp = datetime.now().isoformat()
    row_data = [timestamp, user_id, action_type, pr_or_ea_id, amount_awarded, notes]
    try:
        with sheet_lock:
            sheet_mgr.ledger_ws.append_row(row_data, value_input_option="RAW")
        ledger_cache["rows"] = []
        ledger_cache["last_fetch"] = 0
    except Exception as e:
        raise SheetError(f"Error appending ledger row: {e}")

################################################################################
# Simulation Data (hour-based logic)
################################################################################

def read_simulation_data():
    """
    Reads hour_index, hour_awarding_so_far, current_multiplier from row 2 of 'Simulation'.
    """
    try:
        with sheet_lock:
            row_values = sheet_mgr.sim_ws.row_values(2)
        hour_idx = int(row_values[0]) if row_values[0] else 0
        hour_award = float(row_values[1]) if row_values[1] else 0.0
        curr_mult = float(row_values[2]) if row_values[2] else 1.0
        return {
            "hour_index": hour_idx,
            "hour_awarding_so_far": hour_award,
            "current_multiplier": curr_mult
        }
    except Exception as e:
        raise SheetError(f"Error reading simulation data: {e}")

def write_simulation_data(sim_dict):
    """
    Writes hour_index, hour_awarding_so_far, current_multiplier to row 2 of 'Simulation'.
    """
    row_values = [
        sim_dict.get("hour_index", 0),
        sim_dict.get("hour_awarding_so_far", 0.0),
        sim_dict.get("current_multiplier", 1.0)
    ]
    try:
        with sheet_lock:
            sheet_mgr.sim_ws.update("A2:C2", [row_values], value_input_option="RAW")
    except Exception as e:
        raise SheetError(f"Error writing simulation data: {e}")

def get_simulation_data():
    """
    Returns the simulation row from cache or from sheet if stale.
    """
    now_ts = time.time()
    if (now_ts - simulation_cache["last_fetch"] < SIM_CACHE_TTL) and simulation_cache["data"]:
        return simulation_cache["data"]

    data = read_simulation_data()
    simulation_cache["data"] = data
    simulation_cache["last_fetch"] = now_ts
    return data

def update_simulation_data(sim_data):
    """
    Writes sim_data to the sheet and updates the local cache.
    """
    write_simulation_data(sim_data)
    simulation_cache["data"] = sim_data
    simulation_cache["last_fetch"] = time.time()
