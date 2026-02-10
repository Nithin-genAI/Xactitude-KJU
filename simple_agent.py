"""
Simplified AI Agent for Persona Search
PURE AI DISCOVERY MODE - No local fallbacks unless absolutely necessary.
"""

import google.generativeai as genai
from typing import List, Tuple
import re
import os

# Configure API key safely
def get_api_key():
    try:
        # Try environment variable
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key: return api_key
        
        # Try secrets file
        with open('.streamlit/secrets.toml', 'r') as f:
            for line in f:
                if 'GOOGLE_API_KEY' in line:
                    return line.split('=')[1].strip().strip('"')
    except:
        pass
    return None

def run_simple_persona_search(topic: str, region: str = "Global") -> List[Tuple[str, str]]:
    """`
    Directly asks Gemini to find the best experts.
    """
    try:
        api_key = get_api_key()
        if api_key:
            genai.configure(api_key=api_key)
        
        import time
        
        # 1. Check local map FIRST (Save API calls + Speed)
        topic_lower = topic.lower()
        candidates = []
        
        # Extended local map for demo safety
        DEMO_MAP = {
            "helicopter shot": ["Mahendra Singh Dhoni", "Hardik Pandya", "Kieron Pollard"],
            "python": ["Guido van Rossum", "Linus Torvalds", "Peter Norvig"],
            "relativity": ["Albert Einstein", "Stephen Hawking", "Richard Feynman"],
            "evolution": ["Charles Darwin", "Richard Dawkins", "Stephen Jay Gould"],
        }
        
        # Check custom demo map with REGION VALIDATION
        # Only use demo map if region is Global or query implies global intent
        if region == "Global":
            for key, experts in DEMO_MAP.items():
                if key in topic_lower:
                    print(f"✅ Found local match for '{key}'")
                    return [(e, f"Expert in {topic}") for e in experts]
        
        # Check standard topic map (if imported, or define here)
        # ...
        
        print(f"🤖 AI AGENT: Searching for experts on '{topic}' in '{region}'...")
        
        models_to_try = [
            'gemini-2.5-flash',
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash'
        ]
        
        response = None
        last_error = None
        
        print(f"🤖 AI AGENT: Searching for experts on '{topic}' in '{region}'...")
        
        for model_name in models_to_try:
            try:
                print(f"   Trying model: {model_name}...")
                model = genai.GenerativeModel(model_name)
                
                prompt = f"""
                Task: You are an expert finder. Identify exactly 3 real, specific people (historical or modern) who are the ABSOLUTE BEST experts to teach the topic: "{topic}".
                
                Context:
                - Topic: {topic}
                - User Region: {region}
                
                Rules:
                1. CRITICAL: If User Region is NOT "Global", you MUST ONLY suggest experts from {region}.
                2. If the region is "{region}", finding someone from {region} is your TOP PRIORITY.
                3. If key terms like "helicopter shot" appear, find the SPECIFIC inventor/legend (e.g., MS Dhoni).
                4. If the topic is broad (e.g., "Physics") and region is "Global", find the biggest names (e.g., Einstein).
                5. Do NOT output generic introductions.
                
                Output Format (Strictly 3 lines):
                Name: Brief description of why they are the expert (one sentence)
                Name: Brief description of why they are the expert (one sentence)
                Name: Brief description of why they are the expert (one sentence)
                """
                
                response = model.generate_content(prompt)
                print(f"✅ SUCCESS with {model_name}")
                break
            except Exception as e:
                print(f"⚠️ Failed with {model_name}: {e}")
                last_error = e
                if "429" in str(e):
                    print("   Rate limit hit. Waiting 2 seconds...")
                    time.sleep(2)
                continue
        
        if not response:
            raise last_error
            
        print(f"🤖 RAW RESPONSE:\n{response.text}")
        
        # Parse
        personas = parse_persona_response(response.text)
        
        if len(personas) >= 3:
            return personas[:3]
            
        print("⚠️ Parsing failed or not enough results. Retrying parsing.")
        
        # Retry with simpler prompt if first failed
        retry_prompt = f"List 3 famous experts for {topic}. Format: Name - Description"
        response = model.generate_content(retry_prompt)
        personas = parse_persona_response(response.text)
        
        if len(personas) >= 1:
            return personas
            
        return fallback_selection(topic)
            
    except Exception as e:
        print(f"❌ AI AGENT ERROR: {e}")
        import traceback
        traceback.print_exc()
        return fallback_selection(topic)


def parse_persona_response(text: str) -> List[Tuple[str, str]]:
    """Robust parsing that handles almost any list format"""
    personas = []
    
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Regex to find "Name" followed by separator and "Description"
        # Matches: "1. Name: Desc", "- Name - Desc", "Name : Desc"
        match = re.search(r'(?P<name>[A-Za-z0-9\.\s\']+?)[:\-\—]\s*(?P<desc>.+)', line)
        
        if match:
            name = match.group('name').strip()
            desc = match.group('desc').strip()
            
            # Clean up leading numbers/bullets from name
            name = re.sub(r'^[\d\-\.\*]+\s*', '', name)
            
            # Skip noise lines
            if len(name) < 2 or "Here" in name:
                continue
                
            personas.append((name, desc))
            
    return personas


def fallback_selection(topic: str) -> List[Tuple[str, str]]:
    """Last resort only"""
    print("⚠️ FAILED TO FIND AI EXPERTS - USING FALLBACK")
    return [
        ("AI Agent Search Failed", "Could not connect to Gemini"),
        ("Try Again", "Please rephrase your topic"),
        ("Albert Einstein", "Default expert")
    ]
