from datetime import datetime
import json
import time

import pandas as pd
import streamlit as st

import frontend.css as css
from backend.llms import OpenAILLM
from backend.utils import AVATAR, prompt_modifier
from backend.agents import (
    build_scenario_prompt, 
    ScenarioAgent,
    UserClarificationAgent, 
    ScenarioClarificationAgent, 
    RetortAgent, 
    InjectionAttackAgent, 
    ConductorAgent)

version = '1.0.4'
MODEL = 'gpt-4-mini'

# ========================================================================================================================
# Set up pop up boxes
@st.dialog("Input Username")
def get_username():
    # Extract valid emails at inception
    students = pd.read_csv('./students.csv', header=None)[0]
    students = [s.lower() for s in students]    
    tempuser = st.text_input("Please input your Marquette email address below")
    # If launch
    if st.button("Submit", type='primary'):
        # Check to see if valid user
        if tempuser.lower() not in students:
            st.error('This email is not recognized as a student in this class.', icon="🚨")
        else:
            st.session_state['username'] = tempuser.lower()
            st.rerun()

def callback():
    st.session_state['downloaded'] = True
    st.balloons()

@st.dialog("Download Conversation")
def package_and_download():
    # Package
    package = {
        'username': st.session_state['username'],
        'occupation': st.session_state['occupation'],
        'topic': st.session_state['topic'],
        'messages': st.session_state['messages'],
        'start_time': st.session_state['start_time'],
        'end_time': st.session_state['end_time'],
    }
    package = json.dumps(package)
    st.download_button('Download D2L File', package, f'{st.session_state["username"].replace("@marquette.edu", "").replace(".", "-")} {datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}.json',
                        on_click=callback, type='primary')
    # st.download_button('Download Conversation', st.session_state['messages'], 
    #                    f'Ethics Conversation {datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}.txt',
    #                    on_click=callback)

# ========================================================================================================================
# Establish app and session_state variables
st.set_page_config(page_title='⚖️ EthicsBot', layout='wide')

if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_launched_convo" not in st.session_state:
    st.session_state['user_launched_convo'] = False
if "llm" not in st.session_state:
    st.session_state['llm'] = None
if "system_role" not in st.session_state:
    st.session_state['system_role'] = None
if "start_time" not in st.session_state:
    st.session_state['start_time'] = None
if "end_time" not in st.session_state:
    st.session_state['end_time'] = None
if "occupation" not in st.session_state:
    st.session_state['occupation'] = None
if "topic" not in st.session_state:
    st.session_state['topic'] = None
if "downloaded" not in st.session_state:
    st.session_state['downloaded'] = False
if "user_avatar" not in st.session_state:
    st.session_state['user_avatar'] = AVATAR

# ========================================================================================================================
# Sidebar
with st.sidebar:
    # Image
    st.image('./frontend/adv logo.png', use_container_width=True)
    st.markdown(css.hide_img_fs, unsafe_allow_html=True)
    # API Key
    openaikey = st.text_input("OpenAI API Key", placeholder = "Enter your API Key")
    # Note:
    st.write("Oh hey, just so you know, when you close the app, it will retain no memory of your API key or your documents.")
    st.write(f"Version: {version}")    
    # Footer
    st.markdown(css.footer, unsafe_allow_html=True)

# Check Launch Conditions =================================================================================================
if st.session_state['username'] is None:
    get_username()

if st.session_state['downloaded'] == True:
    st.session_state.messages = []
    st.session_state['user_launched_convo'] = False
    st.session_state['downloaded'] = False

# ========================================================================================================================
# Build Header and inputs
st.header("⚖️ ADV EthicsBot")
occupation = st.text_input("Please input your planned occupation below (optional)", placeholder="example: AI Engineer")
topic = st.text_input("Please input any special topic that you're interested in (optional)", placeholder="example: use of AI for financial credit approval")
col1, col2, col3, col4 = st.columns([1,1,1,3])

# ========================================================================================================================
# Export
if col3.button("Export Conversation", type='primary'):
    st.session_state['end_time'] = time.time()
    # Retain conversation in window
    for message in st.session_state.messages:
        if message["role"].lower().strip() != 'system':
            if message["role"] == "user":
                use_avatar = st.session_state['user_avatar']
            else:
                use_avatar = "⚖️"
            with st.chat_message(message["role"], avatar=use_avatar):
                st.write(message["content"])
    package_and_download()

# Reset
if col2.button("Reset Conversation", type='secondary'):
    st.session_state.messages = []
    st.session_state['user_launched_convo'] = False

# Build Conversation
viable = False
if col1.button("Begin Conversation", type='primary'):
    viable = True
    # Check for API key
    if openaikey == '':
        viable = False
        st.error('WARNING! You have not loaded an API Key', icon="🚨")
    else:
        st.session_state['api_key'] = openaikey

# Create llm
if st.session_state['llm'] is None and st.session_state['api_key'] is not None:
    st.session_state['llm'] = OpenAILLM(api_key=openaikey, model = MODEL)

# Begin conversation
if viable == True or st.session_state['user_launched_convo'] == True:

    # Generate initial topic
    if st.session_state['user_launched_convo'] == False:
        with st.spinner('EthicsBot is designing a scenario...'):

            # Build scenario
            st.session_state['occupation'] = occupation
            st.session_state['topic'] = topic
            scenario = build_scenario_prompt(occupation = occupation, topic = topic)
            scenario_agent = ScenarioAgent(llm = st.session_state['llm'])
            scenario_agent.system_prompt_ += prompt_modifier(st.session_state['username'])
            scenario = scenario_agent.respond(scenario)

            st.session_state.messages.append({"role": "assistant", "content": scenario})
            st.session_state['user_launched_convo'] = True
            st.session_state['start_time'] = time.time()

        # Add to chat log
        with st.chat_message("assistant", avatar = "⚖️"):
            st.write(scenario)        

    # Enter user response into conversation
    if user_response := st.chat_input("What's your response?"):
        st.session_state.messages.append({"role": "user", "content": user_response})

        # Select agent
        agent = None
        conductor_agent = ConductorAgent(llm = st.session_state['llm'])
        with st.spinner('EthicsBot is thinking...'):
            agent_id = conductor_agent.select_agent(messages = st.session_state.messages)
        agent_action = ''
        if agent_id == 1:
            agent = UserClarificationAgent(llm = st.session_state['llm'])
            agent_action = "trying to figure out what you mean..."
        elif agent_id == 2:
            agent = ScenarioClarificationAgent(llm = st.session_state['llm'])
            agent_action = "trying to provide more information about the scenario..."
        elif agent_id == 3:
            agent = RetortAgent(llm = st.session_state['llm'])
            agent_action = "retorting..."
        elif agent_id == 4:
            agent = InjectionAttackAgent(llm = st.session_state['llm'])
            agent_action = "skeptical of your response..."
        if agent is not None:
            agent.system_prompt_ += prompt_modifier(st.session_state['username'])

        for message in st.session_state.messages:
            if message["role"].lower().strip() != 'system':
                if message["role"] == "user":
                    use_avatar = st.session_state['user_avatar']
                else:
                    use_avatar = "⚖️"
                with st.chat_message(message["role"], avatar=use_avatar):
                    st.write(message["content"])

        # Generate agent response
        with st.spinner(f'EthicsBot is {agent_action}'):
            agent_response = agent.respond(messages = st.session_state.messages)
            st.session_state.messages.append({"role": "assistant", "content": agent_response}) 

        # Add to chat log
        with st.chat_message("assistant", avatar = "⚖️"):
            st.write(agent_response)