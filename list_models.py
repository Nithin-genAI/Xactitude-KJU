
import google.generativeai as genai
import os

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

api_key = get_api_key()
if not api_key:
    print("No API Key found.")
else:
    genai.configure(api_key=api_key)
    print("Listing available models...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")
