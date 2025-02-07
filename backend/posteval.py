import os
from datetime import datetime
import pickle
import json
import pandas as pd
import sys
from pydantic import BaseModel
from ethicsbot.backend.llms import OpenAILLM
from ethicsbot.backend.evaluation import deobfuscate_text, obfuscate_text
from dotenv import load_dotenv
from pathlib import Path
import pytz

# BS to get pickle to unload
current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

# Retrieve the OpenAI API key
load_dotenv(Path(project_root + '/.env'))
api_key = os.getenv('OPENAI_API_KEY')
model = 'gpt-4o-mini'

# $ Support
class FinalEvaluation(BaseModel):
    positive_feedback: str
    reason_points_lost: str
    ideas_for_improvement: str

def append_text(oldtext, newtext):
    if newtext is None:
        return oldtext
    if oldtext == '':
        return newtext
    else:
        return oldtext + '\n\n' + newtext
    
def convert_central_to_utc(dt: datetime) -> datetime:
    central = pytz.timezone('US/Central')
    utc = pytz.utc
    return central.localize(dt).astimezone(utc).strftime('%d/%m/%Y, %H:%M:%S')

# *============================================================================================================
# * Define assignment variables
folder_path = r'C:\Users\hunte\Downloads\EthicsBot 6 Download Feb 6, 2025 701 PM'
due_date = pd.to_datetime('2025-02-05 23:59:59', format='%Y-%m-%d %H:%M:%S')
# *============================================================================================================

export_path = r"C:\Users\hunte\OneDrive\Documents\Marquette\AIM 4470 AI Ethics\Spring 25\EthicsBot Assignments"

# $ Define additional variables
students = {}
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
student_file = os.path.join(parent_dir, "students.csv")
student_csv = pd.read_csv(student_file, header=None)
for value in student_csv[0]:
    students[value.lower()] = {'occupation_':[],
                               'topic_':[],
                               'minutes_spent_':[],
                               'user_responses_':[],
                               'word_count_':[],
                               'sentence_count_':[],
                               'grade_':[],
                               'grade_logic_':[],
                               'conversation_':[],
                               'generated_':[],
                               'final_grade':None,
                               'final_logic':None}

# unmask map (from evaluator keys which had to be semi-obfuscated)
unmask = {'occupation_':'occupation_',
          'topic_':'topic_',
          'ms_': 'minutes_spent_',
          'ur_': 'user_responses_',
          'wc_': 'word_count_',
          'sc_': 'sentence_count_',
          'g_': 'grade_',
          'gl_': 'grade_logic_',
          'conversation_':'conversation_',
          'generated_':'generated_'}

SYSTEM_ROLE = """Role:
You're an ethics professor giving feedback on a recently submitted assignment. The assignment was divided into three parts, each graded using the same criteria. You've already assessed the work and taken notes on why students received their respective scores.

Objective:
Use the provided grading notes to deliver personalized, second-person feedback to students. Keep the tone casual and conversational—like a natural human, not a robotic AI.
Explain to the students through the use of THEIR OWN QUOTES why the earned their grade, especially for where they got points off.

Guidelines:
- Avoid referencing:
  - Specific grade values.
  - Terms like “final defense” or “final thought” (treat it as an ongoing conversation rather than something requiring a formal conclusion).
  - The pronouns “I” or “we.”
  - MOST IMPORTANTLY, don't talk about the time requirement.

- Feedback structure:
  - Highlight positives where applicable; if none, return None.
  - Mention areas where points were lost with clear explanations; if none, return None.
  - Provide suggestions for improvement; if none, return None.
  - MOST IMPORTANTLY, pull specific quotes (if they exist) to help point out to the student why they earned the grades they did.

- Tone:
  - Be concise, direct, and supportive.
  - Keep it short and natural."""

# $ Extraction
if not os.path.exists(folder_path):
    raise FileNotFoundError(f"The folder {folder_path} does not exist.")
for file_name in os.listdir(folder_path):
    file_path = os.path.join(folder_path, file_name)
    # Check if the item is a file
    if os.path.isfile(file_path):
        # Keep '.muef' files, delete others
        if not file_name.endswith('.muef'):
            os.remove(file_path)
        else:
            # Unpickle the file
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            student = data.user_name_
            # Add all content to review dictionary
            data = data.__dict__
            for k in list(data.keys()):
                if unmask.get(k) in list(students[student].keys()):
                    students[student][unmask.get(k)].append(data[k])

# $ Final Evaluation
max_grade = 0
for student in list(students.keys()):
    result = students[student]
    # No assignments whatsoever
    if len(result['grade_']) == 0:
        students[student]['final_grade'] = 0
        students[student]['final_logic'] = "You didn't turn in this assignment."   
    else:
        assignments = len(result['grade_']) 
        if assignments > 3:
            raise Exception(f'WARNING!: {assignments} files found for {student}')

        # Late penalty for turned in assignments
        print("Grading: " + student)
        for i, convo in enumerate(result['conversation_']):
            if pd.to_datetime(result['generated_'][i], 
                              format='%d/%m/%Y, %H:%M:%S') > pd.to_datetime(convert_central_to_utc(due_date), 
                                                                            format='%d/%m/%Y, %H:%M:%S'):
                students[student]['grade_'][i] = 0
                students[student]['grade_logic_'][i] = obfuscate_text("You turned this file in late. There is a zero-tolerance policy for late work.")
            
        # Partial assignment
        if assignments < 3:
            delta = 3 - assignments
            for i in range(0, delta):
                students[student]['grade_'].append(0)
                students[student]['grade_logic_'].append(obfuscate_text("You didn't turn in this assignment."))      

        # Generate final summary
        students[student]['grade_logic_'] = [deobfuscate_text(logic) for logic in students[student]['grade_logic_']]
        context = {'grades':students[student]['grade_'],
                   'grade_logic':students[student]['grade_logic_']}
        context = json.dumps(context)
        llm = OpenAILLM(api_key, model = model)
        response = llm.query(prompt = context, system_role = SYSTEM_ROLE, response_format = FinalEvaluation)
        feedback = append_text('', response.positive_feedback)
        #  feedback = append_text(feedback, response.reason_points_lost) # REMOVED: with curve, this could get washed
        feedback = append_text(feedback, response.ideas_for_improvement)
        students[student]['final_logic'] = feedback
        grade = sum(students[student]['grade_'])/300
        students[student]['final_grade'] = grade
        if grade > max_grade:
            max_grade = grade

# $ Point adjustment (scale to 21) and final assignment assembly
s = []
g = []
l = []
m = []
# t = []
wc = []
sc = []
mins = []
grades = []
resps = []
if max_grade < 1:
    free_points = 1 - max_grade
else:
    free_points = 0
for student in list(students.keys()):
    unadj_grade = students[student]['final_grade']
    grade = 0
    if unadj_grade != 0:
        grade = int(round(21*(unadj_grade + free_points), 0))
        students[student]['final_grade'] = grade
    s.append(student)
    g.append(grade)
    l.append(students[student]['final_logic'])
    m.append(json.dumps(students[student]))
    # t.append(students[student]['generated_'])
    wc.append(students[student]['word_count_'])
    sc.append(students[student]['sentence_count_'])
    mins.append(students[student]['minutes_spent_'])
    grades.append(students[student]['grade_'])
    resps.append(students[student]['user_responses_'])

data = pd.DataFrame({'student':s, 'grade':g, 'ind_grades':grades, 'logic':l, 
                    #  'time':t,
                     'word count':wc, 'sentence count':sc, 'responses': resps,
                     'meta':m})

# Export
current_date = datetime.now().strftime("%Y-%m-%d")
data.to_excel(f"{export_path}/EthicsBot Graded-{current_date}.xlsx", index=False)
print("Grading completed!")