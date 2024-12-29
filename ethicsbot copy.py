import datetime
import io
import os
import sqlite3

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import streamlit as st

import frontend.css as css
from backend.agents import ConvoAgent, EvalAgent
from backend.api_requests import eval_json_to_markdown, textify
from backend.llms import OpenAILLM
from backend.sql import createdb, deletedb, sqlexecute, sqlinsert
from backend.utils import file_extraction

@st.experimental_dialog("Begin Conversation?")
def begin_convo(document, doctype):
    st.write("Are you sure you want to start a new conversation with the VC Agent?")
    # Conversation parameters (base questions, tenacity, max_follow_up)
    scepticism = st.slider("Select VC Scepticism (0 = Push Over Investor; 1 = Tight Wad)", 
                            min_value = 0.0, max_value=1.0, step = .05, value = 1.0, key="convo_scepticism")
    temp = st.slider("Select model creativity (0 = Always a Consistent Response; 1 = Wild West of Insults)", 
                            min_value = 0.0, max_value=1.0, step = .05, value = 1.0, key="convo_temperature")   
    tenacity = st.slider("Tenacity of investor to continue asking questions in a topic", 
                            min_value = 0.0, max_value=.75, step = .05, value = .5)                  
    col1, col2 = st.columns(2)
    base_questions = col1.number_input("Number of topic chains", value=5, placeholder="Type a number...")
    max_follow_up = col2.number_input("Max follow ups in a chain", value=5, placeholder="Type a number...")

    # If launch
    if st.button("Begin Conversation"):
        st.session_state.agent_args['scepticism'] = scepticism
        st.session_state.agent_args['temperature'] = temp
        st.session_state.user_launched_convo = True
        with st.spinner('Calling the VC team...'):
            st.session_state.messages.append({"role": "assistant", "content": "You can quit a conversation at anytime by responding with 'QUIT'"})  
            llm = OpenAILLM(openaikey, temperature=temp)
            st.session_state.convo_agent = ConvoAgent(llm, scepticism=scepticism)  
            agent_response = st.session_state.convo_agent.initialize(content=document, document_type=doctype, 
                                                                     base_questions=base_questions, tenacity=tenacity, max_follow_up=max_follow_up)
            st.session_state.messages.append({"role": "assistant", "content": agent_response})   
        st.rerun()

# ========================================================================================================================
# Establish app and session_state variables
st.set_page_config(page_title='⚖️ Ethics Bot', layout='wide')

if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None
if 'doctype' not in st.session_state:
    st.session_state['doctype'] = None
if 'loaded' not in st.session_state:
    st.session_state['loaded'] = False
if 'upload_counter' not in st.session_state:
    st.session_state['upload_counter'] = 0

if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_launched_convo" not in st.session_state:
    st.session_state.user_launched_convo = False
if "convo_agent" not in st.session_state:
    st.session_state.convo_agent = None 
if "agent_args" not in st.session_state:
    st.session_state.agent_args = {}

# ========================================================================================================================
# Sidebar
with st.sidebar:
    # Image
    st.image('./frontend/mu logo.png', use_column_width=True)
    st.markdown(css.hide_img_fs, unsafe_allow_html=True)
    # API Key
    openaikey = st.text_input("OpenAI API Key", placeholder = "Enter your API Key")
    # Note:
    st.write("Oh hey, just so you know, when you close the app, it will retain no memory of your API key or your documents.")
    # Footer
    st.markdown(css.footer, unsafe_allow_html=True)

# ========================================================================================================================
# Doc types
docs = ['Executive Summary', 'Lean Canvas', 'Pitch Deck', 'Valuation', 'Market Research']
top_col1, top_col2 = st.columns([1, 3])
with top_col1:
    st.header("⚖️ Ethics Bot")
    #st.image('./frontend/mu logo.png', use_column_width=True)
    st.markdown(css.hide_img_fs, unsafe_allow_html=True)    
    doctype = st.selectbox("Select your document type", docs, index=None,
                          placeholder="What are you working on...")
    
# ========================================================================================================================
if doctype is None:
    st.session_state.messages = []
elif doctype == st.session_state['doctype']:
    pass
else: # New selection
    tab1, tab2, tab3, tab4 = st.tabs(['Load', 'Feedback', 'Converse', 'History'])

    # Load
    with tab1:
        col1, col2 = st.columns(2)
        # File uploader
        uploader_key = f"uploaded_file_{st.session_state.upload_counter}"
        uploaded_file = col1.file_uploader("Choose a file to upload.", key=uploader_key)    

        if col1.button("Upload", type='primary'):
            if uploaded_file is not None:
                bytes_io = io.BytesIO(uploaded_file.getvalue())
                filename = uploaded_file.name
                fileext = filename.split('.')[-1]
                extracted = file_extraction(bytes_io, fileext)

                # Upload document
                sqlinsert("INSERT INTO documents (document_type, upload_date, document) VALUES (?, ?, ?)",
                          [doctype, datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"), extracted.replace("'","`")],
                          dbpath)

                # Increment upload counter to reset the file_uploader (new unique ID = clears the variable)
                st.session_state['upload_counter'] += 1

                # Add content to column 2
                with col2:
                    st.title("Content Uploaded!\nProceed to the Feedback or Converse Tabs.")
                    with st.expander("Preview Ingested Content"):
                        dt = f"Content Date: {datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")}"               
                        max_char = 1500
                        if len(extracted) > max_char:
                            extracted = extracted[:max_char] + '...\n\n Content truncated for display purposes only.'                    
                        st.write(dt + '\n\n' + extracted)

            else:
                col2.write("Please upload a file before submitting.")

    # Evaluate
    with tab2:
        if doctype is not None:
            viable = True
            prior = None
            # Check for API key
            if openaikey == '':
                viable = False
                st.error('WARNING! You have not loaded an API Key', icon="🚨")
            # Check for document
            docdata = pd.read_sql(f"SELECT id, document, upload_date FROM documents WHERE document_type = '{doctype}' ORDER BY id DESC LIMIT 1",sqlite3.connect(dbpath))
            if len(docdata) == 0:
                viable = False
                st.error(f'WARNING! You have not loaded a {doctype}.', icon="🚨")
            else:
                # Current
                doc_id = int(docdata.iloc[0]['id'])
                doc_dt = docdata.iloc[0]['upload_date']
                doc = docdata.iloc[0]['document']
                doc.replace("`","'")

                 # Prior
                docdata = pd.read_sql(f"SELECT markdown FROM performance WHERE document_type = '{doctype}' AND Interaction_Type = 'Evaluation' ORDER BY id DESC LIMIT 1", sqlite3.connect(dbpath))
                if len(docdata) == 1:
                    prior = docdata.iloc[0]['markdown']
                    prior.replace("`","'")

            # Get feedback
            if viable == True:
                col1, col2 = st.columns(2)
                scepticism = col1.slider("Select VC Scepticism (0 = Pushover Investor; 1 = Tight Wad)", 
                                        min_value = 0.0, max_value=1.0, step = .05, value = 1.0)
                temp = col2.slider("Select model creativity (0 = Always a Consistent Response; 1 = Wild West of Insults)", 
                                     min_value = 0.0, max_value=1.0, step = .05, value = 1.0)                    
                st.write(f"Utilizing document from: {doc_dt}")
                getfeedback = st.button("Generate Feedback", type='primary')

                # Pass doc to LLM
                if getfeedback == True:
                    st.write('\n\n')
                    with st.spinner('Wait for it...'):
                        llm = OpenAILLM(openaikey, temperature=temp)
                        agent = EvalAgent(llm, scepticism=scepticism)
                        # Execute api call
                        response = agent.evaluate_document(doc, doctype, prior) #, prior
                        text_response = textify(eval_json_to_markdown(response))
                        rightnow = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
                        # Store in server
                        sqlinsert("""INSERT INTO Performance 
                                  (document_type, doc_id, interaction_type, interaction_date, feedback, scepticism, temperature, score, markdown) 
                                  VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                  [doctype, doc_id, 'Evaluation', rightnow, text_response.replace("'","`"), 
                                   scepticism, temp, response.final_score, eval_json_to_markdown(response).replace("'","`")],
                                   dbpath)

                    # Display result
                    st.write(eval_json_to_markdown(response))

                    # Export button (col1) to save feedback
                    st.download_button("Download Feedback", data = text_response, type = 'primary', 
                                       file_name=f"{doctype} Evaluation {rightnow}.txt")

                    # Celebration animations
                    if response.final_score >= 75:
                        st.balloons()
                    if response.final_score <= 25:
                        st.snow()

                else:
                    if prior is not None:
                        st.title("Prior Feedback:")
                        st.write(prior.replace("`","'"))

    # Converse
    with tab3:
        if doctype is not None:
            viable = True
            prior = None
            # Check for API key
            if openaikey == '':
                viable = False
                st.error('WARNING! You have not loaded an API Key', icon="🚨")
            # Check for document
            docdata = pd.read_sql(f"SELECT id, document, upload_date FROM documents WHERE document_type = '{doctype}' ORDER BY id DESC LIMIT 1",sqlite3.connect(dbpath))
            if len(docdata) == 0:
                viable = False
                st.error(f'WARNING! You have not loaded a {doctype}.', icon="🚨")
            else:
                # Current
                doc_id = int(docdata.iloc[0]['id'])
                doc_dt = docdata.iloc[0]['upload_date']
                doc = docdata.iloc[0]['document']
                doc.replace("`","'")

            # Get feedback
            if viable == True:
                
                st.write(f"Utilizing document from: {doc_dt}")
                    # User initialize conversation
                if st.session_state.user_launched_convo == False:
                    getfeedback = st.button("Start Conversation", type='primary')
                    if getfeedback == True:
                        begin_convo(doc, doctype)

                # Begin conversation
                if st.session_state.user_launched_convo == True:
                    if st.session_state.convo_agent.convo_complete_ == False:
                        # Display entire conversation history
                        for message in st.session_state.messages:
                            with st.chat_message(message["role"]):
                                st.write(message["content"])

                        # Enter user response into conversation
                        if user_response := st.chat_input("What's your response?"):
                            st.session_state.messages.append({"role": "user", "content": user_response})
                            # Generate VC response
                            with st.spinner('VC Agent is typing...'):
                                agent_response = st.session_state.convo_agent.user_response(user_response)                         
                                st.session_state.messages.append({"role": "assistant", "content": agent_response}) 
                            st.rerun()     
                    else: # Convo over, clear everything and reset
                        st.title("The VC has ended the chat!")
                        st.markdown(st.session_state.convo_agent.markdown_)

                        # Store in server
                        rightnow = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
                        scepticism = st.session_state.agent_args['scepticism']
                        temp = st.session_state.agent_args['temperature']                        
                        sqlinsert("""INSERT INTO Performance 
                                (document_type, doc_id, interaction_type, interaction_date, feedback, scepticism, temperature, score, markdown) 
                                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                [doctype, doc_id, 'Conversation', rightnow, st.session_state.convo_agent.feedback_.replace("'","`"), 
                                scepticism, temp, st.session_state.convo_agent.final_score_, st.session_state.convo_agent.markdown_.replace("'","`")],
                                dbpath)

                        # Reset main variables
                        st.session_state.messages = []
                        st.session_state.user_launched_convo = False
                                             
                        # Celebration animations
                        if st.session_state.convo_agent.final_score_ >= 75:
                            st.balloons()
                        if st.session_state.convo_agent.final_score_ <= 25:
                            st.snow()                        
                        st.session_state.convo_agent = None

    # History
    with tab4:
        sql = f"""SELECT interaction_type, rank() OVER(PARTITION BY interaction_type ORDER BY id ASC) AS attempt, score, scepticism, temperature FROM performance ORDER BY interaction_type, attempt"""
        data = pd.read_sql(sql, sqlite3.connect(dbpath))
        if len(data) != 0:
            # Chart
            fig = px.line(data, x="attempt", y="score", color='interaction_type', 
                        title="Performance Through Time", markers = True,
                        color_discrete_map={'Evaluation':'#D0B010','Conversation':'#ffffff'})
            fig.update_layout( xaxis={
                'range': [data['attempt'].min(), data['attempt'].max()], 
                'tickvals': [*range(int(data['attempt'].min()), int(data['attempt'].max())+1)]})        
            st.plotly_chart(fig, use_container_width=True)
            # Data
            st.write("Performance Data")
            st.data_editor(
                data,
                column_config={
                        "score": st.column_config.ProgressColumn("score", help="", format="%f", min_value=0, max_value=100),
                        "scepticism": st.column_config.ProgressColumn("scepticism", help="", format="%f", min_value=0, max_value=1),
                        "temperature": st.column_config.ProgressColumn("temperature", help="", format="%f", min_value=0, max_value=1)},
                hide_index=True)