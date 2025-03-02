from datetime import datetime
import pickle
import time

import pandas as pd
import streamlit as st

import frontend.css as css
from backend.llms import OpenAILLM
from backend.evaluation import Evaluator

version = '1.0.2'

# ========================================================================================================================
# Set up LLM model
model = 'gpt-4o-mini'

# Prompts
INSTR = """Objective:
Create morally ambiguous scenarios with no clear right or wrong choice, compelling students to deeply analyze their decisions.

Guidelines:

- Scenario Characteristics:
  - Ensure dilemmas are highly complex with no binary choices.
  - Avoid overused scenarios like "choosing between patients as a doctor" or "developing a controversial cure."
  - Focus on unique, unconventional, and thought-provoking situations.

  - Interaction Flow:
  - Present the dilemma concisely without any additional context or explanation.
  - Prompt the student to explain their decision and reasoning.
  - Introduce new information or counterarguments aimed at challenging their stance.
  - Continue the discussion with the goal of trying to get the student to reconsider their position.
  - If they change their mind, prompt them to identify what influenced their shift in thinking.

Tone:

  - Keep responses witty, concise, and engaging.
  - Avoid unnecessary elaboration—stay focused on the scenario and dialogue.

Instruction:
Simply present the dilemma without prefacing or adding extra context."""

# PERSONALITY = """You are a playful, witty, and fun master of rhetoric. You are in a debate with a university student regarding an ethical dilemma."""
PERSONALITY = """You are a master debator able to identify flaws in logic and argument structure. You are in a debate with a university student regarding an ethical dilemma."""

RETORT = """Given the provided context, your objective is:
Engage the user in a progressively challenging moral dilemma, responding dynamically based on their input to deepen the ambiguity and complexity of the scenario.

Guidelines for Responses:

If the user asks a follow-up question:
- Provide additional context or details that answer their question.
- Avoid offering suggestions or guidance—focus on increasing moral ambiguity.
- Don't ask additional questions to the user, just provide the context

If the user provides a response to the dilemma:
- Present a strong counterargument that challenges their position OR
- Introduce a SINGULAR new element to further complicate the ethical scenario if their position is very strong and no good counterargument exists.
- Push the user to reconsider their stance with progressively tougher retorts.

If the user response with something totally unrelated:
- Tell the user to take the conversation seriously or you'll leave the conversation

Response Style:
- Be logically consistent throughout the conversation.
- Avoid repeating the same points—each response should escalate the dilemma.
- Responses should become increasingly difficult to defend against, forcing deeper contemplation.
- Keep the responses no longer than a few sentences long.

Tone:
- Remain concise and sharp.
- Keep it engaging and thought-provoking without losing the intellectual challenge.
- Feel free to toss in some emojis in the body (not just the end) of the response where relevant to make the conversation more fun.

Special Instructions:
- If the conversation has reached a steady-state or the student is not contributing anything new to the conversation tell the student you appreciated the conversation, but you without deeper responses, you are going to leave for some funny and exotic reason.
- If the student has engaged for a long time and the conversation has exceeded at least 20 back and forth responses, tell the student you appreciated the conversation and that they did a great job, but you have to leave now for some funnyand exotic reason.
"""

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
def evaluate_and_download():
    # Evaluate
    eval = Evaluator(user_name = st.session_state['username'],
                     occupation = st.session_state['occupation'],
                     topic = st.session_state['topic'])
    with st.spinner('Preparing output...'):
        eval.evaluate(st.session_state['llm'], st.session_state['messages'], st.session_state['start_time'], st.session_state['end_time'])
        # pickle class
        package = pickle.dumps(eval)
        st.session_state['conversation'] = eval.conversation_

    st.download_button('Download D2L File', package, f'Ethics D2L {datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}.muef',
                        on_click=callback, type='primary')
    st.download_button('Download Conversation', st.session_state['conversation'], 
                       f'Ethics Conversation {datetime.now().strftime('%d/%m/%Y, %H:%M:%S')}.txt',
                       on_click=callback)

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

# ========================================================================================================================
# Sidebar
with st.sidebar:
    # Image
    st.image('./frontend/mu logo.png', use_container_width=True)
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
st.header("⚖️ Marquette University EthicsBot")
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
            with st.chat_message(message["role"]):
                st.write(message["content"])
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

    # Generate initial topic
    if st.session_state['user_launched_convo'] == False:
        with st.spinner('EthicsBot is thinking...'):
            if occupation is not None and occupation != '':
                system_role = (f"You are now a university professor of ethics teaching students who will end up working as {occupation}s. "
                               f"Your goal is to create an INCREDIBLY tricky ethical dilemma that they may face in thier future career track. ")
                st.session_state['occupation'] = occupation
            else:
                system_role = f"You are now a university professor of ethics. Your goal is to create an INCREDIBLY tricky ethical dilemma. You are to design an ethical quandary for any career related to corporate finance, high finance, accounting, audit, tax, or being a student."
            system_role += '\n' + INSTR

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
        st.session_state.messages.append({"role": "system", "content": RETORT})

        for message in st.session_state.messages:
            if message["role"].lower().strip() != 'system':
                with st.chat_message(message["role"]):
                    st.write(message["content"])

        # Generate agent response
        with st.spinner('EthicsBot is thinking...'):
            agent_response = st.session_state['llm'].query(prompt = st.session_state.messages, system_role = PERSONALITY)
            st.session_state.messages.append({"role": "assistant", "content": agent_response}) 

        # Add to chat log
        with st.chat_message("assistant"):
            st.write(agent_response)