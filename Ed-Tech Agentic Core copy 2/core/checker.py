import json
import asyncio
from core.structured_client import StructuredClient
from agents.definitions import CheckerAgent
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from core.logger import logger

class CheckerResult(BaseModel):
    status: Literal["PASS", "FAIL", "WARNING"]
    issues: List[str]
    corrected_answer_index: Optional[int]
    feedback: str

class AssignmentChecker:
    def __init__(self, api_key=None, model_name=None):
        self.client = StructuredClient(api_key)
        if model_name:
            self.agent = CheckerAgent(model=model_name)
        else:
            self.agent = CheckerAgent()
        
    async def check_question(self, question_json: dict):
        """
        Checks a single question.
        """
        q_str = json.dumps(question_json, indent=2)
        
        resp, _, _, cost = await self.client.generate_structured(
            response_model=CheckerResult,
            system_prompt=self.agent.get_system_prompt(),
            user_content=self.agent.format_user_prompt(q_str),
            model=self.agent.model
        )
        return resp, cost

    async def check_batch(self, questions: List[dict]):
        """
        Checks a batch of questions in parallel.
        """
        tasks = [self.check_question(q) for q in questions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_report = []
        total_cost = 0.0
        
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Checker failed for Q{i+1}: {res}")
                final_report.append({
                    "index": i+1,
                    "status": "ERROR",
                    "issues": [str(res)],
                    "feedback": "System Error"
                })
            else:
                data, cost = res
                total_cost += cost
                if data:
                    report_item = data.model_dump()
                    report_item["index"] = i+1
                    final_report.append(report_item)
                else:
                     final_report.append({
                        "index": i+1,
                        "status": "ERROR",
                        "issues": ["Model returned None"],
                        "feedback": "System Error"
                    })
                    
        return final_report, total_cost
