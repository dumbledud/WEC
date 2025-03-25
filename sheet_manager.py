import streamlit as st
import json
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import threading
import time
from datetime import datetime

################################################################################
# Streamlit secrets-based GSpread client
################################################################################

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

def get_gspread_client():
    """
    Reads the service account JSON from st.secrets["gcp_credentials"],
    then returns an authorized gspread client.
    Make sure your secrets contain:
      gcp_credentials: |
        {
          "type": "service_account",
          "project_id": "wecledger",
          "private_key_id": "...",
          "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----
