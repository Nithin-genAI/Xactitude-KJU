import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Optional
import google.generativeai as genai
import os

def get_api_key():
    try:
        # Try environment variable
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key and api_key.startswith("AI"): return api_key
        
        # Try secrets file
        secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit/secrets.toml")
        if os.path.exists(secrets_path):
            with open(secrets_path, 'r') as f:
                for line in f:
                    if 'GOOGLE_API_KEY' in line:
                        return line.split('=')[1].strip().strip('"')
    except:
        pass
    return None

# Configure Gemini
api_key = get_api_key()
if api_key:
    genai.configure(api_key=api_key)

def scrape_wikipedia_summary(persona_name: str) -> Optional[Dict]:
    """
    Scrape Wikipedia for persona summary and key facts
    Returns: Dict with bio, quotes, and key facts
    """
    try:
        # Clean persona name for Wikipedia search
        search_name = persona_name.replace(" ", "_")
        url = f"https://en.wikipedia.org/wiki/{search_name}"
        
        # Make request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return None
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get first few paragraphs (intro)
        paragraphs = soup.find_all('p', limit=5)
        bio_text = ""
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50:  # Skip very short paragraphs
                bio_text += text + " "
                if len(bio_text) > 500:  # Get about 500 chars
                    break
        
        # Clean up bio
        bio_text = re.sub(r'\[\d+\]', '', bio_text)  # Remove citation numbers
        bio_text = bio_text[:600]  # Limit length
        
        # Get infobox data (birth, death, occupation, etc.)
        infobox = soup.find('table', class_='infobox')
        key_facts = {}
        image_url = None
        
        if infobox:
            # 1. Try to find the image
            image_tag = infobox.find('img')
            if image_tag:
                image_src = image_tag.get('src')
                if image_src:
                    if image_src.startswith('//'):
                        image_url = "https:" + image_src
                    else:
                        image_url = image_src
            
            # 2. Extract key facts
            rows = infobox.find_all('tr')
            for row in rows:
                header = row.find('th')
                data = row.find('td')
                if header and data:
                    key = header.get_text().strip()
                    value = data.get_text().strip()
                    if key in ['Born', 'Died', 'Occupation', 'Known for', 'Education']:
                        key_facts[key] = value[:100]  # Limit length
        
        return {
            "name": persona_name,
            "bio": bio_text.strip(),
            "key_facts": key_facts,
            "image_url": image_url, # Added field
            "source": "Wikipedia"
        }
        
    except Exception as e:
        print(f"Wikipedia scraping error for {persona_name}: {e}")
        return None

def get_persona_context_with_gemini(persona_name: str, topic: str) -> str:
    """
    Use Gemini with grounding to get accurate persona context
    """
    try:
        # First try Wikipedia scraping
        wiki_data = scrape_wikipedia_summary(persona_name)
        
        # Use Gemini to create enhanced context
        prompt = f"""
        Create a brief, accurate profile for {persona_name} to help them teach about {topic}.
        
        Include:
        1. Their main expertise and achievements (2-3 sentences)
        2. Their teaching/communication style
        3. 1-2 famous quotes or sayings (if applicable)
        
        {f"Wikipedia data: {wiki_data['bio'][:300]}" if wiki_data else ""}
        
        Keep it concise (max 150 words) and factual.
        """
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        return response.text.strip()
        
    except Exception as e:
        print(f"Error getting persona context: {e}")
        return f"{persona_name} is a renowned expert in their field."

def enhance_tutor_prompt_with_context(persona_name: str, topic: str, base_prompt: str) -> str:
    """
    Enhances the base tutor prompt with Wikipedia knowledge about the persona.
    """
    data = scrape_wikipedia_summary(persona_name)
    
    if not data:
        return base_prompt
        
    context = f"""
    PERSONA CONTEXT (Use this to inform your teaching style):
    {persona_name} is a renowned expert in their field.
    
    Key Achievements & Background:
    {data.get('summary', 'No summary available.')}
    
    """
    
    # Optional: Use Gemini to summarize the style if we have the quota
    try:
        models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash-exp', 'gemini-1.5-flash']
        
        style_prompt = f"Based on this summary of {persona_name}, describe their specific communication style and personality in 2 sentences: {data.get('summary')[:1000]}"
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(style_prompt)
                context += f"\nCommunication Style Guide:\n{response.text}\n"
                break # Success
            except Exception as e:
                if "429" in str(e):
                    time.sleep(2)
                    continue
                else:
                    break # Other error, don't retry
                    
    except Exception as e:
        print(f"Error getting persona context: {e}")
        
    return context + f"\nRemember to embody {persona_name}'s authentic expertise and communication style!\n\n{base_prompt}"

def get_persona_fun_fact(persona_name: str) -> Optional[str]:
    """
    Get an interesting fun fact about the persona
    """
    try:
        wiki_data = scrape_wikipedia_summary(persona_name)
        
        if not wiki_data:
            return None
        
        # Use Gemini to extract a fun fact
        prompt = f"""
        From this Wikipedia bio about {persona_name}, extract ONE interesting, lesser-known fun fact.
        
        Bio: {wiki_data['bio']}
        
        Return ONLY the fun fact in one sentence, starting with "Did you know?"
        """
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        return response.text.strip()
        
    except:
        return None

def enhance_tutor_prompt_with_context(persona_name: str, topic: str, base_prompt: str) -> str:
    """
    Enhance the tutor prompt with real persona context from Wikipedia
    """
    try:
        context = get_persona_context_with_gemini(persona_name, topic)
        
        enhanced_prompt = f"""
{base_prompt}

PERSONA CONTEXT (Use this to inform your teaching style):
{context}

Remember to embody {persona_name}'s authentic expertise and communication style!
"""
        return enhanced_prompt
        
    except:
        return base_prompt

def get_persona_image_url(persona_name: str) -> str:
    """
    Get a robust image URL for the persona.
    1. Try Wikipedia (high quality)
    2. Fallback to UI Avatars (reliable, personalized)
    """
    try:
        # 1. Try Wikipedia
        data = scrape_wikipedia_summary(persona_name)
        if data and data.get('image_url'):
            return data['image_url']
            
    except Exception as e:
        print(f"Error fetching image for {persona_name}: {e}")
        
    # 2. Fallback to UI Avatars
    # Generates a nice SVG/PNG with initials
    clean_name = persona_name.replace(" ", "+")
    return f"https://ui-avatars.com/api/?name={clean_name}&background=random&size=200&bold=true"
