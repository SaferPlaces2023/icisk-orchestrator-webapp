import os

import streamlit as st

from icisk_orchestrator_db import DBI
from icisk_orchestrator_webapp import langgraph_interface as lgi
from icisk_orchestrator_webapp.session.state import session_manager
from icisk_orchestrator_webapp import utils



st.set_page_config(page_title="ICisk AI Orchestrator — Login", page_icon="🔐", layout="wide")



def validate_login(user_id: str):
    """
    Validate the user ID and set up the session.
    """
    print(f"Validating user ID: {user_id}")
    user = DBI.user_by_id(user_id)
    print(f"User: {user}")
    if user is not None:
        return True
    else:
        return False


_, center_col, _ = st.columns([1, 1, 1], vertical_alignment="center") 

with center_col:   
    
    st.image(utils.StaticPaths.ICISK_LOGO, use_container_width=True)
    
    st.divider()
    
    st.markdown('<div><h2 style="text-align: center; margin-bottom: 5%">🔐 ICisk AI Orchestrator — Login</h2>', unsafe_allow_html=True)

    with st.form("login-form"):
        st.markdown("Please enter your user ID to log in. If you don't have an account, please contact the administrator.")
        
        user_id = st.text_input("User ID", placeholder="your-icisk-ai-agent-user-id")

        if st.form_submit_button("Login"):
            if validate_login(user_id=user_id):
                session_manager.setup(user_id=user_id)
                st.rerun()
            else:
                st.divider()
                st.error("Invalid user ID. Please try again.")
                st.stop()
                
# TODO: Maybe some description, footer, credits, etc.