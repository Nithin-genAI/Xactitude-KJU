"""
Query Rewriter Module
Lightweight module to rewrite user queries for high-signal semantic retrieval.
Uses a fast, cheap model (Gemini 1.5 Flash) to expand vague language into cognitive topics.
"""

import google.generativeai as genai
import os

def rewrite_query(user_message: str) -> str:
    """
    Rewrites the user message into an intent-rich semantic search query.
    
    Args:
        user_message (str): The original user chat message.
        
    Returns:
        str: The rewritten query (under 20 words) focused on concepts and principles.
    """
    try:
        # Use lightweight model for speed and cost efficiency
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
Rewrite the following user query for high-signal semantic retrieval. 
Focus on decision-making, principles, strategies, and conceptual topics — not biography.

User Query: "{user_message}"

Constraints:
1. Expansion: Expand vague language into cognitive topics.
2. Preservation: Preserve the original core meaning.
3. Length: Keep output strictly under 20 words.
4. Output: Return ONLY the rewritten query string. No explanations.
"""
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            cleaned_query = response.text.strip().replace('"', '').replace('\n', ' ')
            return cleaned_query
            
        return user_message # Fallback to original if empty response
        
    except Exception as e:
        print(f"⚠️ Query manipulation failed: {e}")
        return user_message # Fallback to original on error
