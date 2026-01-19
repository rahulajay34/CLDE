
import pandas as pd
import json
import os

def check_format():
    # 1. Read Template Header
    template_path = "temp - template.csv"
    with open(template_path, "r", encoding="utf-8") as f:
        template_header = f.readline().strip()
    
    # 2. Simulate View Logic
    # Columns from ui/views.py
    cols = ["questionType", "contentType", "contentBody", "intAnswer", "prepTime(in_seconds)", 
            "floatAnswer.max", "floatAnswer.min", "fitbAnswer", "mcscAnswer", "subjectiveAnswer", 
            "option.1", "option.2", "option.3", "option.4", "mcmcAnswer", "tagRelationships", 
            "difficultyLevel", "answerExplanation"]
            
    # Create empty DF
    df = pd.DataFrame(columns=cols)
    
    # Generate CSV header string
    generated_csv = df.to_csv(index=False)
    generated_header = generated_csv.split("\n")[0].strip()
    
    print(f"Template Header:  {template_header}")
    print(f"Generated Header: {generated_header}")
    
    if template_header == generated_header:
        print("✅ Headers Match EXACTLY.")
    else:
        print("❌ Headers DO NOT MATCH.")
        # Find diff
        t_cols = template_header.split(",")
        g_cols = generated_header.split(",")
        
        if len(t_cols) != len(g_cols):
            print(f"Length Mismatch: Temp={len(t_cols)}, Gen={len(g_cols)}")
            
        for i in range(min(len(t_cols), len(g_cols))):
            if t_cols[i] != g_cols[i]:
                print(f"Mismatch at index {i}: Template='{t_cols[i]}' vs Gen='{g_cols[i]}'")

if __name__ == "__main__":
    check_format()
