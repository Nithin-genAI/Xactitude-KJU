"""
Intent Parser Module
Uses Gemini Function Calling to extract structured intent from user queries.
"""

import google.generativeai as genai
import os
import json
from typing import Dict, Optional

# Configure API key (reusing logic from ai_agent.py)
def configure_api():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        try:
            with open('.streamlit/secrets.toml', 'r') as f:
                for line in f:
                    if 'GOOGLE_API_KEY' in line:
                        api_key = line.split('=')[1].strip().strip('"')
                        break
        except:
            pass
    
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

configure_api()

def parse_user_intent(user_query: str) -> Dict:
    """
    Analyzes the user's query to extract structured intent.
    Returns a dictionary with: goal, domain, user_stage, decision_type.
    """
    print(f"🧠 Analyzing intent for: '{user_query}'")
    
    # 1. Define the tool/function signature
    intent_tool = {
        "function_declarations": [
            {
                "name": "log_user_intent",
                "description": "Log the structured intent of the learner based on their query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "goal": {
                            "type": "string",
                            "description": "The specific objective of the user (e.g., 'start a company', 'learn sorting algorithms')."
                        },
                        "domain": {
                            "type": "string",
                            "description": "The broader field or industry (e.g., 'Entrepreneurship', 'Computer Science')."
                        },
                        "user_stage": {
                            "type": "string",
                            "description": "The inferred experience level or life stage (e.g., 'Student', 'Professional', 'Beginner')."
                        },
                        "decision_type": {
                            "type": "string",
                            "description": "The type of help needed (e.g., 'Career Advice', 'Technical Concept', 'Life Decision')."
                        }
                    },
                    "required": ["goal", "domain", "user_stage", "decision_type"]
                }
            }
        ]
    }

    try:
        model = genai.GenerativeModel('gemini-2.5-flash', tools=[intent_tool])
        chat = model.start_chat()
        
        # 2. Force the model to use the tool
        prompt = f"""
        Analyze this user query: "{user_query}"
        
        Extract the underlying intent and call `log_user_intent`.
        Infer the 'user_stage' and 'decision_type' from context if not explicit.
        If vague, make a reasonable guess based on likely intent for a learning platform.
        """
        
        response = chat.send_message(prompt)
        
        # 3. Extract the function call arguments
        if response.candidates[0].content.parts[0].function_call:
            fc = response.candidates[0].content.parts[0].function_call
            intent_data = dict(fc.args)
            print(f"✅ Intent detected: {intent_data}")
            return intent_data
        else:
            print("⚠️ No intent detected (fallback)")
            return {
                "goal": user_query,
                "domain": "General",
                "user_stage": "Unknown",
                "decision_type": "Exploration"
            }
            
    except Exception as e:
        print(f"❌ Error parsing intent: {e}")
        return {
            "goal": user_query,
            "domain": "General", 
            "user_stage": "Unknown",
            "decision_type": "Exploration"
        }

if __name__ == "__main__":
    # Test
    q = "Should I start a startup in college?"
    print(json.dumps(parse_user_intent(q), indent=2))
