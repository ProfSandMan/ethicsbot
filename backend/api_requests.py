from typing import Dict, List

from pydantic import BaseModel


class EvaluationSection(BaseModel):
    section: str
    strengths: str
    weaknesses: str
    improvement_recommendation: str
    section_score: int

class EvalResponseJSON(BaseModel):
    witty_remarks: str
    evaluation: List[EvaluationSection]
    overall_summary: str
    final_score: int

def eval_json_to_markdown(data):
    md = []
    
    # Add witty remarks
    md.append(f"### Initial Remarks\n\n{data.witty_remarks}\n")
    
    # Add evaluation sections
    md.append("### Evaluation\n")
    for idx, section in enumerate(data.evaluation):
        md.append(f"#### Section {idx+1}: {section.section}\n")
        md.append(f"- **Strengths:** {section.strengths}")
        md.append(f"- **Weaknesses:** {section.weaknesses}")
        md.append(f"- **Improvement Recommendation:** {section.improvement_recommendation}")
        md.append(f"- **Section Score:** {section.section_score}\n")
    
    # Add overall summary
    md.append(f"### Overall Summary\n\n{data.overall_summary}\n")
    
    # Add final score
    md.append(f"### Final Score: {data.final_score}\n")
    
    # Join everything into a markdown formatted string
    return "\n".join(md)

def textify(markdown):
    markdown = markdown.replace("### ",'').replace("**",'')
    return markdown

class QuestionsJSON(BaseModel):
    question_log: List[str]

class ConversationJSON(BaseModel):
    score: int
    explanation: str