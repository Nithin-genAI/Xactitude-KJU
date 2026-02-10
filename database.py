import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import os
import traceback

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), "curio_data.db")

def get_connection():
    """Get database connection with proper settings"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def init_database():
    """Initialize the SQLite database with required tables"""
    try:
        conn = get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # users table with email support
        # We'll create it with email if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                email TEXT UNIQUE,
                preferred_region TEXT DEFAULT 'Global',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # MIGRATION: Check if email column exists, if not add it
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'email' not in columns:
            print("🔄 Migrating database: Adding email column to users table...")
            try:
                # SQLite cannot add UNIQUE column directly
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
                conn.commit()
                # Create unique index instead
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            except Exception as e:
                print(f"⚠️ Migration warning: {e}")

        # Learning sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                topic TEXT NOT NULL,
                persona TEXT NOT NULL,
                region TEXT,
                student_level TEXT,
                is_custom_guide BOOLEAN DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Chat messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
            )
        """)
        
        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                favorite_personas TEXT,
                favorite_topics TEXT,
                preferred_level TEXT DEFAULT 'beginner',
                total_sessions INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Analytics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        traceback.print_exc()
        return False

def get_or_create_user(user_id: str = None, username: str = "Anonymous", preferred_region: str = "Global", email: str = None) -> Dict:
    """
    Get existing user by EMAIL or create new one.
    If email is provided, we prioritize looking up by email.
    """
    try:
        conn = get_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        cursor = conn.cursor()
        user = None
        
        # 1. Try to find by EMAIL first (if provided)
        if email:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            
            if user:
                print(f"✅ Found existing user by email: {email}")
                # Update username if it changed
                if username and username != user[1]:
                    cursor.execute("UPDATE users SET username = ? WHERE email = ?", (username, email))
                    conn.commit()
        
        # 2. If not found by email, try user_id (fallback for legacy/session-based)
        if not user and user_id:
             cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
             user = cursor.fetchone()
        
        # 3. If still not found, CREATE NEW USER
        if not user:
            # Generate ID if needed
            if not user_id:
                import uuid
                user_id = str(uuid.uuid4())
                
            print(f"🆕 Creating new user: {username} ({email if email else 'No Email'})")
            
            cursor.execute("""
                INSERT INTO users (user_id, username, email, preferred_region)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, email, preferred_region))
            
            # Create user preferences
            cursor.execute("""
                INSERT INTO user_preferences (user_id, favorite_personas, favorite_topics)
                VALUES (?, ?, ?)
            """, (user_id, "[]", "[]"))
            
            conn.commit()
            
            # Retrieve newly created user
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
        else:
            # User found, update last active
            # Use the found user's ID for the update
            actual_user_id = user[0]
            cursor.execute("""
                UPDATE users SET last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (actual_user_id,))
            conn.commit()
            
            # Retrieve again to be safe
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (actual_user_id,))
            user = cursor.fetchone()
        
        conn.close()
        
        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"] if "email" in user.keys() else None,
            "preferred_region": user["preferred_region"],
            "created_at": user["created_at"],
            "last_active": user["last_active"]
        }
    except Exception as e:
        print(f"❌ Error in get_or_create_user: {e}")
        traceback.print_exc()
        return {"error": str(e)}

def create_learning_session(user_id: str, topic: str, persona: str, region: str, 
                            student_level: str, is_custom_guide: bool = False) -> int:
    """Create a new learning session and return session_id"""
    try:
        conn = get_connection()
        if not conn:
            return -1
        
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO learning_sessions 
            (user_id, topic, persona, region, student_level, is_custom_guide)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, topic, persona, region, student_level, int(is_custom_guide)))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Created learning session: {session_id} | Topic: {topic} | Persona: {persona}")
        return session_id
    except Exception as e:
        print(f"❌ Error creating learning session: {e}")
        traceback.print_exc()
        return -1

def add_chat_message(session_id: int, role: str, content: str) -> bool:
    """Add a chat message to the session"""
    try:
        conn = get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Insert message
        cursor.execute("""
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (?, ?, ?)
        """, (session_id, role, content))
        
        # Update message count
        cursor.execute("""
            UPDATE learning_sessions 
            SET message_count = message_count + 1
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Message stored: [{role}] in session {session_id}")
        return True
    except Exception as e:
        print(f"❌ Error adding chat message: {e}")
        traceback.print_exc()
        return False

def end_learning_session(session_id: int) -> bool:
    """Mark a learning session as ended"""
    try:
        conn = get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE learning_sessions 
            SET ended_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Session {session_id} ended successfully")
        return True
    except Exception as e:
        print(f"❌ Error ending session: {e}")
        traceback.print_exc()
        return False

def get_user_stats(user_id: str) -> Dict:
    """Get user learning statistics"""
    try:
        conn = get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        
        # Total sessions
        cursor.execute("""
            SELECT COUNT(*) FROM learning_sessions WHERE user_id = ?
        """, (user_id,))
        total_sessions = cursor.fetchone()[0]
        
        # Total messages
        cursor.execute("""
            SELECT SUM(message_count) FROM learning_sessions WHERE user_id = ?
        """, (user_id,))
        total_messages = cursor.fetchone()[0] or 0
        
        # Favorite topics
        cursor.execute("""
            SELECT topic, COUNT(*) as count 
            FROM learning_sessions 
            WHERE user_id = ?
            GROUP BY topic
            ORDER BY count DESC
            LIMIT 5
        """, (user_id,))
        favorite_topics = [{"topic": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Favorite personas
        cursor.execute("""
            SELECT persona, COUNT(*) as count 
            FROM learning_sessions 
            WHERE user_id = ?
            GROUP BY persona
            ORDER BY count DESC
            LIMIT 5
        """, (user_id,))
        favorite_personas = [{"persona": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Recent sessions
        cursor.execute("""
            SELECT session_id, topic, persona, started_at, message_count
            FROM learning_sessions 
            WHERE user_id = ?
            ORDER BY started_at DESC
            LIMIT 5
        """, (user_id,))
        recent_sessions = [{
            "session_id": row[0],
            "topic": row[1],
            "persona": row[2],
            "started_at": row[3],
            "message_count": row[4]
        } for row in cursor.fetchall()]
        
        # All sessions (for full history)
        cursor.execute("""
            SELECT session_id, topic, persona, started_at, message_count
            FROM learning_sessions 
            WHERE user_id = ?
            ORDER BY started_at DESC
        """, (user_id,))
        
        all_sessions = [{
            "session_id": row[0],
            "topic": row[1],
            "persona": row[2],
            "started_at": row[3],
            "message_count": row[4]
        } for row in cursor.fetchall()]
        
        conn.close()
        
        print(f"✅ Retrieved stats for user {user_id}")
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "favorite_topics": favorite_topics,
            "favorite_personas": favorite_personas,
            "recent_sessions": recent_sessions,
            "all_sessions": all_sessions
        }
    except Exception as e:
        print(f"❌ Error getting user stats: {e}")
        traceback.print_exc()
        return {}

def log_analytics_event(event_type: str, event_data: Dict = None) -> bool:
    """Log analytics event"""
    try:
        conn = get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO analytics (event_type, event_data)
            VALUES (?, ?)
        """, (event_type, json.dumps(event_data) if event_data else None))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Analytics event logged: {event_type}")
        return True
    except Exception as e:
        print(f"❌ Error logging analytics: {e}")
        traceback.print_exc()
        return False

def get_popular_topics(limit: int = 10) -> List[Dict]:
    """Get most popular topics across all users"""
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT topic, COUNT(*) as count
            FROM learning_sessions
            GROUP BY topic
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        topics = [{"topic": row[0], "count": row[1]} for row in cursor.fetchall()]
        conn.close()
        
        print(f"✅ Retrieved {len(topics)} popular topics")
        return topics
    except Exception as e:
        print(f"❌ Error getting popular topics: {e}")
        traceback.print_exc()
        return []

def get_popular_personas(limit: int = 10) -> List[Dict]:
    """Get most popular personas across all users"""
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT persona, COUNT(*) as count
            FROM learning_sessions
            GROUP BY persona
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        personas = [{"persona": row[0], "count": row[1]} for row in cursor.fetchall()]
        conn.close()
        
        print(f"✅ Retrieved {len(personas)} popular personas")
        return personas
    except Exception as e:
        print(f"❌ Error getting popular personas: {e}")
        traceback.print_exc()
        return []

def get_chat_history(session_id: int) -> List[Dict]:
    """Get chat history for a specific session"""
    try:
        conn = get_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, timestamp
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        
        messages = [{"role": row[0], "content": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
        conn.close()
        
        print(f"✅ Retrieved {len(messages)} messages from session {session_id}")
        return messages
    except Exception as e:
        print(f"❌ Error getting chat history: {e}")
        traceback.print_exc()
        return []

def update_user_preferences(user_id: str, favorite_topics: List[str] = None, 
                           favorite_personas: List[str] = None, 
                           preferred_level: str = None) -> bool:
    """Update user preferences"""
    try:
        conn = get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if favorite_topics is not None:
            updates.append("favorite_topics = ?")
            params.append(json.dumps(favorite_topics))
        
        if favorite_personas is not None:
            updates.append("favorite_personas = ?")
            params.append(json.dumps(favorite_personas))
        
        if preferred_level is not None:
            updates.append("preferred_level = ?")
            params.append(preferred_level)
        
        if updates:
            params.append(user_id)
            query = f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            print(f"✅ User preferences updated for {user_id}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error updating user preferences: {e}")
        traceback.print_exc()
        return False

def get_session_details(session_id: int) -> Dict:
    """Get complete session details including metadata and messages"""
    try:
        conn = get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        
        # Get session info
        cursor.execute("""
            SELECT session_id, user_id, topic, persona, region, student_level, 
                   started_at, ended_at, message_count, is_custom_guide
            FROM learning_sessions
            WHERE session_id = ?
        """, (session_id,))
        
        session_row = cursor.fetchone()
        if not session_row:
            return {}
        
        # Get chat history
        messages = get_chat_history(session_id)
        
        conn.close()
        
        return {
            "session_id": session_row[0],
            "user_id": session_row[1],
            "topic": session_row[2],
            "persona": session_row[3],
            "region": session_row[4],
            "student_level": session_row[5],
            "started_at": session_row[6],
            "ended_at": session_row[7],
            "message_count": session_row[8],
            "is_custom_guide": session_row[9],
            "messages": messages
        }
    except Exception as e:
        print(f"❌ Error getting session details: {e}")
        traceback.print_exc()
        return {}

def delete_session(session_id: int) -> bool:
    """Delete a session and its messages"""
    try:
        conn = get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Delete messages first
        cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        
        # Delete session
        cursor.execute("DELETE FROM learning_sessions WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Session {session_id} and its messages deleted")
        return True
    except Exception as e:
        print(f"❌ Error deleting session: {e}")
        traceback.print_exc()
        return False

# Initialize database on import
init_database()