from datetime import datetime
import json
import time

import pandas as pd
import openai
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

version = '1.0.6'
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

# ========================================================================================================================
# Build Header and inputs
st.header("⚖️ ADV EthicsBot")
occupation = st.text_input("Please input your planned occupation below (optional)", placeholder="example: AI Engineer")
topic = st.text_input("Please input any special topic that you're interested in (optional)", placeholder="example: use of AI for financial credit approval")
col1, col2, col3, col4 = st.columns([1,1,1,3])

# ========================================================================================================================
# Export
st.session_state['end_time'] = time.time()
export_package = {
    'username': st.session_state['username'],
    'occupation': st.session_state['occupation'],
    'topic': st.session_state['topic'],
    'messages': st.session_state['messages'],
    'start_time': st.session_state['start_time'],
    'end_time': st.session_state['end_time'],
}
export_json = json.dumps(export_package, indent=2)
if st.session_state["username"] is None:
    username = "unknown"
else:
    username = st.session_state["username"]
download_filename = f'{username.replace("@marquette.edu", "").replace(".", "-")} {datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}.json'

col3.download_button(
    label='Download D2L File',
    data=export_json,
    file_name=download_filename,
    mime='application/json',
    type='primary'
)

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
    st.session_state['llm'] = OpenAILLM(api_key=st.session_state['api_key'], model = MODEL)

# Begin conversation
if viable == True or st.session_state['user_launched_convo'] == True:

    # Generate initial topic
    if st.session_state['user_launched_convo'] == False:
        with st.spinner('EthicsBot is designing a scenario...'):

            # Build scenario
            st.session_state['occupation'] = occupation
            st.session_state['topic'] = topic
            scenario = build_scenario_prompt(occupation = occupation, topic = topic)
            try:
                scenario_agent = ScenarioAgent(llm = st.session_state['llm'])
                scenario_agent.system_prompt_ += prompt_modifier(st.session_state['username'])
                scenario = scenario_agent.respond(scenario)
                st.session_state.messages.append({"role": "assistant", "content": scenario})
                st.session_state['user_launched_convo'] = True
                st.session_state['start_time'] = time.time()

                # Add to chat log
                with st.chat_message("assistant", avatar = "⚖️"):
                    st.write(scenario)       

            except Exception as e:
                # if e is openAI.AuthenticationError, then prompt user to enter API key
                if isinstance(e, openai.AuthenticationError):
                    st.error('WARNING! You have not loaded a valid API Key', icon="🚨")
                if isinstance(e, openai.RateLimitError):
                    st.error('WARNING! You do not have any money loaded to your API key', icon="🚨")
                if isinstance(e, openai.APIError):
                    st.error('WARNING! You have made an API error', icon="🚨")
                if isinstance(e, openai.APIConnectionError):
                    st.error('WARNING! The connection to the API failed', icon="🚨")
                else:
                    st.error('WARNING! An unknown error occurred', icon="🚨")

    # Enter user response into conversation
    if user_response := st.chat_input("What's your response?"):
        st.session_state.messages.append({"role": "user", "content": user_response})

        # Select agent
        try:
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
            else:
                agent = RetortAgent(llm = st.session_state['llm'])
                agent_action = "retorting..."

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
                able_to_respond = False
                for i in range(3):
                    try:
                        agent_response = agent.respond(messages = st.session_state.messages)
                        able_to_respond = True
                        break
                    except:
                        pass
                if able_to_respond == False:
                    agent_response = "I'm sorry, I'm having trouble responding. Please try again."

                st.session_state.messages.append({"role": "assistant", "content": agent_response}) 

            # Add to chat log
            with st.chat_message("assistant", avatar = "⚖️"):
                if agent_response:
                    st.write(agent_response)
                else:
                    st.write("I'm sorry, I'm having trouble responding. Please try again.")

        except Exception as e:
            # if e is openAI.AuthenticationError, then prompt user to enter API key
            if isinstance(e, openai.AuthenticationError):
                st.error('WARNING! You have not loaded a valid API Key', icon="🚨")
            elif isinstance(e, openai.RateLimitError):
                st.error('WARNING! You do not have any money loaded to your API key', icon="🚨")
            elif isinstance(e, openai.APIError):
                st.error('WARNING! You have made an API error', icon="🚨")
            elif isinstance(e, openai.APIConnectionError):
                st.error('WARNING! The connection to the API failed', icon="🚨")
            else:
                st.error('WARNING! An unknown error occurred', icon="🚨")