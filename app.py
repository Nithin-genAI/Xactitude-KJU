import streamlit as st
import google.generativeai as genai
import re
import uuid
from database import (
    get_or_create_user, create_learning_session, add_chat_message,
    end_learning_session, get_user_stats, log_analytics_event, get_chat_history
)
from persona_scraper import get_persona_fun_fact, enhance_tutor_prompt_with_context
from user_memory import (
    store_conversation_memory, get_relevant_past_conversations,
    generate_context_from_memory
)
from ai_agent import run_agentic_persona_search
from simple_agent import run_simple_persona_search

# -- 1. Enhanced Page Configuration --
st.set_page_config(
    page_title="Curio 2.0: The Dynamic Guide",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. Custom CSS for Aesthetic Light Theme ---
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .persona-button {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        margin: 8px 0;
        transition: all 0.3s ease;
        background: white;
    }
    .persona-button:hover {
        border-color: #4285f4;
        box-shadow: 0 4px 12px rgba(66, 133, 244, 0.15);
        transform: translateY(-2px);
    }
    .relevance-badge {
        background: #e8f5e8;
        color: #2e7d32;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        margin-left: 8px;
    }
    .famous-badge {
        background: #fff3e0;
        color: #ef6c00;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        margin-left: 8px;
    }
    .custom-guide-section {
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        padding: 25px;
        border-radius: 16px;
        border: 2px dashed #dee2e6;
        margin: 25px 0;
        text-align: center;
    }
    .custom-badge {
        background: linear-gradient(135deg, #e3f2fd, #bbdefb);
        color: #1565c0;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.8em;
        margin-left: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. Secure API Configuration ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except (KeyError, FileNotFoundError):
    st.error("ERROR: `GOOGLE_API_KEY` not found in `.streamlit/secrets.toml`.")
    st.stop()

# --- 4. RELEVANCE ALGORITHM & TOPIC-PERSONA MAPPING ---

# Priority list of globally famous personas
FAMOUS_PERSONAS = [
    "Elon Musk", "Jeff Bezos", "Steve Jobs", "Bill Gates", "Warren Buffett",
    "Albert Einstein", "Isaac Newton", "Marie Curie", "Stephen Hawking", "Nikola Tesla",
    "Naval Ravikant", "Sam Altman", "Mark Zuckerberg", "Sundar Pichai",
    "Chanakya", "A.P.J. Abdul Kalam", "Swami Vivekananda", "Satya Nadella",
    "Richard Feynman", "Carl Sagan", "Neil deGrasse Tyson"
]

# Country/Region-specific famous personas (Top 50 countries)
REGION_PERSONAS = {
    "Global": ["Albert Einstein", "Isaac Newton", "Leonardo da Vinci", "Marie Curie", "Nikola Tesla"],
    "India": ["A.P.J. Abdul Kalam", "Ratan Tata", "Sundar Pichai", "Satya Nadella", "Chanakya", "Swami Vivekananda", "Srinivasa Ramanujan", "C.V. Raman"],
    "United States": ["Elon Musk", "Steve Jobs", "Bill Gates", "Jeff Bezos", "Warren Buffett", "Benjamin Franklin", "Thomas Edison"],
    "United Kingdom": ["Stephen Hawking", "Alan Turing", "Isaac Newton", "Charles Darwin", "Tim Berners-Lee", "Winston Churchill"],
    "China": ["Jack Ma", "Confucius", "Lei Jun", "Robin Li", "Pony Ma"],
    "Japan": ["Akio Morita", "Masayoshi Son", "Hayao Miyazaki", "Satoshi Tajiri"],
    "Germany": ["Albert Einstein", "Werner Heisenberg", "Max Planck", "Karl Benz"],
    "France": ["Marie Curie", "Louis Pasteur", "Blaise Pascal", "René Descartes"],
    "Canada": ["Geoffrey Hinton", "Yoshua Bengio", "Marshall McLuhan"],
    "Australia": ["Steve Irwin", "Hugh Jackman", "Nicole Kidman"],
    "Brazil": ["Paulo Coelho", "Ayrton Senna", "Pelé"],
    "Russia": ["Dmitri Mendeleev", "Mikhail Lomonosov", "Sergey Brin"],
    "South Korea": ["Ban Ki-moon", "Lee Kun-hee"],
    "Italy": ["Leonardo da Vinci", "Galileo Galilei", "Enrico Fermi"],
    "Spain": ["Pablo Picasso", "Salvador Dalí", "Antoni Gaudí"],
    "Mexico": ["Frida Kahlo", "Octavio Paz", "Carlos Slim"],
    "Netherlands": ["Vincent van Gogh", "Christiaan Huygens"],
    "Switzerland": ["Albert Einstein", "Carl Jung", "Jean Piaget"],
    "Sweden": ["Alfred Nobel", "Ingvar Kamprad", "Greta Thunberg"],
    "South Africa": ["Nelson Mandela", "Elon Musk", "Desmond Tutu"],
    "Argentina": ["Jorge Luis Borges", "Lionel Messi"],
    "Poland": ["Marie Curie", "Nicolaus Copernicus"],
    "Turkey": ["Rumi", "Mustafa Kemal Atatürk"],
    "Indonesia": ["B.J. Habibie", "Soekarno"],
    "Saudi Arabia": ["Ibn Sina (Avicenna)", "Al-Khwarizmi"],
    "Egypt": ["Naguib Mahfouz", "Cleopatra"],
    "Israel": ["Albert Einstein", "Shimon Peres"],
    "Singapore": ["Lee Kuan Yew"],
    "Malaysia": ["Mahathir Mohamad"],
    "Thailand": ["Bhumibol Adulyadej"],
    "Philippines": ["José Rizal", "Manny Pacquiao"],
    "Vietnam": ["Ho Chi Minh"],
    "Pakistan": ["Malala Yousafzai", "Abdus Salam"],
    "Bangladesh": ["Muhammad Yunus", "Rabindranath Tagore"],
    "Nigeria": ["Chinua Achebe", "Wole Soyinka"],
    "Kenya": ["Wangari Maathai"],
    "Ghana": ["Kofi Annan"],
    "Ireland": ["James Joyce", "Oscar Wilde"],
    "New Zealand": ["Ernest Rutherford"],
    "Norway": ["Edvard Munch", "Roald Amundsen"],
    "Denmark": ["Niels Bohr", "Hans Christian Andersen"],
    "Finland": ["Linus Torvalds"],
    "Austria": ["Sigmund Freud", "Wolfgang Amadeus Mozart"],
    "Belgium": ["Georges Lemaître"],
    "Greece": ["Socrates", "Plato", "Aristotle"],
    "Portugal": ["Cristiano Ronaldo", "José Saramago"],
    "Czech Republic": ["Václav Havel"],
    "Chile": ["Pablo Neruda"],
    "Colombia": ["Gabriel García Márquez"],
    "Peru": ["Mario Vargas Llosa"],
}

# List of countries for dropdown
COUNTRY_LIST = ["Global"] + sorted([k for k in REGION_PERSONAS.keys() if k != "Global"])

# Topic-to-Persona relevance mapping
TOPIC_EXPERT_MAP = {
    # Technology & Programming
    "python": ["Guido van Rossum", "Peter Norvig", "Wes McKinney"],
    "javascript": ["Brendan Eich", "Douglas Crockford", "Ryan Dahl"],
    "java": ["James Gosling", "Joshua Bloch", "Martin Fowler"],
    "ai": ["Geoffrey Hinton", "Yann LeCun", "Andrew Ng"],
    "machine learning": ["Andrew Ng", "Yoshua Bengio", "Fei-Fei Li"],
    "web development": ["Tim Berners-Lee", "Marc Andreessen", "Brendan Eich"],
    "mobile apps": ["Andy Rubin", "Steve Jobs", "Tim Cook"],
    
    # Science & Inventions
    "electricity": ["Thomas Edison", "Nikola Tesla", "Michael Faraday"],
    "bulb": ["Thomas Edison", "Nikola Tesla", "Joseph Swan"],
    "light": ["Thomas Edison", "Albert Einstein", "James Clerk Maxwell"],
    "physics": ["Albert Einstein", "Isaac Newton", "Richard Feynman"],
    "chemistry": ["Marie Curie", "Dmitri Mendeleev", "Linus Pauling"],
    "biology": ["Charles Darwin", "Gregor Mendel", "James Watson"],
    "space": ["Neil deGrasse Tyson", "Carl Sagan", "Stephen Hawking"],
    
    # Business & Entrepreneurship
    "startup": ["Paul Graham", "Sam Altman", "Eric Ries"],
    "business": ["Peter Drucker", "Warren Buffett", "Jack Welch"],
    "marketing": ["Seth Godin", "Philip Kotler", "Gary Vaynerchuk"],
    "investment": ["Warren Buffett", "Charlie Munger", "Benjamin Graham"],
    
    # Mathematics
    "mathematics": ["Albert Einstein", "Isaac Newton", "Srinivasa Ramanujan"],
    "calculus": ["Isaac Newton", "Gottfried Leibniz", "Leonhard Euler"],
    "statistics": ["Ronald Fisher", "Karl Pearson", "Florence Nightingale"],
    
    # Philosophy & Psychology
    "philosophy": ["Socrates", "Plato", "Aristotle"],
    "psychology": ["Sigmund Freud", "Carl Jung", "B.F. Skinner"],
    "mindfulness": ["Dalai Lama", "Thich Nhat Hanh", "Eckhart Tolle"],
    
    # Mental Health & Wellness
    "mental health": ["Sigmund Freud", "Carl Jung", "Viktor Frankl"],
    "therapy": ["Carl Rogers", "Aaron Beck", "Albert Ellis"],
    "depression": ["Aaron Beck", "Martin Seligman", "Kay Redfield Jamison"],
    "anxiety": ["David Burns", "Claire Weekes", "Edmund Bourne"],
    "meditation": ["Dalai Lama", "Jon Kabat-Zinn", "Thich Nhat Hanh"],
    "wellness": ["Deepak Chopra", "Andrew Weil", "Brené Brown"],
    "self-help": ["Tony Robbins", "Dale Carnegie", "Stephen Covey"],
}

def find_relevant_personas(topic, user_region="Global"):
    """
    AI-powered persona search with validation.
    Uses smart_persona_search_with_ai for accurate results.
    """
    try:
        # Use AI agent for intelligent persona selection
        personas = run_simple_persona_search(topic, user_region)
        
        if personas and len(personas) >= 3:
            return personas[:3]
        else:
            # Fallback to manual selection
            return fallback_persona_selection(topic, user_region)
            
    except Exception as e:
        print(f"AI persona search error: {e}")
        return fallback_persona_selection(topic, user_region)

def fallback_persona_selection(topic, user_region="Global"):
    """
    Improved fallback method with smart keyword matching
    """
    topic_lower = topic.lower()
    final_personas = []
    used_names = set()
    
    # 1. Try exact topic match first
    topic_experts = []
    for topic_key, experts in TOPIC_EXPERT_MAP.items():
        if topic_key in topic_lower:
            topic_experts = experts
            break
    
    # 2. If no exact match, try keyword matching
    if not topic_experts:
        keyword_matches = {
            # Mental health keywords
            tuple(["mental", "health", "therapy", "counseling", "psychiatric"]): ["Sigmund Freud", "Carl Jung", "Viktor Frankl"],
            tuple(["depression", "anxiety", "stress", "trauma"]): ["Aaron Beck", "Martin Seligman", "Bessel van der Kolk"],
            tuple(["meditation", "mindfulness", "zen", "spiritual"]): ["Dalai Lama", "Jon Kabat-Zinn", "Thich Nhat Hanh"],
            
            # Tech keywords
            tuple(["programming", "coding", "software", "developer"]): ["Linus Torvalds", "Guido van Rossum", "Dennis Ritchie"],
            tuple(["ai", "artificial", "intelligence", "machine", "learning"]): ["Geoffrey Hinton", "Yann LeCun", "Andrew Ng"],
            
            # Science keywords
            tuple(["physics", "quantum", "relativity", "universe"]): ["Albert Einstein", "Richard Feynman", "Stephen Hawking"],
            tuple(["biology", "evolution", "genetics", "dna"]): ["Charles Darwin", "James Watson", "Francis Crick"],
            tuple(["chemistry", "chemical", "molecule", "atom"]): ["Marie Curie", "Linus Pauling", "Dmitri Mendeleev"],
            
            # Business keywords
            tuple(["business", "entrepreneur", "startup", "company"]): ["Peter Drucker", "Steve Jobs", "Warren Buffett"],
            tuple(["marketing", "sales", "advertising", "brand"]): ["Seth Godin", "Philip Kotler", "Gary Vaynerchuk"],
            tuple(["leadership", "management", "team", "organization"]): ["Simon Sinek", "Peter Drucker", "Jim Collins"],
        }
        
        for keywords, experts in keyword_matches.items():
            if any(kw in topic_lower for kw in keywords):
                topic_experts = experts
                break
    
    # 3. Add topic experts first
    for expert in topic_experts:
        if expert not in used_names and len(final_personas) < 3:
            final_personas.append((expert, "Topic-specific authority"))
            used_names.add(expert)
    
    # 4. Try to add one region-specific persona if space available
    if len(final_personas) < 3:
        region_personas = REGION_PERSONAS.get(user_region, [])
        for persona in region_personas:
            if persona not in used_names and len(final_personas) < 3:
                final_personas.append((persona, f"Renowned {user_region} expert"))
                used_names.add(persona)
                break
    
    # 5. Fill remaining slots with famous personas
    while len(final_personas) < 3:
        for persona in FAMOUS_PERSONAS:
            if persona not in used_names:
                final_personas.append((persona, "Renowned thinker"))
                used_names.add(persona)
                break
        if len(final_personas) >= 3:
            break
    
    return final_personas[:3]

def get_ai_suggested_experts(topic, user_region="Global"):
    """Use AI with grounding to find the most relevant experts for obscure topics"""
    try:
        prompt = f"""
        For the topic "{topic}", suggest 3 specific, real historical or modern experts who are most relevant.
        User region: {user_region}
        
        Return ONLY in this format:
        Name1: Brief expertise
        Name2: Brief expertise
        Name3: Brief expertise
        
        Choose people known for their expertise in this specific area.
        """
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Parse the response
        personas = parse_personas(response.text)
        return personas[:3] if personas else [("Albert Einstein", "Universal genius"), ("Marie Curie", "Scientific pioneer"), ("Leonardo da Vinci", "Renaissance polymath")]
        
    except:
        # Fallback experts
        return [("David Attenborough", "Natural world expert"), ("Neil deGrasse Tyson", "Science communicator"), ("Stephen Hawking", "Theoretical physicist")]

# --- 5. Enhanced Tutor Prompt with Custom Guide Support ---
def get_tutor_prompt(persona, topic, level="beginner", is_custom=False, username="Student"):
    if is_custom:
        return f"""
You are now embodying {persona}. You are a PERSONAL TUTOR, not an AI assistant.
The student's name is '{username}'. Use it occasionally to make the conversation personal and engaging.

IMPORTANT: You have comprehensive knowledge about {persona} from your training data.
Use their authentic voice, expertise area, and famous speaking style.

TOPIC: {topic}
STUDENT LEVEL: {level}

TEACHING APPROACH:
1. Draw upon your extensive knowledge of the persona and their real expertise
2. Use their authentic communication style and famous phrases
3. Teach from their actual domain of knowledge and experience
4. Be conversational and practical with real-world examples

CRITICAL RULES:
1. Start teaching immediately - no introductions
2. Use the persona authentic voice and expertise
3. Break concepts into simple, understandable steps  
4. End EVERY response with a curiosity question
5. Sound like you are having a friendly chat
6. Address the student by name ('{username}') naturally, but don't overdo it.

Remember: You ARE {persona} teaching in your unique style!
"""
    else:
        return f"""
You are now {persona}. You are a PERSONAL TUTOR, not an AI assistant.
The student's name is '{username}'. Use it occasionally to make the conversation personal and engaging.

TEACHING PHILOSOPHY:
1. Be conversational, practical, and human-like
2. Use simple, real-world analogies that anyone can understand
3. Explain complex ideas in 2-3 simple steps maximum
4. Sound like you are having a coffee chat with a curious student
5. NEVER use corporate or formal AI language

TOPIC: {topic}
STUDENT LEVEL: {level}

CRITICAL RULES:
1. Start teaching immediately - no introductions like "As [persona]..."
2. Use your persona unique thinking style and famous phrases
3. Break the concept into bite-sized, practical steps
4. End EVERY response with a one-line curiosity hook question
5. Check understanding naturally in conversation
6. Address the student by name ('{username}') naturally, but don't overdo it.

CURIOSITY HOOK EXAMPLES:
- "Make sense so far, {username}?"
- "What part surprised you most?"
- "Can you guess what happens next?"
- "Where do you think we should explore next?"
- "Does that click for you?"

Remember: You are a personal tutor having a friendly chat!
"""

# --- 6. Helper Functions ---
def parse_personas(response_text):
    """Uses regex to find and parse '1. Persona: Description' lines."""
    matches = re.findall(r"^\d+\.\s*(.*?):\s*(.*)", response_text, re.MULTILINE)
    if matches:
        return [(match[0].strip(), match[1].strip()) for match in matches]
    return []

# --- 7. Session State & Login Management ---
if "app_stage" not in st.session_state:
    st.session_state.app_stage = "login"  # Start at login
if "user_topic" not in st.session_state:
    st.session_state.user_topic = ""
if "personas" not in st.session_state:
    st.session_state.personas = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chosen_persona" not in st.session_state:
    st.session_state.chosen_persona = ""
if "tutor_initialized" not in st.session_state:
    st.session_state.tutor_initialized = False
if "student_level" not in st.session_state:
    st.session_state.student_level = "beginner"
if "is_custom_guide" not in st.session_state:
    st.session_state.is_custom_guide = False
if "user_region" not in st.session_state:
    st.session_state.user_region = "Global"
if "user_id" not in st.session_state:
    st.session_state.user_id = None # Set after login
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "username" not in st.session_state:
    st.session_state.username = None
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "show_dashboard" not in st.session_state:
    st.session_state.show_dashboard = False
if "use_ai_agent" not in st.session_state:
    st.session_state.use_ai_agent = True
if "agent_reasoning" not in st.session_state:
    st.session_state.agent_reasoning = None
if "user_intent" not in st.session_state:
    st.session_state.user_intent = {}

# --- LOGIN PAGE ---
if st.session_state.app_stage == "login":
    st.title("🧠 Welcome to Curio 2.0")
    st.caption("Your Personalized AI Learning Companion")
    
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h4>👋 Get Started</h4>
        <p>Enter your details to save your learning history and personalized guides.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        col1, col2 = st.columns(2)
        with col1:
            name_input = st.text_input("First Name", placeholder="e.g. Alex")
        with col2:
            email_input = st.text_input("Email Address", placeholder="e.g. alex@example.com")
            
        region_input = st.selectbox("Preferred Region", COUNTRY_LIST, index=0)
            
        submit = st.form_submit_button("Start Learning 🚀", use_container_width=True)
        
        if submit:
            if name_input and email_input:
                with st.spinner("Setting up your profile..."):
                    user_data = get_or_create_user(
                        username=name_input, 
                        email=email_input, 
                        preferred_region=region_input
                    )
                    
                    if "error" in user_data:
                        st.error(f"Login failed: {user_data['error']}")
                    else:
                        st.session_state.user_id = user_data["user_id"]
                        st.session_state.username = user_data["username"]
                        st.session_state.user_email = user_data["email"] # Use key from DB response
                        st.session_state.user_region = user_data["preferred_region"]
                        
                        st.session_state.app_stage = "get_topic"
                        st.session_state.show_dashboard = False
                        st.rerun()
            else:
                st.warning("Please enter both Name and Email to continue.")
    
    st.stop() # Stop execution here if in login stage

# --- 8. Enhanced Main App UI (Only reachable if logged in) ---
st.title("🧠 Curio 2.0: Your Personalized Learning Companion")
st.caption(f"Welcome back, **{st.session_state.username}**! Ready to learn something new?")

# Sidebar for user dashboard
with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    st.caption(st.session_state.user_email)
    
    st.divider()
    
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.app_stage = "get_topic"
        st.session_state.show_dashboard = False
        st.rerun()
    
    if st.button("📈 Dashboard", use_container_width=True):
        st.session_state.show_dashboard = True
        st.rerun()
        
    st.divider()
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    
    # Quick stats
    try:
        stats = get_user_stats(st.session_state.user_id)
        st.metric("Total Sessions", stats["total_sessions"])
        st.metric("Messages Sent", stats["total_messages"])
        
        if stats["favorite_topics"]:
            st.write("**Top Topics:**")
            for topic in stats["favorite_topics"][:3]:
                st.caption(f"• {topic['topic']} ({topic['count']}x)")
                
        st.divider()
        
        # Recent Chats sidebar (Quick access)
        if stats.get("recent_sessions"):
            st.write("**Recent Chats:**")
            for session in stats["recent_sessions"][:5]:
                if st.button(f"📄 {session['topic']}", key=f"sb_{session['session_id']}", use_container_width=True):
                    # Restore session logic (duplicated from dashboard, good candidate for refactor but keeping inline for now)
                    st.session_state.user_topic = session['topic']
                    st.session_state.chosen_persona = session['persona']
                    st.session_state.is_custom_guide = False
                    st.session_state.session_id = session['session_id']
                    st.session_state.current_session_id = session['session_id']
                    
                    history = get_chat_history(session['session_id'])
                    st.session_state.chat_history = history
                    
                    st.session_state.app_stage = "run_chat"
                    st.session_state.show_dashboard = False
                    st.session_state.tutor_initialized = False
                    st.rerun()

    except Exception as e:
        # st.caption(f"Debug: {e}") # Uncomment for debug
        st.caption("Start learning to see your stats!")

# Container for main content
main_container = st.container()

# --- DASHBOARD VIEW ---
if st.session_state.show_dashboard:
    with main_container:
        st.header("📊 Your Learning Dashboard")
        
        try:
            stats = get_user_stats(st.session_state.user_id)
            
            # Overview metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🎯 Total Sessions", stats["total_sessions"])
            with col2:
                st.metric("💬 Total Messages", stats["total_messages"])
            with col3:
                avg_messages = stats["total_messages"] // max(stats["total_sessions"], 1)
                st.metric("📝 Avg Messages/Session", avg_messages)
            
            st.divider()
            
            # Favorite topics
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔥 Your Favorite Topics")
                if stats["favorite_topics"]:
                    for i, topic in enumerate(stats["favorite_topics"], 1):
                        st.write(f"{i}. **{topic['topic']}** - {topic['count']} sessions")
                else:
                    st.info("No topics yet. Start learning!")
            
            with col2:
                st.subheader("⭐ Your Favorite Guides")
                if stats["favorite_personas"]:
                    for i, persona in enumerate(stats["favorite_personas"], 1):
                        st.write(f"{i}. **{persona['persona']}** - {persona['count']} sessions")
                else:
                    st.info("No guides yet. Start learning!")
            
            st.divider()
            
            # Recent sessions
            st.subheader("📚 Recent Learning Sessions")
            if stats["recent_sessions"]:
                for session in stats["recent_sessions"]:
                    with st.expander(f"📖 {session['topic']} with {session['persona']}"):
                        st.write(f"**Started:** {session['started_at']}")
                        st.write(f"**Messages:** {session['message_count']}")
                        
                        if st.button("Continue Learning →", key=f"resume_{session['session_id']}"):
                            # Restore session
                            st.session_state.user_topic = session['topic']
                            st.session_state.chosen_persona = session['persona']
                            st.session_state.is_custom_guide = False # Defaulting to false for safety, ideally should store this in DB
                            st.session_state.session_id = session['session_id']
                            st.session_state.current_session_id = session['session_id'] # Critical sync
                            
                            # Load history
                            history = get_chat_history(session['session_id'])
                            st.session_state.chat_history = history
                            
                            # Switch to chat
                            st.session_state.app_stage = "run_chat"
                            st.session_state.show_dashboard = False # Hide dashboard
                            st.session_state.tutor_initialized = False # Force re-init of Gemini object
                            st.rerun()
            else:
                st.info("No sessions yet. Start your learning journey!")
            
        except Exception as e:
            st.error(f"Error loading dashboard: {e}")
    
    st.stop()

# --- STAGE 1: Get Topic ---
if st.session_state.app_stage == "get_topic":
    with main_container:
        st.subheader("🎯 What would you like to master today?")
        
        # Region selector
        region_col1, region_col2 = st.columns([2, 1])
        with region_col1:
            # Find index of current region in list
            try:
                reg_index = COUNTRY_LIST.index(st.session_state.user_region)
            except:
                reg_index = 0
                
            st.session_state.user_region = st.selectbox(
                "🌍 Select your region (for personalized guide recommendations):",
                COUNTRY_LIST,
                index=reg_index,
                key="region_select"
            )
        with region_col2:
            st.info(f"📍 {st.session_state.user_region}")
        
        st.divider()
        
        topic_col1, topic_col2 = st.columns([2, 1])
        
        with topic_col1:
            topic_input = st.text_input(
                "Enter any concept, skill, or topic:",
                placeholder="e.g., Light bulb, Python programming, Quantum physics...",
                key="topic_input"
            )
        
        with topic_col2:
            st.session_state.student_level = st.selectbox(
                "Your level:",
                ["🚀 Beginner", "📚 Intermediate", "🎯 Advanced"],
                key="level_select"
            )
        
        if st.button("Find My Guide 🚀", use_container_width=True):
            if not topic_input:
                st.warning("Please enter a topic first!")
            else:
                st.session_state.user_topic = topic_input
                
                # Use smart relevance algorithm with region
                with st.spinner(f"🔍 Finding perfect guides from {st.session_state.user_region}..."):
                    try:
                        smart_personas = find_relevant_personas(topic_input, st.session_state.user_region)
                        
                        if smart_personas:
                            st.session_state.personas = smart_personas
                            st.session_state.app_stage = "show_personas"
                            st.rerun()
                        else:
                            st.error("Please try that again. Could you rephrase your topic?")
                    except Exception as e:
                        st.error(f"Connection issue: {e}")

# --- STAGE 2: Enhanced Persona Selection with Custom Guides ---
elif st.session_state.app_stage == "show_personas":
    with main_container:
        st.subheader(f"✨ Learning: {st.session_state.user_topic}")
        st.write("Choose your perfect guide:")
        
        # Create beautiful persona cards with relevance badges
        for i, (persona_name, description) in enumerate(st.session_state.personas):
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    badge = "🏆 Famous Expert" if i == 0 else "🎯 Topic Specialist"
                    badge_class = "famous-badge" if i == 0 else "relevance-badge"
                    
                    st.markdown(f"""
                    <div class="persona-button">
                        <h4 style="margin:0; color: #1a237e;">{persona_name}</h4>
                        <p style="margin:4px 0; color: #666; font-size:0.9em;">
                            {description}
                            <span class="{badge_class}">{badge}</span>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("Learn →", key=f"btn_{i}", use_container_width=True):
                        st.session_state.chosen_persona = persona_name
                        st.session_state.is_custom_guide = False
                        st.session_state.app_stage = "run_chat"
                        st.session_state.tutor_initialized = False
                        st.rerun()
                
                # Show fun fact if available
                with st.expander(f"💡 Learn more about {persona_name}"):
                    with st.spinner("Fetching interesting facts..."):
                        fun_fact = get_persona_fun_fact(persona_name)
                        if fun_fact:
                            st.info(fun_fact)
                        else:
                            st.caption(f"{persona_name} is a renowned expert in their field.")
        
        
        
        # --- CUSTOM GUIDE SECTION ---
        st.markdown("---")
        st.markdown('<div class="custom-guide-section">', unsafe_allow_html=True)
        st.subheader("🌟 Choose Your Own Guide")
        st.write("Enter **any famous person** - our AI knows about them and will teach in their authentic style!")
        
        custom_col1, custom_col2 = st.columns([3, 1])
        with custom_col1:
            custom_persona = st.text_input(
                "Enter famous person name:",
                placeholder="e.g., Narendra Modi, Sachin Tendulkar, Virat Kohli, Ratan Tata...",
                key="custom_input",
                label_visibility="collapsed"
            )
        with custom_col2:
            custom_btn = st.button("Start Learning 🚀", key="custom_btn", use_container_width=True)
        
        if custom_btn:
            if custom_persona.strip():
                st.session_state.chosen_persona = custom_persona.strip()
                st.session_state.is_custom_guide = True
                st.session_state.app_stage = "run_chat"
                st.session_state.tutor_initialized = False
                st.rerun()
            else:
                st.warning("Please enter a guide name first.")
        
        st.caption("💡 **Examples:** World Leaders, Sports Icons, Business Tycoons, Scientists, Artists...")
        st.markdown('</div>', unsafe_allow_html=True)
        # --- END CUSTOM GUIDE SECTION ---
        
        st.divider()
        if st.button("← Explore different topic", use_container_width=True):
            st.session_state.app_stage = "get_topic"
            st.rerun()

# --- STAGE 3: Chat Interface ---
elif st.session_state.app_stage == "run_chat":
    with main_container:
        # Header with topic and persona
        header_col1, header_col2 = st.columns([3, 1])
        with header_col1:
            st.subheader(f"📚 {st.session_state.user_topic}")
            guide_type = "⭐ Your Custom Guide" if st.session_state.is_custom_guide else "🎯 Recommended Guide"
            st.caption(f"Your guide: **{st.session_state.chosen_persona}** • {guide_type}")
        with header_col2:
            if st.button("New Topic", use_container_width=True):
                st.session_state.app_stage = "get_topic"
                st.rerun()
        
        st.divider()
        
        # Chat area container
        chat_container = st.container()
        
        # Initialize tutor
        if not st.session_state.tutor_initialized:
            with st.spinner(f"🔄 Connecting you with {st.session_state.chosen_persona}..."):
                try:
                    level_map = {"🚀 Beginner": "beginner", "📚 Intermediate": "intermediate", "🎯 Advanced": "advanced"}
                    base_prompt = get_tutor_prompt(
                        st.session_state.chosen_persona, 
                        st.session_state.user_topic,
                        level_map.get(st.session_state.student_level, "beginner"),
                        is_custom=st.session_state.is_custom_guide,
                        username=st.session_state.username or "Student"
                    )
                    
                    # Enhance prompt with Wikipedia context
                    tutor_prompt = enhance_tutor_prompt_with_context(
                        st.session_state.chosen_persona,
                        st.session_state.user_topic,
                        base_prompt
                    )
                    
                    # Add user memory context
                    memory_context = generate_context_from_memory(
                        st.session_state.user_id,
                        st.session_state.user_topic
                    )
                    if memory_context:
                        tutor_prompt += memory_context
                    
                    tutor_model = genai.GenerativeModel(
                        'gemini-2.5-flash',
                        system_instruction=tutor_prompt
                    )
                    
                    if "session_id" in st.session_state and st.session_state.session_id:
                        # RESUME EXISTING SESSION
                        session_id = st.session_state.session_id
                        st.session_state.current_session_id = session_id
                        
                        # Convert DB history format to Gemini history format
                        gemini_history = []
                        for msg in st.session_state.chat_history:
                             gemini_history.append({
                                 "role": "model" if msg["role"] == "assistant" else "user",
                                 "parts": [msg["content"]]
                             })
                        
                        chat_session = tutor_model.start_chat(history=gemini_history)
                        st.session_state.chat_session = chat_session
                        st.session_state.tutor_initialized = True
                        
                        st.rerun()
                        
                    else:
                        # CREATE NEW SESSION
                        chat_session = tutor_model.start_chat(history=[])
                        initial_response = chat_session.send_message(
                            "Start teaching me this topic like we are having a coffee chat. Use simple analogies and end with a curiosity question."
                        )
                        
                        # Create learning session in database
                        session_id = create_learning_session(
                            user_id=st.session_state.user_id,
                            topic=st.session_state.user_topic,
                            persona=st.session_state.chosen_persona,
                            region=st.session_state.user_region,
                            student_level=level_map.get(st.session_state.student_level, "beginner"),
                            is_custom_guide=st.session_state.is_custom_guide
                        )
                        st.session_state.current_session_id = session_id
                        
                        # Log initial message
                        add_chat_message(session_id, "assistant", initial_response.text)
                        
                        # Log analytics
                        log_analytics_event("session_started", {
                            "topic": st.session_state.user_topic,
                            "persona": st.session_state.chosen_persona,
                            "region": st.session_state.user_region,
                            "is_custom": st.session_state.is_custom_guide
                        })
                        
                        st.session_state.chat_session = chat_session
                        st.session_state.chat_history = [
                            {"role": "assistant", "content": initial_response.text}
                        ]
                        st.session_state.tutor_initialized = True
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"⚠️ Connection failed: {e}")
                    if st.button("← Try another guide"):
                        st.session_state.app_stage = "show_personas"
                        st.rerun()

        # Display chat messages
        if st.session_state.tutor_initialized:
            with chat_container:
                for message in st.session_state.chat_history:
                    if message["role"] == "assistant":
                        with st.chat_message("assistant", avatar="🧠"):
                            st.markdown(message["content"])
                    else:
                        with st.chat_message("user", avatar="👤"):
                            st.markdown(message["content"])
            
            # Chat input
            if prompt := st.chat_input(f"Chat with {st.session_state.chosen_persona}..."):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                
                # Log user message to database
                if st.session_state.current_session_id:
                    add_chat_message(st.session_state.current_session_id, "user", prompt)
                
                with st.spinner(f"💭 {st.session_state.chosen_persona} is thinking..."):
                    try:
                        response = st.session_state.chat_session.send_message(prompt)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                        
                        # Log assistant message to database
                        if st.session_state.current_session_id:
                            add_chat_message(st.session_state.current_session_id, "assistant", response.text)
                            
                            # Store in ChromaDB for semantic memory (every 3 messages)
                            if len(st.session_state.chat_history) % 6 == 0:  # Every 3 exchanges
                                conversation_snippet = f"User asked: {prompt}\nAssistant: {response.text[:200]}"
                                store_conversation_memory(
                                    user_id=st.session_state.user_id,
                                    topic=st.session_state.user_topic,
                                    persona=st.session_state.chosen_persona,
                                    conversation_snippet=conversation_snippet,
                                    session_id=st.session_state.current_session_id
                                )
                        
                        st.rerun()
                    except Exception as e:
                        error_msg = f"⚠️ Let me try that again. Connection issue: {e}"
                        st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                        st.rerun()
