"""
Demo script to test AI Agentic Persona Search
Run this to see the agent in action!
"""

import os
import google.generativeai as genai

# Load API key from secrets file
try:
    with open('.streamlit/secrets.toml', 'r') as f:
        for line in f:
            if 'GOOGLE_API_KEY' in line:
                api_key = line.split('=')[1].strip().strip('"')
                os.environ['GOOGLE_API_KEY'] = api_key
                genai.configure(api_key=api_key)
                print(f"✅ API Key loaded successfully")
                break
except Exception as e:
    print(f"⚠️  Could not load API key: {e}")

from ai_agent import run_agentic_persona_search
import json

def demo_agent():
    print("=" * 60)
    print("🤖 AI AGENTIC PERSONA SEARCH - DEMO")
    print("=" * 60)
    
    import time

    # Test case 1: Mental Health
    print("\n📋 Test 1: Finding experts for 'mental health' in 'Global'")
    print("-" * 60)
    
    result = run_agentic_persona_search("mental health", "Global")
    
    if result.get("status") == "success":
        print(f"\n✅ SUCCESS!")
        print(f"🛠️  Agent made {len(result['agent_steps'])} tool calls")
        
        print("\n🔧 Tools Used:")
        for i, step in enumerate(result['agent_steps'], 1):
            print(f"  {i}. {step['tool']}")
            print(f"     Args: {step['input']}")
        
        print("\n💡 Agent Response:")
        print(result['response'])
        
    else:
        print(f"\n❌ FAILED: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("⏳ Waiting 10 seconds to respect rate limits...")
    time.sleep(10)
    
    # Test case 2: AI
    print("\n📋 Test 2: Finding experts for 'artificial intelligence' in 'India'")
    print("-" * 60)
    
    result2 = run_agentic_persona_search("artificial intelligence", "India")
    
    if result2.get("status") == "success":
        print(f"\n✅ SUCCESS!")
        print(f"🛠️  Agent made {len(result2['agent_steps'])} tool calls")
        
        print("\n🔧 Tools Used:")
        for i, step in enumerate(result2['agent_steps'], 1):
             print(f"  {i}. {step['tool']}")
        
        print("\n💡 Agent Response:")
        print(result2['response'][:300] + "...")
        
    else:
        print(f"\n❌ FAILED: {result2.get('error')}")
    
    print("\n" + "=" * 60)
    print("🎉 Demo Complete!")
    print("=" * 60)

if __name__ == "__main__":
    demo_agent()
