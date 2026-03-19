import streamlit as st

from sheet_manager import get_balance, init_sheets, post_pr, register_user

st.set_page_config(page_title="WeCoin MVP")
st.title("WeCoin MVP")
st.caption("A minimal Streamlit app for registering users, posting PRs, and checking balances.")

init_sheets()

menu = st.sidebar.selectbox("Menu", ["Register", "Post PR", "View Balance"])
user_id = st.text_input("Enter your user ID:").strip()

if menu == "Register":
    if st.button("Register"):
        if not user_id:
            st.error("Please enter a user ID before registering.")
        else:
            created = register_user(user_id)
            if created:
                st.success(f"User {user_id} registered!")
            else:
                st.info(f"User {user_id} is already registered.")

elif menu == "Post PR":
    if st.button("Post Personal Record"):
        if not user_id:
            st.error("Please enter a user ID before posting a PR.")
        else:
            awarded = post_pr(user_id)
            if awarded:
                st.success("PR posted!")
            else:
                st.error("User not found. Please register first.")

elif menu == "View Balance":
    if not user_id:
        st.info("Enter a user ID to view the current balance.")
    else:
        balance = get_balance(user_id)
        st.write(f"User {user_id} has {balance} WeCoin")
