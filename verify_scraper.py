
from persona_scraper import get_persona_fun_fact, enhance_tutor_prompt_with_context

persona = "Mahendra Singh Dhoni"
topic = "Helicopter Shot"
prompt = "Teach me cricket."

print(f"🔍 Testing Scraper for: {persona}...")

# 1. Test Fun Fact
fact = get_persona_fun_fact(persona)
print(f"\n✅ Fun Fact Retrieved:\n{fact}")

# 2. Test Context Enhancement
enhanced_prompt = enhance_tutor_prompt_with_context(persona, topic, prompt)
print(f"\n✅ Enhanced Prompt Context (First 500 chars):\n{enhanced_prompt[:500]}...")
