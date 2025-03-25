import streamlit as st
import json

from sheet_manager import (
    get_user_data, update_user_data,
    append_ledger, get_simulation_data, update_simulation_data,
    SheetError
)


from awarding_logic import (
    register_user, post_pr, post_ea, view_wallet, dev_override, CONFIG
)
from graph_logic import generate_award_graph

def main():
    st.title("WeCoin - Full Concurrency + Secrets + Graphs Example")
    st.write("This Streamlit app uses Google Sheets for data, concurrency + caching, hour-based logic, dev override, and awarding graphs.")

    menu = ["Register","Post PR","Post EA","View Wallet","Show Graph","Dev Override"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Register":
        st.subheader("Register a User")
        user_id = st.text_input("User ID:")
        if st.button("Register"):
            if user_id.strip():
                msg = register_user(user_id.strip())
                st.success(msg)
            else:
                st.warning("Please enter a valid user ID.")

    elif choice == "Post PR":
        st.subheader("Post Personal Record")
        user_id = st.text_input("User ID:")
        if st.button("Post PR"):
            if user_id.strip():
                msg = post_pr(user_id.strip())
                st.info(msg)
            else:
                st.warning("No user ID entered.")

    elif choice == "Post EA":
        st.subheader("Post Encouraging Act")
        user_id = st.text_input("User ID:")
        if st.button("Post EA"):
            if user_id.strip():
                msg = post_ea(user_id.strip())
                st.info(msg)
            else:
                st.warning("No user ID entered.")

    elif choice == "View Wallet":
        st.subheader("View Wallet")
        user_id = st.text_input("User ID:")
        if st.button("Check"):
            if user_id.strip():
                msg = view_wallet(user_id.strip())
                st.success(msg)
            else:
                st.warning("No user ID entered.")

    elif choice == "Show Graph":
        st.subheader("Award Graphs")
        mode = st.selectbox("Graph Mode", ["global","user","pr","ea"])
        user_id = None
        if mode == "user":
            user_id = st.text_input("User ID for graph")

        if st.button("Generate Graph"):
            png_data = generate_award_graph(mode=mode, user_id=user_id)
            st.image(png_data, caption=f"Mode={mode}, user={user_id or 'ALL'}")

    elif choice == "Dev Override":
        st.subheader("Developer Override")
        secret_key = st.text_input("Secret Key (hidden)", type="password")
        st.write("Enter new params as JSON, e.g. {\"DAILY_USER_CAP\":20000}")
        raw_json = st.text_area("Params JSON:")
        if st.button("Override"):
            import json
            try:
                new_params = json.loads(raw_json)
            except:
                st.error("Invalid JSON format.")
                return
            success, message = dev_override(secret_key, new_params)
            if success:
                st.success(message)
            else:
                st.error(message)

    st.write("---")
    st.write("**Current Config:**")
    st.json(CONFIG)

if __name__ == "__main__":
    main()
