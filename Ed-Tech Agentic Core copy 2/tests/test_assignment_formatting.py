
import unittest
import pandas as pd
import json
from typing import List, Literal
from pydantic import BaseModel, Field

# Mocking the Models (Copy-paste to avoid import issues depending on environment, 
# although importing from core.models is better if path is set up. Let's try import first)
try:
    from core.models import MCSCQuestion, MCMCQuestion, SubjectiveQuestion
except ImportError:
    # Fallback Mock if run outside of package context
    print("Warning: Could not import core.models. Using mock models.")
    class MCSCQuestion(BaseModel):
        question_text: str
        options: List[str]
        correct_option_index: int
        explanation: str
        difficulty: str
        type: Literal["mcsc"] = "mcsc"

    class MCMCQuestion(BaseModel):
        question_text: str
        options: List[str]
        correct_option_indices: List[int]
        explanation: str
        difficulty: str
        type: Literal["mcmc"] = "mcmc"

    class SubjectiveQuestion(BaseModel):
        question_text: str
        model_answer: str
        explanation: str
        difficulty: str
        type: Literal["subjective"] = "subjective"

class TestAssignmentFormatting(unittest.TestCase):
    def test_column_mapping(self):
        # 1. Create Sample Data
        q1 = MCSCQuestion(
            question_text="What is 2+2?",
            options=["1", "2", "3", "4"],
            correct_option_index=4,
            explanation="Math.",
            difficulty="Easy"
        )
        
        q2 = MCMCQuestion(
            question_text="Select even numbers",
            options=["1", "2", "3", "4"],
            correct_option_indices=[2, 4],
            explanation="Divisible by 2.",
            difficulty="Medium"
        )
        
        q3 = SubjectiveQuestion(
            question_text="Explain AI.",
            model_answer="AI is cool.",
            explanation="Basic def.",
            difficulty="Hard"
        )
        
        # 2. Serialize (Simulating Orchestrators output)
        data = [q1.model_dump(), q2.model_dump(), q3.model_dump()]
        
        # 3. Apply View Logic (Simulated from views.py)
        rows = []
        for q in data:
            q_type = q.get("type", "mcsc")
            row = {
                "questionType": q_type,
                "contentType": "markdown",
                "contentBody": q.get("question_text", ""),
                "intAnswer": "",
                "prepTime(in_seconds)": "",
                "floatAnswer.max": "",
                "floatAnswer.min": "",
                "fitbAnswer": "",
                "mcscAnswer": "",
                "subjectiveAnswer": "",
                "option.1": "",
                "option.2": "",
                "option.3": "",
                "option.4": "",
                "mcmcAnswer": "",
                "tagRelationships": "",
                "difficultyLevel": q.get("difficulty", "Medium"),
                "answerExplanation": q.get("explanation", "")
            }
            
            if q_type == "mcsc":
                opts = q.get("options", [])
                for i, opt in enumerate(opts):
                    if i < 4:
                        row[f"option.{i+1}"] = opt
                row["mcscAnswer"] = q.get("correct_option_index", "")
                
            elif q_type == "mcmc":
                opts = q.get("options", [])
                for i, opt in enumerate(opts):
                    if i < 4:
                        row[f"option.{i+1}"] = opt
                indices = q.get("correct_option_indices", [])
                if isinstance(indices, list):
                    row["mcmcAnswer"] = ", ".join(map(str, indices))
                else:
                    row["mcmcAnswer"] = str(indices)
                    
            elif q_type == "subjective":
                row["subjectiveAnswer"] = q.get("model_answer", "")
            
            rows.append(row)
            
        df = pd.DataFrame(rows)
        
        cols = ["questionType", "contentType", "contentBody", "intAnswer", "prepTime(in_seconds)", 
                "floatAnswer.max", "floatAnswer.min", "fitbAnswer", "mcscAnswer", "subjectiveAnswer", 
                "option.1", "option.2", "option.3", "option.4", "mcmcAnswer", "tagRelationships", 
                "difficultyLevel", "answerExplanation"]
        
        # Add missing
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        df = df[cols]
        
        # 4. Assertions
        print("\nGenerated DataFrame:")
        print(df[["questionType", "mcscAnswer", "mcmcAnswer", "subjectiveAnswer"]])
        
        # Row 1: MCSC
        self.assertEqual(df.iloc[0]["questionType"], "mcsc")
        self.assertEqual(str(df.iloc[0]["mcscAnswer"]), "4")
        self.assertEqual(df.iloc[0]["mcmcAnswer"], "")
        
        # Row 2: MCMC
        self.assertEqual(df.iloc[1]["questionType"], "mcmc")
        self.assertEqual(str(df.iloc[1]["mcmcAnswer"]), "2, 4")
        self.assertEqual(df.iloc[1]["mcscAnswer"], "")
        
        # Row 3: Subjective
        self.assertEqual(df.iloc[2]["questionType"], "subjective")
        self.assertEqual(df.iloc[2]["subjectiveAnswer"], "AI is cool.")
        self.assertEqual(df.iloc[2]["mcscAnswer"], "")

if __name__ == "__main__":
    unittest.main()
