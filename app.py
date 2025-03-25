import streamlit as st
from awarding_logic import (
    register_user, post_pr, post_ea, view_wallet, dev_override
)
from awarding_logic import CONFIG
from graph_logic import generate_award_graph

def main():
    st.title("WeCoin - Best Version Simulation")
    st.write("This app uses Google Sheets for concurrency, caching, hour-based logic, dev overrides, and awarding graphs.")

    menu = ["Register","Post PR","Post EA","View Wallet","Show Graph","Dev Override"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Register":
        st.subheader("Register User")
        user_id = st.text_input("User ID")
        if st.button("Register"):
            if user_id.strip():
                msg = register_user(user_id.strip())
                st.success(msg)
            else:
                st.warning("Please enter a user ID.")

    elif choice == "Post PR":
        st.subheader("Post a Personal Record")
        user_id = st.text_input("User ID")
        if st.button("Post PR"):
            if user_id.strip():
                msg = post_pr(user_id.strip())
                st.info(msg)
            else:
                st.warning("Enter a user ID.")

    elif choice == "Post EA":
        st.subheader("Post an Encouraging Act")
        user_id = st.text_input("User ID")
        if st.button("Post EA"):
            if user_id.strip():
                msg = post_ea(user_id.strip())
                st.info(msg)
            else:
                st.warning("Enter a user ID.")

    elif choice == "View Wallet":
        st.subheader("View Wallet")
        user_id = st.text_input("User ID")
        if st.button("Check Wallet"):
            if user_id.strip():
                msg = view_wallet(user_id.strip())
                st.success(msg)
            else:
                st.warning("Enter a user ID.")

    elif choice == "Show Graph":
        st.subheader("Award Graph")
        mode = st.selectbox("Graph Mode", ["global","user","pr","ea"])
        user_id = None
        if mode == "user":
            user_id = st.text_input("Which user ID?")

        if st.button("Generate Graph"):
            png_data = generate_award_graph(mode=mode, user_id=user_id)
            st.image(png_data, caption=f"Award Graph - {mode}")

    elif choice == "Dev Override":
        st.subheader("Developer Override")
        secret_key = st.text_input("Secret Key", type="password")
        st.write("Enter new params as JSON (e.g. {\"DAILY_USER_CAP\":20000})")
        raw_json = st.text_area("New Params JSON")
        if st.button("Override"):
            import json
            try:
                new_params = json.loads(raw_json)
            except:
                st.error("Invalid JSON.")
                return

            success, msg = dev_override(secret_key, new_params)
            if success:
                st.success(msg)
            else:
                st.error(msg)

    st.write("---")
    st.write("Current CONFIG:", CONFIG)

if __name__ == "__main__":
    main()
