import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict
from datetime import datetime
import traceback
import json

# ChromaDB persistent directory
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_data")

# Ensure directory exists
os.makedirs(CHROMA_DIR, exist_ok=True)

# Initialize ChromaDB client
client = None
try:
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False)
    )
    print(f"✅ ChromaDB initialized at {CHROMA_DIR}")
except ImportError as e:
    print(f"❌ ChromaDB module not found: {e}")
    client = None
except Exception as e:
    print(f"⚠️ ChromaDB initialization warning: {e}")
    client = None

def is_chromadb_available() -> bool:
    """Check if ChromaDB is available"""
    return client is not None

def get_user_memory_collection():
    """Get or create user memory collection"""
    try:
        if client is None:
            print("⚠️ ChromaDB client not available")
            return None
        return client.get_or_create_collection(
            name="user_memory",
            metadata={"description": "User conversation history and preferences"}
        )
    except ValueError as e:
        print(f"❌ Invalid parameters for user memory collection: {e}")
        return None
    except Exception as e:
        print(f"❌ Error getting user memory collection: {e}")
        return None

def get_learning_insights_collection():
    """Get or create learning insights collection"""
    try:
        if client is None:
            print("⚠️ ChromaDB client not available")
            return None
        return client.get_or_create_collection(
            name="learning_insights",
            metadata={"description": "User learning patterns and insights"}
        )
    except ValueError as e:
        print(f"❌ Invalid parameters for learning insights collection: {e}")
        return None
    except Exception as e:
        print(f"❌ Error getting learning insights collection: {e}")
        return None

def store_conversation_memory(user_id: str, topic: str, persona: str, 
                              conversation_snippet: str, session_id: int) -> bool:
    """
    Store conversation snippet in ChromaDB for semantic search.
    
    Args:
        user_id: User identifier
        topic: Topic being learned
        persona: Expert persona being used
        conversation_snippet: Snippet of conversation to store
        session_id: Learning session ID
        
    Returns:
        bool: Success status
    """
    try:
        collection = get_user_memory_collection()
        if collection is None:
            print("⚠️ ChromaDB collection unavailable, conversation not stored in memory")
            return False
        
        # Create unique ID
        doc_id = f"{user_id}_{session_id}_{int(datetime.now().timestamp() * 1000)}"
        
        # Store with metadata
        collection.add(
            documents=[conversation_snippet],
            metadatas=[{
                "user_id": user_id,
                "topic": topic,
                "persona": persona,
                "session_id": str(session_id),
                "timestamp": datetime.now().isoformat()
            }],
            ids=[doc_id]
        )
        
        print(f"✅ Conversation memory stored: {doc_id}")
        return True
        
    except ValueError as e:
        print(f"❌ Invalid parameters for storing conversation memory: {e}")
        return False
    except Exception as e:
        print(f"❌ Error storing conversation memory: {e}")
        traceback.print_exc()
        return False

def get_relevant_past_conversations(user_id: str, current_topic: str, limit: int = 3) -> List[Dict]:
    """
    Retrieve relevant past conversations using semantic search.
    
    Args:
        user_id: User identifier
        current_topic: Current topic being learned
        limit: Number of results to return
        
    Returns:
        List of relevant past conversations with metadata
    """
    try:
        collection = get_user_memory_collection()
        if collection is None:
            print("⚠️ ChromaDB collection unavailable")
            return []
        
        # Query for similar conversations
        results = collection.query(
            query_texts=[current_topic],
            where={"user_id": user_id},
            n_results=limit
        )
        
        if not results or not results.get('documents') or not results['documents'][0]:
            print(f"ℹ️ No past conversations found for user {user_id} on topic '{current_topic}'")
            return []
        
        # Format results
        conversations = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            conversations.append({
                "snippet": doc,
                "topic": metadata.get("topic", "Unknown"),
                "persona": metadata.get("persona", "Unknown"),
                "timestamp": metadata.get("timestamp", ""),
                "session_id": metadata.get("session_id", ""),
                "distance": results['distances'][0][i] if 'distances' in results else 0
            })
        
        print(f"✅ Retrieved {len(conversations)} past conversations for topic '{current_topic}'")
        return conversations
        
    except Exception as e:
        print(f"❌ Error retrieving past conversations: {e}")
        traceback.print_exc()
        return []

def store_learning_insight(user_id: str, insight_type: str, insight_text: str, 
                          metadata: Dict = None) -> bool:
    """
    Store learning insights (e.g., "user struggles with X", "user prefers Y style").
    
    Args:
        user_id: User identifier
        insight_type: Type of insight (e.g., "strength", "weakness", "preference")
        insight_text: Detailed insight text
        metadata: Additional metadata
        
    Returns:
        bool: Success status
    """
    try:
        collection = get_learning_insights_collection()
        if collection is None:
            print("⚠️ ChromaDB collection unavailable")
            return False
        
        doc_id = f"{user_id}_{insight_type}_{int(datetime.now().timestamp() * 1000)}"
        
        meta = metadata or {}
        meta.update({
            "user_id": user_id,
            "insight_type": insight_type,
            "timestamp": datetime.now().isoformat()
        })
        
        collection.add(
            documents=[insight_text],
            metadatas=[meta],
            ids=[doc_id]
        )
        
        print(f"✅ Learning insight stored: {doc_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error storing learning insight: {e}")
        traceback.print_exc()
        return False

def get_user_learning_insights(user_id: str, limit: int = 5) -> List[Dict]:
    """
    Get user's learning insights.
    
    Args:
        user_id: User identifier
        limit: Maximum number of insights to return
        
    Returns:
        List of learning insights
    """
    try:
        collection = get_learning_insights_collection()
        if collection is None:
            print("⚠️ ChromaDB collection unavailable")
            return []
        
        results = collection.get(
            where={"user_id": user_id},
            limit=limit
        )
        
        if not results or not results.get('documents'):
            print(f"ℹ️ No learning insights found for user {user_id}")
            return []
        
        insights = []
        for i, doc in enumerate(results['documents']):
            metadata = results['metadatas'][i] if i < len(results['metadatas']) else {}
            insights.append({
                "text": doc,
                "type": metadata.get("insight_type", ""),
                "timestamp": metadata.get("timestamp", "")
            })
        
        print(f"✅ Retrieved {len(insights)} learning insights")
        return insights
        
    except Exception as e:
        print(f"❌ Error retrieving learning insights: {e}")
        traceback.print_exc()
        return []

def generate_context_from_memory(user_id: str, current_topic: str) -> str:
    """
    Generate context string from user's past conversations.
    
    Args:
        user_id: User identifier
        current_topic: Current topic being learned
        
    Returns:
        Context string for AI system prompt
    """
    try:
        past_convos = get_relevant_past_conversations(user_id, current_topic, limit=2)
        
        if not past_convos:
            print(f"ℹ️ No memory context available for user {user_id}")
            return ""
        
        context = "\n\n🧠 RELEVANT PAST LEARNING:\n"
        for i, convo in enumerate(past_convos, 1):
            context += f"{i}. Previously learned about '{convo['topic']}' with {convo['persona']}\n"
            snippet_preview = convo['snippet'][:150].replace('\n', ' ')
            context += f"   Context: {snippet_preview}...\n"
        
        context += "\n📚 Use this context to build upon their previous knowledge!\n"
        
        print(f"✅ Generated context from {len(past_convos)} past conversations")
        return context
        
    except Exception as e:
        print(f"❌ Error generating context from memory: {e}")
        traceback.print_exc()
        return ""

def get_user_learning_profile(user_id: str) -> Dict:
    """
    Get comprehensive learning profile for a user combining insights and history.
    
    Args:
        user_id: User identifier
        
    Returns:
        Dict with user's learning profile
    """
    try:
        insights = get_user_learning_insights(user_id, limit=10)
        
        profile = {
            "user_id": user_id,
            "learning_insights": insights,
            "total_insights": len(insights),
            "generated_at": datetime.now().isoformat()
        }
        
        print(f"✅ Generated learning profile for user {user_id}")
        return profile
        
    except Exception as e:
        print(f"❌ Error generating learning profile: {e}")
        traceback.print_exc()
        return {"user_id": user_id, "error": str(e)}

def clear_user_memory(user_id: str) -> bool:
    """
    Clear all memory for a specific user (for privacy/reset).
    
    Args:
        user_id: User identifier
        
    Returns:
        bool: Success status
    """
    try:
        cleared = False
        
        # Clear from user_memory collection
        memory_collection = get_user_memory_collection()
        if memory_collection:
            results = memory_collection.get(where={"user_id": user_id})
            if results and results.get('ids'):
                memory_collection.delete(ids=results['ids'])
                print(f"✅ Cleared user_memory for {user_id}")
                cleared = True
        
        # Clear from learning_insights collection
        insights_collection = get_learning_insights_collection()
        if insights_collection:
            results = insights_collection.get(where={"user_id": user_id})
            if results and results.get('ids'):
                insights_collection.delete(ids=results['ids'])
                print(f"✅ Cleared learning_insights for {user_id}")
                cleared = True
        
        if not cleared:
            print(f"ℹ️ No data found to clear for user {user_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error clearing user memory: {e}")
        traceback.print_exc()
        return False

def search_memory_by_topic(user_id: str, topic: str, limit: int = 5) -> List[Dict]:
    """
    Search user memory by specific topic.
    
    Args:
        user_id: User identifier
        topic: Topic to search for
        limit: Number of results
        
    Returns:
        List of matching memories
    """
    try:
        collection = get_user_memory_collection()
        if collection is None:
            return []
        
        results = collection.query(
            query_texts=[topic],
            where={"user_id": user_id},
            n_results=limit
        )
        
        if not results or not results.get('documents') or not results['documents'][0]:
            return []
        
        memories = []
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            memories.append({
                "content": doc,
                "topic": metadata.get("topic", ""),
                "persona": metadata.get("persona", ""),
                "session_id": metadata.get("session_id", ""),
                "timestamp": metadata.get("timestamp", "")
            })
        
        return memories
        
    except Exception as e:
        print(f"❌ Error searching memory: {e}")
        traceback.print_exc()
        return []

def batch_store_conversations(user_id: str, conversations: List[Dict]) -> int:
    """
    Store multiple conversations at once.
    
    Args:
        user_id: User identifier
        conversations: List of conversation dicts with keys: 
                      topic, persona, snippet, session_id
        
    Returns:
        Number of conversations stored
    """
    stored_count = 0
    try:
        for conv in conversations:
            success = store_conversation_memory(
                user_id=user_id,
                topic=conv.get("topic", "Unknown"),
                persona=conv.get("persona", "Unknown"),
                conversation_snippet=conv.get("snippet", ""),
                session_id=conv.get("session_id", 0)
            )
            if success:
                stored_count += 1
        
        print(f"✅ Batch stored {stored_count}/{len(conversations)} conversations")
        return stored_count
        
    except Exception as e:
        print(f"❌ Error in batch store: {e}")
        traceback.print_exc()
        return stored_count

# Initialize on import
if is_chromadb_available():
    print("✅ User memory system ready!")
else:
    print("⚠️ User memory system not available - ChromaDB initialization failed")