import gspread
from oauth2client.service_account import ServiceAccountCredentials
import threading
import time
import os
from datetime import datetime

# Google Sheets scopes
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

# Environment variables or fallback for local testing
CRED_FILE = os.environ.get("GSPREAD_CRED_PATH", "credentials.json")
SPREADSHEET_NAME = os.environ.get("SPREADSHEET_NAME", "WeCoinSystem")

# A lock to ensure concurrency safety when reading/writing to the Sheets
sheet_lock = threading.Lock()

# Basic caching for user data and ledger
user_cache = {}          # { user_id: {"data": {...}, "row_num": <int>, "last_fetch": <float>} }
ledger_cache = {"rows": [], "last_fetch": 0}
simulation_cache = {"data": {}, "last_fetch": 0}

MAX_CACHE_AGE_SECONDS = 30
LEDGER_CACHE_TTL = 60
SIM_CACHE_TTL = 30

class SheetError(Exception):
    pass

class SheetManager:
    def __init__(self):
        self.gc = None
        self.users_ws = None
        self.ledger_ws = None
        self.sim_ws = None
        self._connect_sheets()

    def _connect_sheets(self):
        """Authorize and open the spreadsheet, capturing references to each worksheet."""
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, SCOPE)
            gc = gspread.authorize(creds)
            sh = gc.open(SPREADSHEET_NAME)

            # Users
            try:
                self.users_ws = sh.worksheet("Users")
            except gspread.WorksheetNotFound:
                self.users_ws = sh.add_worksheet("Users", rows=100, cols=10)
                self.users_ws.update("A1:F1", [["user_id","balance","daily_earned","daily_pr_count","total_earned_ever","last_daily_reset"]])

            # Ledger
            try:
                self.ledger_ws = sh.worksheet("Ledger")
            except gspread.WorksheetNotFound:
                self.ledger_ws = sh.add_worksheet("Ledger", rows=100, cols=10)
                self.ledger_ws.update("A1:F1", [["timestamp","user_id","action_type","pr_or_ea_id","amount_awarded","notes"]])

            # Simulation
            try:
                self.sim_ws = sh.worksheet("Simulation")
            except gspread.WorksheetNotFound:
                self.sim_ws = sh.add_worksheet("Simulation", rows=10, cols=10)
                self.sim_ws.update("A1:C1", [["hour_index","hour_awarding_so_far","current_multiplier"]])
                self.sim_ws.update("A2:C2", [[0,0.0,1.0]])

            self.gc = gc
        except Exception as e:
            raise SheetError(f"Error connecting to Google Sheets: {e}")

# Global manager
sheet_mgr = SheetManager()

def get_users_ws():
    return sheet_mgr.users_ws

def get_ledger_ws():
    return sheet_mgr.ledger_ws

def get_sim_ws():
    return sheet_mgr.sim_ws

#############
# User Data #
#############
def find_user_row(user_id):
    """Return the 1-based row of user_id in Users sheet, or None if not found."""
    now_ts = time.time()
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
    """Pull user data from row_num in Users sheet."""
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
    """Write user_dict fields back to a row in Users."""
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
    """Append a new user row."""
    now_date = datetime.now().date().isoformat()
    row_data = [user_id, starting_balance, 0, 0, 0, now_date]
    try:
        with sheet_lock:
            sheet_mgr.users_ws.append_row(row_data, value_input_option="RAW")
    except Exception as e:
        raise SheetError(f"Error creating user row for {user_id}: {e}")

def get_user_data(user_id, max_cache_age=MAX_CACHE_AGE_SECONDS):
    """Retrieve user data from cache or sheet if stale/nonexistent. Create row if user doesn't exist."""
    now_ts = time.time()
    cached = user_cache.get(user_id)
    if cached:
        if now_ts - cached["last_fetch"] < max_cache_age:
            return cached["data"]

    # Not cached or stale => check sheet
    row_num = find_user_row(user_id)
    if not row_num:
        # user doesn't exist => create row
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
    """Push updated user_dict to sheet & refresh cache."""
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

###############
# Ledger Data #
###############
def get_ledger_data():
    """Return ledger rows from sheet, caching them for LEDGER_CACHE_TTL seconds."""
    now_ts = time.time()
    if now_ts - ledger_cache["last_fetch"] < LEDGER_CACHE_TTL and ledger_cache["rows"]:
        return ledger_cache["rows"]

    try:
        with sheet_lock:
            rows = sheet_mgr.ledger_ws.get_all_values()
        # skip header
        data_rows = rows[1:]
        ledger_cache["rows"] = data_rows
        ledger_cache["last_fetch"] = now_ts
        return data_rows
    except Exception as e:
        raise SheetError(f"Error reading ledger data: {e}")

def append_ledger(user_id, action_type, pr_or_ea_id, amount_awarded, notes=""):
    timestamp = datetime.now().isoformat()
    row_data = [timestamp, user_id, action_type, pr_or_ea_id, amount_awarded, notes]
    try:
        with sheet_lock:
            sheet_mgr.ledger_ws.append_row(row_data, value_input_option="RAW")
        # Invalidate ledger cache
        ledger_cache["rows"] = []
        ledger_cache["last_fetch"] = 0
    except Exception as e:
        raise SheetError(f"Error appending ledger row: {e}")

#####################
# Simulation (Hour) #
#####################
def read_simulation_data():
    """Read hour_index, hour_awarding_so_far, current_multiplier from row 2 of Simulation sheet."""
    try:
        with sheet_lock:
            row_data = sheet_mgr.sim_ws.row_values(2)
        hour_idx = int(row_data[0]) if row_data[0] else 0
        hour_award = float(row_data[1]) if row_data[1] else 0.0
        curr_mult = float(row_data[2]) if row_data[2] else 1.0
        return {
            "hour_index": hour_idx,
            "hour_awarding_so_far": hour_award,
            "current_multiplier": curr_mult
        }
    except Exception as e:
        raise SheetError(f"Error reading simulation data: {e}")

def write_simulation_data(sim_dict):
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
    """Cache the simulation row for SIM_CACHE_TTL seconds."""
    now_ts = time.time()
    if now_ts - simulation_cache["last_fetch"] < SIM_CACHE_TTL and simulation_cache["data"]:
        return simulation_cache["data"]

    data = read_simulation_data()
    simulation_cache["data"] = data
    simulation_cache["last_fetch"] = now_ts
    return data

def update_simulation_data(sim_data):
    write_simulation_data(sim_data)
    simulation_cache["data"] = sim_data
    simulation_cache["last_fetch"] = time.time()
