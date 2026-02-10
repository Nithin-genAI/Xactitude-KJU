"""
AI Agentic Persona Search System
Uses Gemini function calling for intelligent multi-step persona discovery
"""

import google.generativeai as genai
from typing import List, Dict, Optional
import json
import os
import traceback

# Configure API key - standalone version
def configure_api():
    """Configure Gemini API key from environment or secrets file"""
    # Try environment variable first
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        # Try loading from secrets file
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

# Configure on import
configure_api()

# Import existing modules
from persona_scraper import scrape_wikipedia_summary

# REGIONAL PERSONA DATABASE - CRITICAL FOR COUNTRY-WISE FILTERING
REGION_PERSONAS = {
    "India": {
        "Science & Technology": ["Jagadish Chandra Bose", "C.V. Raman", "Vikram Sarabhai", "Homi Bhabha"],
        "Mathematics": ["Srinivasa Ramanujan", "Aryabhata"],
        "Philosophy & Spirituality": ["Ramakrishna Paramahamsa", "Jiddu Krishnamurti", "Swami Vivekananda"],
        "Business & Entrepreneurship": ["Ratan Tata", "Mukesh Ambani", "Narayana Murthy"],
        "Medicine": ["Sushruta", "Charaka"],
        "Literature": ["Rabindranath Tagore", "Premchand"],
        "Politics": ["Mahatma Gandhi", "Jawaharlal Nehru", "Dr. Ambedkar"],
        "Sports": ["Sachin Tendulkar", "Virat Kohli"],
        "Arts": ["Raja Ravi Varma"],
        "Astronomy": ["Aryabhata", "Bhaskara II"],
    },
    "United States": {
        "Science & Technology": ["Albert Einstein", "Isaac Newton", "Stephen Hawking", "Richard Feynman"],
        "Computer Science": ["Alan Turing", "Grace Hopper", "Steve Jobs", "Bill Gates"],
        "Physics": ["Richard Feynman", "J. Robert Oppenheimer", "Enrico Fermi"],
        "Business & Entrepreneurship": ["Warren Buffett", "Elon Musk", "Steve Jobs", "Jeff Bezos"],
        "Literature": ["Mark Twain", "Ernest Hemingway", "F. Scott Fitzgerald"],
        "Medicine": ["Jonas Salk", "Louis Pasteur"],
        "Psychology": ["Carl Rogers", "B.F. Skinner"],
        "Sports": ["Michael Jordan", "Muhammad Ali"],
        "Music": ["Duke Ellington", "Louis Armstrong"],
    },
    "United Kingdom": {
        "Science & Technology": ["Isaac Newton", "Stephen Hawking", "Alan Turing"],
        "Literature": ["William Shakespeare", "Jane Austen", "Charles Dickens"],
        "Physics": ["Michael Faraday", "Paul Dirac"],
        "Medicine": ["Edward Jenner", "Florence Nightingale"],
        "Philosophy": ["David Hume", "Bertrand Russell"],
        "Economics": ["Adam Smith", "John Maynard Keynes"],
        "Biology": ["Charles Darwin", "Joseph Banks"],
    },
    "Germany": {
        "Science & Technology": ["Albert Einstein", "Max Planck", "Werner Heisenberg"],
        "Philosophy": ["Immanuel Kant", "Georg Hegel", "Friedrich Nietzsche"],
        "Music": ["Johann Sebastian Bach", "Ludwig van Beethoven", "Richard Wagner"],
        "Physics": ["Max Born", "Erwin Schrödinger"],
        "Literature": ["Johann Wolfgang von Goethe", "Thomas Mann"],
        "Psychology": ["Sigmund Freud", "Carl Jung"],
    },
    "France": {
        "Science & Technology": ["Pierre Curie", "Marie Curie", "Louis Pasteur"],
        "Philosophy": ["René Descartes", "Jean-Paul Sartre", "Michel Foucault"],
        "Literature": ["Victor Hugo", "Alexandre Dumas", "Marcel Proust"],
        "Mathematics": ["Henri Poincaré", "Évariste Galois"],
        "Art": ["Leonardo da Vinci", "Vincent van Gogh"],
    },
    "Japan": {
        "Science & Technology": ["Yoshiro Nakamatsu", "Akira Yoshino"],
        "Philosophy": ["Masao Abe", "Kitaro Nishida"],
        "Literature": ["Haruki Murakami", "Yasunari Kawabata"],
        "Martial Arts": ["Gichin Funakoshi", "Jigoro Kano"],
        "Art & Design": ["Katsushika Hokusai"],
    },
    "China": {
        "Science & Technology": ["Tu Youyou"],
        "Philosophy": ["Confucius", "Laozi", "Zhuangzi"],
        "Medicine": ["Hua Tuo", "Li Shizhen"],
        "Martial Arts": ["Bruce Lee"],
        "Literature": ["Luo Guanzhong"],
        "Art": ["Zhang Daqian"],
    },
    "Global": {
        "Science & Technology": ["Albert Einstein", "Isaac Newton", "Marie Curie"],
        "Philosophy": ["Plato", "Aristotle", "Socrates"],
        "Business": ["Peter Drucker", "Jack Welch"],
        "Psychology": ["Sigmund Freud", "Carl Jung", "Abraham Maslow"],
        "Economics": ["Adam Smith", "Thomas Piketty"],
    }
}

# TOPIC TO CATEGORY MAPPING
TOPIC_CATEGORY_MAP = {
    "python": "Computer Science",
    "programming": "Computer Science",
    "coding": "Computer Science",
    "web development": "Computer Science",
    "machine learning": "Computer Science",
    "ai": "Computer Science",
    "artificial intelligence": "Computer Science",
    "data science": "Computer Science",
    "physics": "Science & Technology",
    "quantum": "Science & Technology",
    "relativity": "Science & Technology",
    "astronomy": "Astronomy",
    "mathematics": "Mathematics",
    "business": "Business & Entrepreneurship",
    "entrepreneurship": "Business & Entrepreneurship",
    "startup": "Business & Entrepreneurship",
    "psychology": "Psychology",
    "mental health": "Psychology",
    "philosophy": "Philosophy",
    "literature": "Literature",
    "medicine": "Medicine",
    "health": "Medicine",
    "sports": "Sports",
    "music": "Music",
    "art": "Arts",
}


# Tool definitions for Gemini function calling
def search_expert_database(topic: str, region: str = "Global") -> str:
    """
    Search our curated expert database for relevant personas based on TOPIC AND REGION.
    Returns JSON string with list of experts and their relevance.
    """
    print(f"🔍 Searching database for topic='{topic}', region='{region}'")
    
    topic_lower = topic.lower()
    results = []
    
    # Find matching category
    category = None
    for key_phrase, cat in TOPIC_CATEGORY_MAP.items():
        if key_phrase in topic_lower:
            category = cat
            break
    
    if not category:
        category = "Science & Technology"  # Default fallback
    
    print(f"📚 Matched category: {category}")
    
    # Get region's persona list
    region_data = REGION_PERSONAS.get(region, {})
    
    if region == "Global":
        # For Global, search all regions but prioritize diverse sources
        print(f"🌍 Global search - checking all regions")
        for reg, categories in REGION_PERSONAS.items():
            if reg != "Global":
                experts = categories.get(category, [])
                for expert in experts:
                    results.append({
                        "name": expert,
                        "relevance": "high",
                        "source": "regional_database",
                        "region": reg,
                        "category": category,
                        "match_type": "category_match"
                    })
    else:
        # REGIONAL SEARCH - STRICT FILTERING
        print(f"🎯 Regional search - {region} only")
        
        # First priority: Experts from the selected region in matching category
        experts_in_region = region_data.get(category, [])
        for expert in experts_in_region:
            results.append({
                "name": expert,
                "relevance": "high",
                "source": "regional_database",
                "region": region,
                "category": category,
                "match_type": "exact_regional_match",
                "priority": 1
            })
        
        # Second priority: Experts from Global category if region doesn't have experts
        if not results and "Global" in REGION_PERSONAS:
            print(f"⚠️ No experts found in {region} for {category}, checking Global...")
            global_experts = REGION_PERSONAS["Global"].get(category, [])
            for expert in global_experts:
                results.append({
                    "name": expert,
                    "relevance": "medium",
                    "source": "global_fallback",
                    "region": "Global",
                    "category": category,
                    "match_type": "global_fallback",
                    "priority": 2,
                    "note": f"No experts in {region}, using global expert"
                })
    
    print(f"✅ Found {len(results[:10])} experts")
    return json.dumps(results[:10])  # Return top 10


def get_persona_wikipedia_info(persona_name: str) -> str:
    """
    Fetch Wikipedia information about a persona.
    Returns JSON string with bio, expertise, and key facts.
    """
    print(f"📖 Fetching Wikipedia info for {persona_name}")
    try:
        wiki_data = scrape_wikipedia_summary(persona_name)
        
        if wiki_data:
            return json.dumps({
                "name": persona_name,
                "bio": wiki_data.get("bio", ""),
                "key_facts": wiki_data.get("key_facts", {}),
                "source": "wikipedia",
                "found": True
            })
        else:
            return json.dumps({
                "name": persona_name,
                "found": False,
                "error": "Wikipedia page not found or inaccessible"
            })
    except Exception as e:
        print(f"❌ Error fetching Wikipedia: {e}")
        return json.dumps({
            "name": persona_name,
            "found": False,
            "error": str(e)
        })


def validate_persona_expertise(persona_name: str, topic: str, bio: str = "", region: str = "Global") -> str:
    """
    Validate if a persona is genuinely an expert in the given topic.
    Returns JSON string with expertise score (0-100) and reasoning.
    """
    print(f"✔️ Validating expertise: {persona_name} in {topic}")
    try:
        # Use Gemini to analyze expertise
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        region_context = f"\nRegion preference: {region}" if region != "Global" else ""
        
        prompt = f"""
        Analyze if {persona_name} is a genuine expert in "{topic}".{region_context}
        
        Bio: {bio[:500] if bio else "No bio provided"}
        
        Rate their expertise from 0-100 where:
        - 90-100: World-renowned expert, pioneered the field
        - 70-89: Significant contributor, well-known in field
        - 50-69: Knowledgeable, some contributions
        - 30-49: Tangentially related
        - 0-29: Not relevant
        
        Return ONLY a JSON object with no markdown:
        {{
            "score": <number>,
            "reasoning": "<brief explanation>",
            "is_expert": <true/false>
        }}
        """
        
        response = model.generate_content(prompt)
        # Try to extract JSON from response
        text = response.text.strip()
        
        # Remove markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        result = json.loads(text)
        print(f"  Score: {result.get('score', 0)}/100 - {result.get('reasoning', '')}")
        return json.dumps(result)
        
    except Exception as e:
        print(f"❌ Error validating expertise: {e}")
        # Fallback scoring
        return json.dumps({
            "score": 60,
            "reasoning": f"Validation unavailable",
            "is_expert": True
        })


def check_region_match(persona_name: str, region: str) -> str:
    """
    Check if a persona is from the specified region.
    Returns JSON string with match status and details.
    CRITICAL FOR REGION FILTERING
    """
    print(f"🌍 Checking region match: {persona_name} in {region}")
    
    if region == "Global":
        # Global accepts everyone
        return json.dumps({
            "persona": persona_name,
            "region": region,
            "is_from_region": True,
            "regional_bonus": 0,
            "note": "Global region accepts all personas"
        })
    
    # Check if persona is in the specified region
    region_data = REGION_PERSONAS.get(region, {})
    
    is_match = False
    found_category = None
    
    # Search all categories in the region for this persona
    for category, personas in region_data.items():
        if persona_name in personas:
            is_match = True
            found_category = category
            break
    
    result = {
        "persona": persona_name,
        "region": region,
        "is_from_region": is_match,
        "regional_bonus": 20 if is_match else 0,
        "found_in_category": found_category if is_match else None
    }
    
    print(f"  Match: {is_match} | Category: {found_category or 'N/A'}")
    return json.dumps(result)


# Define tools for Gemini function calling
AGENT_TOOLS = [
    {
        "function_declarations": [
            {
                "name": "search_expert_database",
                "description": "Search curated database of experts by topic AND REGION. Critical: Must respect regional filtering!",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The topic to search experts for (e.g., 'Python', 'Physics', 'Business')"
                        },
                        "region": {
                            "type": "string",
                            "description": "The region to search in (e.g., 'India', 'United States', 'Germany', 'Global'). CRITICAL: You MUST use the exact region name provided by the user. Do NOT default to Global unless user specified Global."
                        }
                    },
                    "required": ["topic", "region"]
                }
            },
            {
                "name": "get_persona_wikipedia_info",
                "description": "Fetch detailed Wikipedia information about a specific persona including bio and expertise.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "persona_name": {
                            "type": "string",
                            "description": "Full name of the persona to look up"
                        }
                    },
                    "required": ["persona_name"]
                }
            },
            {
                "name": "validate_persona_expertise",
                "description": "Validate and score a persona's expertise in a specific topic (0-100 scale).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "persona_name": {
                            "type": "string",
                            "description": "Name of the persona to validate"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Topic to validate expertise in"
                        },
                        "bio": {
                            "type": "string",
                            "description": "Optional biography text to help with validation"
                        },
                        "region": {
                            "type": "string",
                            "description": "Region context for validation"
                        }
                    },
                    "required": ["persona_name", "topic"]
                }
            },
            {
                "name": "check_region_match",
                "description": "CRITICAL: Verify if a persona is from the specified region. Use this to filter results!",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "persona_name": {
                            "type": "string",
                            "description": "Name of the persona"
                        },
                        "region": {
                            "type": "string",
                            "description": "Region to check (must match user's selected region exactly)"
                        }
                    },
                    "required": ["persona_name", "region"]
                }
            }
        ]
    }
]


def process_tool_call(tool_name: str, tool_input: Dict) -> str:
    """Process individual tool calls"""
    print(f"\n🛠️  Tool Call: {tool_name}")
    print(f"   Input: {tool_input}")
    
    if tool_name == "search_expert_database":
        return search_expert_database(
            tool_input.get("topic", ""),
            tool_input.get("region", "Global")
        )
    elif tool_name == "get_persona_wikipedia_info":
        return get_persona_wikipedia_info(tool_input.get("persona_name", ""))
    elif tool_name == "validate_persona_expertise":
        return validate_persona_expertise(
            tool_input.get("persona_name", ""),
            tool_input.get("topic", ""),
            tool_input.get("bio", ""),
            tool_input.get("region", "Global")
        )
    elif tool_name == "check_region_match":
        return check_region_match(
            tool_input.get("persona_name", ""),
            tool_input.get("region", "Global")
        )
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def run_agentic_persona_search(topic: str, region: str = "Global") -> Dict:
    """
    Run AI agentic persona search with multi-step reasoning.
    RESPECTS REGION FILTERING - CRITICAL FEATURE
    Returns dict with personas, reasoning chain, and agent steps.
    """
    print("\n" + "="*70)
    print(f"🤖 AGENTIC PERSONA SEARCH")
    print(f"   Topic: {topic}")
    print(f"   Region: {region}")
    print("="*70)
    
    try:
        # Create agent with tools
        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            tools=AGENT_TOOLS
        )
        
        # Start agentic conversation
        chat = model.start_chat()
        
        # Agent prompt - CRITICAL: Emphasize region filtering
        agent_prompt = f"""
You are an expert persona discovery agent. Your task is to find the BEST expert persona for learning about "{topic}".

CRITICAL CONSTRAINTS:
1. USER SELECTED REGION: "{region}"
2. IF REGION IS NOT "Global": ONLY return personas from {region}
3. Do NOT return personas from other regions unless explicitly stated
4. Always check_region_match for final recommendations

PROCESS:
1. First, search_expert_database with topic="{topic}" and region="{region}"
2. For top 3 candidates, get_persona_wikipedia_info to verify credentials
3. validate_persona_expertise for each candidate in this topic
4. check_region_match for final filtering - MUST match selected region!
5. Return top 3 personas with highest scores from {region}

IMPORTANT: If region is "{region}", ensure ALL returned personas are from {region}.
Return personas ONLY from {region} unless it's "Global".
"""
        
        print(f"📝 Agent Prompt: {agent_prompt[:200]}...")
        
        # Send initial request
        response = chat.send_message(agent_prompt)
        
        agent_steps = []
        iteration = 0
        max_iterations = 10
        
        # Agentic loop
        while response.candidates[0].content.parts[0].function_call and iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Iteration {iteration}")
            
            function_call = response.candidates[0].content.parts[0].function_call
            tool_name = function_call.name
            tool_input = dict(function_call.args)
            
            print(f"   Tool: {tool_name}")
            print(f"   Input: {tool_input}")
            
            # Process tool
            tool_result = process_tool_call(tool_name, tool_input)
            
            agent_steps.append({
                "step": iteration,
                "tool": tool_name,
                "input": tool_input,
                "output": tool_result[:500]  # Truncate for logging
            })
            
            # Send tool result back to agent
            response = chat.send_message(
                genai.protos.Content(
                    parts=[
                        genai.protos.Part(text=tool_result)
                    ]
                )
            )
        
        # Extract final response
        final_response_text = response.candidates[0].content.parts[0].text
        print(f"\n✅ Agent completed in {iteration} iterations")
        # print(f"📊 Final Response:\n{final_response_text}")

        # TRICK: The agent might output JSON or just text. We need to handle both.
        # Check if the response is a JSON block
        import re
        personas = []
        try:
            # Try to find JSON block
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', final_response_text, re.DOTALL)
            if json_match:
                personas = json.loads(json_match.group(1))
            else:
                # Try parsing raw list if it looks like JSON
                try:
                    personas = json.loads(final_response_text)
                except:
                    # Fallback: Parse text manually if it's not JSON
                    # Look for "1. Name - Description" format
                    lines = final_response_text.split('\n')
                    for line in lines:
                        if re.search(r'^\d+\.', line.strip()) or line.strip().startswith('-'):
                           # Simple extraction logic
                           parts = line.split(':', 1)
                           if len(parts) == 2:
                               name = re.sub(r'^[\d\-\.\*]+\s*', '', parts[0]).strip()
                               desc = parts[1].strip()
                               personas.append({"name": name, "description": desc})
        except Exception as e:
            print(f"⚠️ Error parsing agent response: {e}")

        # If we found personas, format them for app.py
        # app.py expects list of tuples or list of dicts. Let's standardize to list of tuples for now to match simple_agent?
        # WAIT: app.py code for smart_personas expects:
        # if smart_personas: st.session_state.personas = smart_personas ...
        # logic in app.py (lines 208-210) handle 'personas' as list of tuples [(name, desc), ...] OR simple list.
        # But wait, lines 682: st.session_state.personas = search_result["personas"]
        # And later in "show_personas" (not shown but assumed), it iterates.
        
        # Let's ensure we return a list of tuples like simple_agent does: [(Name, Desc), ...]
        
        final_personas = []
        if isinstance(personas, list):
            for p in personas:
                if isinstance(p, dict):
                    final_personas.append((p.get("name", "Unknown"), p.get("description", "Expert")))
                elif isinstance(p, list) and len(p) >= 2:
                    final_personas.append((p[0], p[1]))
                elif isinstance(p, tuple):
                    final_personas.append(p)
                    
        # Fallback if agent failed to produce structured list
        if not final_personas:
             # Last ditch: simple_agent logic
             from simple_agent import run_simple_persona_search
             final_personas = run_simple_persona_search(topic, region)

        return {
            "status": "success",
            "topic": topic,
            "region": region,
            "personas": final_personas, # Critical: app.py expects this key
            "reasoning": final_response_text,
            "agent_steps": agent_steps,
            "iterations": iteration
        }
        
    except Exception as e:
        print(f"❌ Error in agentic search: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "topic": topic,
            "region": region,
            "error": str(e),
            "agent_steps": []
        }


# Test function
if __name__ == "__main__":
    # Test 1: India search
    print("\n\n" + "="*70)
    print("TEST 1: India Regional Search")
    print("="*70)
    result1 = run_agentic_persona_search("Physics", region="India", intent={"goal": "Learn fundamentals", "user_stage": "Student"})
    print(f"\nResult: {result1['response']}\n")
    
    # Test 2: United States search
    print("\n\n" + "="*70)
    print("TEST 2: United States Regional Search")
    print("="*70)
    result2 = run_agentic_persona_search("Computer Science", region="United States")
    print(f"\nResult: {result2['response']}\n")
    
    # Test 3: Global search
    print("\n\n" + "="*70)
    print("TEST 3: Global Search")
    print("="*70)
    result3 = run_agentic_persona_search("Mathematics", region="Global")
    print(f"\nResult: {result3['response']}\n")