import os
import ast
import time

from io import StringIO

import nbformat as nbf

import nest_asyncio; nest_asyncio.apply()
import asyncio
import streamlit as st

from icisk_orchestrator_webapp import utils
from icisk_orchestrator_webapp import langgraph_interface as lgi
from icisk_orchestrator_webapp.session.state import session_manager, Interrupt

from icisk_orchestrator_db import DBI, DBS



st.set_page_config(page_title="ICisk AI Orchestrator", page_icon="🧠", layout="wide")
st.markdown("### 🧠 ICisk AI Orchestrator")


with st.sidebar:
    
    # DOC: Sidebar element used as a menu for the user
    with st.expander("**🚀 Quick actions**", expanded=True):
        if st.button("New chat", type="primary", help="Start a new chat"):
            session_manager.close_chat()
            session_manager.setup(session_manager.user_id)
            st.rerun()
        
        col_tool_choice, col_tool_flag = st.columns([7  , 1], vertical_alignment="center")    
        with col_tool_choice:
            session_manager.gui.tool_choice = st.selectbox(
                f"Select specific tool to use",
                options = [
                    'Use all tools (default)'
                ] + [   # TODO: my godness, use a ref 
                    'cds_historic_notebook_tool',
                    'cds_forecast_notebook_tool',
                    'spi_historic_notebook_tool',
                    'spi_forecast_notebook_tool',
                    'code_editor_tool'
                ],
                index=0,
                placeholder="Select a tool",
                label_visibility="collapsed",
                key = "tool_choice"
            )
        with col_tool_flag:
            if session_manager.gui.tool_choice is not None and session_manager.gui.tool_choice != 'Use all tools (default)':
                st.markdown("🔴")
            else:
                st.markdown("🔘")

    
    st.divider()
    
    
    # DOC: Sidebar element used as file-manager (view, upload, download)
    with st.expander("**📁 File manager**"):
        avaliable_files = session_manager.gui.filenames
        
        if st.button("Refresh", help="Refresh file list", type='tertiary', icon=":material/refresh:"):
            st.rerun()
        
        if len(avaliable_files) == 0:
            st.markdown("No files uploaded yet.")
        
        else:
            with utils.css_component(st.container, key='file-container', css_dict={'max-height': '400px', 'overflow-y': 'scroll'}):
                for ifn,file_obj in enumerate(avaliable_files):
                    filename = file_obj.name
                    col_name, col_view, col_download = st.columns([5, 1, 1], vertical_alignment="center")
                    
                    with col_name:
                        st.markdown(f">  **`{filename}`**")
                        
                    with col_view:
                        if st.button("👁️", key=f"view_{filename}-{ifn}", help="view file"):
                            utils.dialog_notebook_code(
                                dialog_title = filename,
                                notebook_code = DBI.notebook_by_name(author=session_manager.user_id, notebook_name=filename, retrieve_source=True).source_code,
                            )
                            
                    with col_download:
                        if session_manager.gui.is_requested_download(filename):
                            st.download_button(
                                label = "📥",
                                data = DBI.notebook_by_name(author=session_manager.user_id, notebook_name=filename, retrieve_source=True).source_code,
                                file_name = filename,
                                mime = "json/ipynb",
                                key = f"download_{filename}-{ifn}"
                            )
                        else:
                            if st.button("📁", key=f"pre-download_{filename}-{ifn}", help="request download"):
                                session_manager.gui.request_download(filename)
                                st.rerun()
                        
        st.divider()
        
        uploader_col, sender_col = st.columns([4, 1])
        
        with uploader_col:
            file_uploader = st.file_uploader("Upload", label_visibility="collapsed", type='ipynb')
        
        with sender_col:
            if st.button("Upload", help="upload file"):
                if file_uploader is not None:
                    DBI.save_notebook(
                        DBS.Notebook(
                            _id = None,
                            name = file_uploader.name,
                            source = nbf.reads(StringIO(file_uploader.getvalue().decode("utf-8")).read(), as_version=4),
                            authors = session_manager.user_id,
                            description = None
                        )
                    )
                st.rerun()



with st.expander("# 💡 **What is this application?** "):
    st.markdown(
        """
        This is a multi-agent artificial intelligence system built with LangGraph and OpenAI models.  
        It is designed to assist users in the guided generation of interactive notebooks by leveraging the **ICisk** project APIs for the retrieval, processing, and visualization of climate data.  
            
        The goal is to simplify environmental data analysis through an intelligent conversational interface capable of guiding users step by step in building their data workflows.  
        
        **This is a beta version**. At the moment, it can assist in: 
        - Obtaining historical and forecast data relating to precipitation, temperature, and river discharge (with notebook creation).
        - Calculation of the **Standardized Precipitation Index (SPI)** with historical and forecast data (with notebook creation).
        - Code generation targeted to created notebooks.
        Additional processing capabilities will be available soon. 
        
        For more details _(i.e: on the agent or on the used data)_, simply interact with the bot.
        """
    )

    

for message in session_manager.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        

    
def render_message(role, content):
    avatar = {
        "user": None,
        "assistant": None,
        "tool": "🛠️"
    }
    st.chat_message(role, avatar=avatar[role]).markdown(content)
    session_manager.chat_history.append({"role": role, "content": content})

def render_user_prompt(prompt):
    render_message("user", prompt)

def render_agent_response(message):
    
    if len(message.get('tool_calls', [])) > 0:
        for tool_call in message['tool_calls']:
            header = f"##### Using tool: _{tool_call['name']}_"
            tool_table = utils.tool_args_md_table(tool_call['args'])
            content = f"{header}\n\n{tool_table}" if tool_table else header
            render_message("tool", content)
    
    if len(message.get('content', [])) > 0:
        if message.get('interrupt', False):
            message['content'] = f"**Interaction required [ _{message['interrupt']['interrupt_type']}_ ]: 💬**\n\n{message['content']}"
        render_message("assistant", message['content'])

   
def handle_response(response):
    for author, data in response.items():
        if data is None:
            continue
        message = None
        if author == 'chatbot':
            messages = data.get('messages', [])
            message = messages[-1] if len(messages) > 0 else None
        elif author == '__interrupt__':
            message = data[0].get('value', None) if len(data) > 0 else None
            session_manager.interrupt = Interrupt(interrupt_type = message['interrupt_type'], resume_key=message.get('resume_key', 'response'))
            message['interrupt'] = session_manager.interrupt.as_dict
        
        session_manager.update_chat(message)
        
        if message is not None and message.get('type', None) != 'system':
            render_agent_response(message)
            

prompt = st.chat_input(key="chat-input", placeholder="Scrivi un messaggio")    
            
if prompt:
    session_manager.update_chat({"type": "human", "content": prompt})
    render_user_prompt(prompt)
    
    def optional_resume_interrupt():
        out = dict()
        if session_manager.is_interrupted():
            out['interrupt_response_key'] = session_manager.interrupt.resume_key
            session_manager.interrupt = None
        return out
    
    def optional_tool_choice():
        out = dict()
        if session_manager.gui.tool_choice is not None and session_manager.gui.tool_choice != 'Use all tools (default)':    # TODO: Use a dict plz
            out['tool_choice'] = session_manager.gui.tool_choice
        return out
            
    async def run_chat():
        
        additional_args = {
            **optional_resume_interrupt(),
            **optional_tool_choice()
        }        
        
        async for message in lgi.ask_agent(
            session_manager.client, 
            session_manager.thread_id, 
            prompt,
            **additional_args
        ):
            handle_response(message)
        
    
    asyncio.run(run_chat())