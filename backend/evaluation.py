from datetime import datetime

from pydantic import BaseModel


class LLMEvaluation(BaseModel):
    grade: int
    logic: str

def real_role(role):
    if role == 'assistant':
        return "AI Chatbot"
    elif role == 'user':
        return "Student"

class Evaluator():
    def __init__(self, user_name, occupation = None, topic = None):
        self.user_name_ = user_name
        self.occupation_ = occupation
        self.topic_ = topic

    def evaluate(self, llm, conversation, start_time, end_time):
        system_role = ("You are an ethics professor grading an assignment for sophomore undergraduate students. "
                       "The student assignment was to interact with an AI bot that specializes in presenting ethical dilemmas. "
                       "You are grading the assignment based on how much effort it appeared the student put into the conversation with the AI. "
                       "You are to grade the assignment based on how long the student spent interacting with the agent (a proxy for how long they thought through the problem), "
                       "how much thought went into the student's responses (Did they ever change their mind? Did they justify and defend their positions?, "
                       "Did they ask questions? Did they carry on a resonable length conversation until a sort of steady state was reached? etc.), and "
                       "whether the student appeared to take the conversation seriously (i.e. they didn't respond with non-sensical, irrelevant, or joke responses). "
                       "A conversation of >= 10 minutes and/or a MEANINGFUL conversation with at least 5 responses is 'A' worthy. "
                       "You are to evaluate all of the above and return an integer grade between 0 and 100, and you must include your logic for why you gave the grade you did.")
        
        mins_spent = round((end_time - start_time) / 60, 2)
        user_responses = 0
        convo_str = ''
        for message in conversation:
            if message["role"].lower().strip() == 'user':
                user_responses += 1
            if message["role"].lower().strip() != 'system':           
                if convo_str == '':
                    convo_str = real_role(message["role"].lower()) + ": " + message["content"]
                else:
                    convo_str += '\n\n' + real_role(message["role"].lower()) + ": " + message["content"]

        prompt = (f"The user spent a total of {mins_spent}n minutes engaging with the AI bot.\n\n"
                  f"The user responded a total of {user_responses} times to the AI agent.\n\n"
                  f"The conversation is below:\n\n{convo_str}")

        response = llm.query(prompt = prompt, system_role = system_role, response_format = LLMEvaluation)
        
        # Package items
        self.minutes_spent_ = mins_spent
        self.user_responses_ = user_responses
        self.grade_ = response.grade
        self.grade_logic_ = response.logic
        self.conversation_ = conversation
        self.generated_ = datetime.now().strftime('%d/%m/%Y, %H:%M:%S')