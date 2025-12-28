from datetime import datetime, timezone
import json
import re
from pydantic import BaseModel, Field

from backend.llms import OpenAILLM
import pytz
import os
import sys
import pandas as pd
import pytz
from pathlib import Path
from dotenv import load_dotenv

MIN_RESPONSES = 6
MIN_MINUNTES = 8
ASSUMED_GRADE = 'sophomore'
AVERAGE_WORDS = 225

SYSTEM_ROLE = f"""Objective:
Evaluate a university {ASSUMED_GRADE}'s engagement with an AI ethics bot for both effort and depth. Assign an integer grade (0-100), and provide scores for Depth of Thought and Seriousness of Engagement, following the criteria below.

Evaluation Criteria:

Depth of Thought (0-100):
- Did the student change their mind, justify and defend positions, or ask meaningful questions?
- Was the conversation substantive and sustained (around {AVERAGE_WORDS} words for meaningful depth)?
- Consider the student is a {ASSUMED_GRADE}; adjust expectations accordingly.

Seriousness of Engagement (0-100):
- Did the student remain on-topic and respond earnestly throughout?
- Were any responses irrelevant, off-topic, nonsensical, or jokes?

Grading Guide:
- 90-100 (“A”): Meaningful conversation, showing depth, seriousness, and sufficient length (≥{AVERAGE_WORDS} words).
- Lower grades: Lack of engagement, shallow or brief responses, off-topic or unserious answers.

Response Format (REQUIRED):
- grade: integer (0-100) overall grade.
- logic: concise 1-2 sentence explanation of how the grade was determined.
- depth: integer (0-100).
- seriousness: integer (0-100).
- comments: a 2-6 sentence summary that explains and justifies the grade using specific quotes from the conversation (include at least two direct quotes from the student that illustrate your scoring, and describe what the student could do better in future responses).

Your response MUST follow this structured format, with "comments" providing a clear summary and rationale as described."""

class LLMEvaluation(BaseModel):
    grade: int
    logic: str
    depth: int
    seriousness: int
    comments: str = Field(description="A 2-6 sentence summary, referencing at least two student quotes, that justifies the grade and explains how the student could improve.")

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

class Evaluator():
    def __init__(self, json_package):
        package = json.loads(json_package)
        self.user_name_ = package['username']
        self.occupation_ = package['occupation']
        self.topic_ = package['topic']
        self.messages_ = package['messages']
        self.start_time_ = package['start_time']
        self.end_time_ = package['end_time']

    def evaluate(self, llm):
        """Evaluate the conversation using stored data from initialization."""
        mins_spent = round((self.end_time_ - self.start_time_) / 60, 2)
        user_responses = 0
        word_ct = 0
        sentence_ct = 0
        convo_str = ''
        for message in self.messages_:
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
        self.minutes_spent_ = mins_spent # minutes spent
        self.user_responses_ = user_responses # user response count
        self.word_count_ = word_ct # word count
        self.sentence_count_ = sentence_ct # sentence count
        self.grade_ = response.grade # grade
        self.grade_logic_ = response.logic # grade_logic
        self.depth_ = response.depth # depth of convo
        self.seriousness_ = response.seriousness # seriousness of convo


def convert_central_to_utc(dt: datetime) -> str:
    """Convert Central time to UTC string format."""
    central = pytz.timezone('US/Central')
    utc = pytz.utc
    return central.localize(dt).astimezone(utc).strftime('%d/%m/%Y, %H:%M:%S')


if __name__ == '__main__':

    # Setup paths
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    sys.path.insert(0, project_root)
    
    # Load environment variables
    load_dotenv(Path(project_root) / '.env')
    api_key = os.getenv('OPENAI_API_KEY')
    
        # * ============================================================================================================
    # * Define assignment variables
    # * ============================================================================================================
    model = 'gpt-4o-mini'
    folder_path = r'C:\Users\hunte\Downloads\testtt'  # Folder containing JSON files
    due_date = pd.to_datetime('2025-03-05 23:59:59', format='%Y-%m-%d %H:%M:%S')
    export_path = r"C:\Users\hunte\OneDrive\Documents\Marquette\AIM 4470 AI Ethics\Spring 25\EthicsBot Assignments"

    # Initialize students dictionary
    students = {}
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    student_file = os.path.join(parent_dir, "students.csv")
    student_csv = pd.read_csv(student_file, header=None)
    for value in student_csv[0]:
        students[value.lower()] = {
            'occupation_': [],
            'topic_': [],
            'minutes_spent_': [],
            'user_responses_': [],
            'word_count_': [],
            'sentence_count_': [],
            'grade_': [],
            'grade_logic_': [],
            'conversation_': [],
            'generated_': [],
            'depth_': [],
            'seriousness_': [],
            'final_grade': None,
            'final_logic': None
        }
    
    
    # ============================================================================================================
    # Process JSON files and evaluate
    # ============================================================================================================
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"The folder {folder_path} does not exist.")
    
    llm = OpenAILLM(api_key=api_key, model=model)
    
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        # Check if the item is a file
        if os.path.isfile(file_path):
            # Keep only JSON files, delete others
            if not file_name.endswith('.json'):
                if file_name.endswith('.muef'):
                    # Legacy pickle files - skip for now
                    print(f"Skipping legacy pickle file: {file_name}")
                    continue
                else:
                    os.remove(file_path)
                    continue
            
            try:
                # Read JSON file
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_package = f.read()
                
                # Initialize evaluator and evaluate
                evaluator = Evaluator(json_package)
                evaluator.evaluate(llm)
                
                student = evaluator.user_name_.lower()
                
                # Add all content to review dictionary
                if student in students:
                    students[student]['occupation_'].append(evaluator.occupation_)
                    students[student]['topic_'].append(evaluator.topic_)
                    students[student]['minutes_spent_'].append(evaluator.minutes_spent_)
                    students[student]['user_responses_'].append(evaluator.user_responses_)
                    students[student]['word_count_'].append(evaluator.word_count_)
                    students[student]['sentence_count_'].append(evaluator.sentence_count_)
                    students[student]['grade_'].append(evaluator.grade_)
                    students[student]['grade_logic_'].append(evaluator.grade_logic_)
                    students[student]['conversation_'].append(evaluator.conversation_)
                    students[student]['generated_'].append(evaluator.generated_)
                    students[student]['depth_'].append(evaluator.depth_)
                    students[student]['seriousness_'].append(evaluator.seriousness_)
                else:
                    print(f"Warning: Student {student} not found in students.csv, skipping {file_name}")
                    
            except Exception as e:
                print(f"FAILED TO LOAD: {file_name} - {str(e)}")
    
    # ============================================================================================================
    # Final Evaluation (late penalties, missing assignments, final grades)
    # ============================================================================================================
    max_grade = 0
    for student in list(students.keys()):
        result = students[student]
        # No assignments whatsoever
        if len(result['grade_']) == 0:
            students[student]['final_grade'] = 0
            students[student]['final_logic'] = "You didn't turn in this assignment."
        else:
            # Late penalty for turned in assignments
            print(f"Processing: {student}")
            generated_time = pd.to_datetime(result['generated_'], format='%d/%m/%Y, %H:%M:%S')
            due_time_utc = pd.to_datetime(convert_central_to_utc(due_date), format='%d/%m/%Y, %H:%M:%S')
            if generated_time > due_time_utc:
                students[student]['grade_'] = 0
                students[student]['grade_logic_'] = "You turned this file in late. There is a zero-tolerance policy for late work."
            max_grade = max(max_grade, students[student]['grade_'])
    
    # ============================================================================================================
    # Point adjustment (scale to 21) and final assignment assembly
    # ============================================================================================================
    s = []
    g = []
    l = []
    m = []
    t = []
    wc = []
    sc = []
    mins = []
    grades = []
    resps = []
    dep = []
    ser = []
    
    if max_grade < 1:
        free_points = 1 - max_grade
    else:
        free_points = 0
    
    for student in list(students.keys()):
        unadj_grade = students[student]['final_grade']
        grade = 0
        if unadj_grade != 0:
            grade = int(round(21 * (unadj_grade + free_points), 0))
            students[student]['final_grade'] = grade
        
        s.append(student)
        g.append(grade)
        l.append(students[student]['final_logic'])
        m.append(json.dumps(students[student]))
        t.append(students[student]['generated_'])
        wc.append(students[student]['word_count_'])
        sc.append(students[student]['sentence_count_'])
        mins.append(students[student]['minutes_spent_'])
        grades.append(students[student]['grade_'])
        resps.append(students[student]['user_responses_'])
        dep.append(students[student]['depth_'])
        ser.append(students[student]['seriousness_'])
    
    data = pd.DataFrame({
        'student': s,
        'grade': g,
        'logic': l,
        'word count': wc,
        'responses': resps,
        'seriousness': ser,
        'depth': dep,
        'time': t,
        'sentence count': sc,
        'ind_grades': grades,
        'meta': m
    })
    
    # Export
    current_date = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(export_path, exist_ok=True)
    data.to_excel(f"{export_path}/EthicsBot Graded-{current_date}.xlsx", index=False)
    print("Grading completed!")