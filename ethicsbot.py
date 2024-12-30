from datetime import datetime
import pickle
import time

import pandas as pd
import streamlit as st
# import tiktoken

import frontend.css as css
from backend.llms import OpenAILLM
from backend.evaluation import Evaluator

# ========================================================================================================================
# Set up LLM model
model = 'gpt-4o-mini'
# encoding = tiktoken.encoding_for_model(model)  # Or any other OpenAI model
model_token_lim = 128000

# ========================================================================================================================
# Set up pop up boxes
@st.experimental_dialog("Input Username")
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

# @st.experimental_dialog("Token Limit")
# def token_lim():
#     st.info('Conversation approaching its token limit.', icon="ℹ️")

@st.experimental_dialog("Download Conversation")
def evaluate_and_download():
    # Evaluate
    eval = Evaluator(user_name = st.session_state['username'],
                     occupation = st.session_state['occupation'],
                     topic = st.session_state['topic'])
    with st.spinner('Preparing output...'):
        eval.evaluate(st.session_state['llm'], st.session_state['messages'], st.session_state['start_time'], st.session_state['end_time'])
        # pickle class
        package = pickle.dumps(eval)

    st.text("The file is now ready for download")
    if st.download_button('Download file', package, f'Ethics Convo {datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}.muef'):
        st.balloons()
        st.toast('Hooray! The file has been downloaded.', icon='🎉')

# ========================================================================================================================
# Establish app and session_state variables
st.set_page_config(page_title='⚖️ Ethics Bot', layout='wide')

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

# Check Launch Condition =================================================================================================
if st.session_state['username'] is None:
    get_username()

# ========================================================================================================================
# Build Header and inputs
st.header("⚖️ Marquette University Ethics Bot")
occupation = st.text_input("Please input your planned occupation below (optional)", placeholder="example: AI Engineer")
topic = st.text_input("Please input any special topic that you're interested in (optional)", placeholder="example: use of AI for financial credit approval")
col1, col2, col3, col4 = st.columns([1,1,1,3])

# ========================================================================================================================
# Export
if col3.button("Export Conversation", type='primary'):
    st.session_state['end_time'] = time.time()
    evaluate_and_download()

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

# Begin conversation
if viable == True or st.session_state['user_launched_convo'] == True:

    # # Check token count
    # content = ''
    # for message in st.session_state.messages:
    #     if content == '':
    #         content += message["role"] + message['content']
    #     else:
    #         content += '\n' + message["role"] + message['content']
    # num_token = len(encoding.encode(content))
    # if num_token/model_token_lim >= .8:
    #     token_lim()

    # Generate initial topic
    if st.session_state['user_launched_convo'] == False:
        with st.spinner('Ethics bot is thinking...'):
            if occupation is not None and occupation != '':
                system_role = (f"You are now a university professor of ethics teaching students who will end up working as {occupation}s. "
                               f"Your goal is to create an INCREDIBLY tricky ethical dilemma that they may face in thier future career track. ")
                st.session_state['occupation'] = occupation
            else:
                system_role = f"You are now a university professor of ethics. Your goal is to create an INCREDIBLY tricky ethical dilemma. "
            system_role += (f"The situation you generate should be extremely morally ambiguous with no clear or correct decision, " 
                            f"forcing the student to really contemplate what to do. Avoid situations with binary options. "
                            f"Try to come up with novel scenarios that aren't just 'you are a doctor that must pick between patients'."
                            f"After you present the dilemma, ask the student how they would respond in the situation and why. "
                            f"After the student responds, you will provide new information and/or counterpoints to their logic in an attempt to get them to change their mind. "
                            f"For the rest of the conversation, your goal is to get the student to change their mind. If they do change their mind, " 
                            f"ask them to define what specifically caused their change of mind." 
                            f"You are witty and concise in your responses to the user.")
                # Check for topic
            if topic is not None and topic != '':
                system_role += f"\n\nThe user has a particular interest in {topic}. Please make the initial ethical dilemma revolve around this topic."
                st.session_state['topic'] = topic
            st.session_state['system_role'] = system_role
            # Initialize and hit for base query
            llm = OpenAILLM(openaikey, model = model)
            st.session_state['llm'] = llm
            prompt = "Please generate the initial ethical dilemma."
            response = st.session_state['llm'].query(prompt = prompt, system_role = st.session_state['system_role'])
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state['user_launched_convo'] = True
            st.session_state['start_time'] = time.time()

        # Add to chat log
        with st.chat_message("assistant"):
            st.write(response)        

    # Enter user response into conversation
    if user_response := st.chat_input("What's your response?"):
        st.session_state.messages.append({"role": "user", "content": user_response})
        counter = ("If the response is a follow up question, please provide the detail (but not a suggestion as to what to do) that answers their question."
                   "If it is a true response to the prior output, please provide a strong counter argument against the prior user response and/or add new information to the ethical dilemma "
                   "in an attempt to convince the user to change their mind. Conclude your statement by asking what the user would do in light of your response. "
                   "Make sure that you are logically consistent across your responses, you don't repeat the same arguments over and over, and the retorts against the student "
                   "progressively get harder and harder (that is to say, make the scenario more morally ambiguous as things progress to make them really reconsider their position). "
                   "You are witty and concise in your retort to the user.")
        st.session_state.messages.append({"role": "system", 
                                          "content": counter})

        for message in st.session_state.messages:
            if message["role"].lower().strip() != 'system':
                with st.chat_message(message["role"]):
                    st.write(message["content"])

        # Generate agent response
        with st.spinner('Ethics bot is thinking...'):
            agent_response = st.session_state['llm'].query(prompt = st.session_state.messages, system_role = st.session_state['system_role'])
            st.session_state.messages.append({"role": "assistant", "content": agent_response}) 

        # Add to chat log
        with st.chat_message("assistant"):
            st.write(agent_response)