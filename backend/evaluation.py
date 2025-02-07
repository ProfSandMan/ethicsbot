from datetime import datetime, timezone
import re
from pydantic import BaseModel
import base64

MIN_RESPONSES = 6
MIN_MINUNTES = 8
ASSUMED_GRADE = 'sophomore'
AVERAGE_WORDS = 225

SYSTEM_ROLE = f"""Objective:
Evaluate a university {ASSUMED_GRADE}'s engagement with an AI ethics bot based on their effort and depth of interaction. Assign an integer grade (0-100) with a clear explanation of the grading rationale.

Grading Criteria:

Time Spent:
- Consider the duration of interaction as a proxy for reflection.
- Conversations lasting ≥ {MIN_MINUNTES} minutes are considered high-effort.

Depth of Thought:
- Evaluate whether the student:
  - Changed their mind at any point.
  - Justified and defended their positions.
  - Asked meaningful questions.
  - Sustained a reasonable conversation length until a steady state was reached.
  - A meaningful conversation includes at least {MIN_RESPONSES} substantial responses.
  - A meaningful conversation has roughly {AVERAGE_WORDS} words.
- Recall that the student is only a {ASSUMED_GRADE}, so judge the depth of thought accordingly

Seriousness of Engagement:
- Determine if the student remained on-topic and engaged earnestly.
- Responses should not include irrelevant, nonsensical, or joking remarks. 

Grading Scale:

An 'A' (90-100) is awarded for a meaningful conversation: 
    - "Meaningful" is some combination of ≥ {MIN_MINUNTES} minutes, {MIN_RESPONSES} thoughtful responses, and a word count of ≥ {AVERAGE_WORDS} words.
Lower grades reflect lack of engagement, shallow responses, or insufficient effort.

Response Format:
- Provide an integer grade (0-100).
- Justify the grade with specific observations based on the above criteria.
  - INCLUDE SPECIFIC QUOTES from the student that demonstrate your application of the criteria."""

class LLMEvaluation(BaseModel):
    grade: int
    logic: str

def real_role(role):
    if role == 'assistant':
        return "EthicsBot"
    elif role == 'user':
        return "Student"

def word_count(text: str) -> int:
    while '  ' in text:
        text = text.replace('  ',' ')
    word_count = len(text.split(' '))
    return word_count

def sentence_count(text: str) -> int:
    sentence_count = len(re.findall(r'[.!?;:]+', text))
    return sentence_count

def obfuscate_text(text: str) -> str:
    # Convert string to bytes, then encode to Base64
    encoded_bytes = base64.b64encode(text.encode('utf-8'))
    return encoded_bytes.decode('utf-8')

def deobfuscate_text(obfuscated_text: str) -> str:
    # Decode Base64 back to bytes, then convert to string
    decoded_bytes = base64.b64decode(obfuscated_text.encode('utf-8'))
    return decoded_bytes.decode('utf-8')

class Evaluator():
    def __init__(self, user_name, occupation = None, topic = None):
        self.user_name_ = user_name
        self.occupation_ = occupation
        self.topic_ = topic

    def evaluate(self, llm, conversation, start_time, end_time):
        mins_spent = round((end_time - start_time) / 60, 2)
        user_responses = 0
        word_ct = 0
        sentence_ct = 0
        convo_str = ''
        for message in conversation:
            if message["role"].lower().strip() == 'user':
                user_responses += 1
                word_ct += word_count(message["content"])
                sentence_ct += sentence_count(message["content"])
            if message["role"].lower().strip() != 'system':           
                if convo_str == '':
                    convo_str = real_role(message["role"].lower()) + ":\n" + message["content"]
                else:
                    convo_str += '\n\n' + real_role(message["role"].lower()) + ":\n" + message["content"]

        prompt = (f"The user spent a total of {mins_spent} minutes engaging with the AI bot.\n\n"
                  f"The user responded a total of {user_responses} times to the AI agent.\n\n"
                  f"The user's total word count was {word_ct} words.\n\n"
                  f"The conversation is below:\n\n{convo_str}")

        response = llm.query(prompt = prompt, system_role = SYSTEM_ROLE, response_format = LLMEvaluation)
        
        # Package items
        self.conversation_ = convo_str
        self.generated_ = datetime.now(timezone.utc).strftime('%d/%m/%Y, %H:%M:%S')
        self.ms_ = mins_spent # minutes spent
        self.ur_ = user_responses # user response count
        self.wc_ = word_ct # word count
        self.sc_ = sentence_ct # sentence count
        self.g_ = response.grade # grade
        self.gl_ = obfuscate_text(response.logic) # grade_logic, encoded to prevent .pdf/.docx conversion trick