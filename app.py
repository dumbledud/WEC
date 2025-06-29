import streamlit as st
from datetime import datetime
from sheet_manager import init_sheets, register_user, post_pr, get_balance

st.title("WeCoin MVP")

init_sheets()

menu = st.sidebar.selectbox("Menu", ["Register", "Post PR", "View Balance"])

user_id = st.text_input("Enter your user ID:")

if menu == "Register":
    if st.button("Register"):
        register_user(user_id)
        st.success(f"User {user_id} registered!")

elif menu == "Post PR":
    if st.button("Post Personal Record"):
        post_pr(user_id)
        st.success("PR posted!")

elif menu == "View Balance":
    balance = get_balance(user_id)
    st.write(f"User {user_id} has {balance} WeCoin")
