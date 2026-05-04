import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# WHY: Create one Supabase client shared across all functions
# Real life: Like one database connection pool at Nokia
# serving all network management requests
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def save_message(session_id, role, content):
    """
    Save one message to database.
    
    WHY: Every message must be saved immediately.
    If app crashes mid conversation nothing is lost.
    Real life: Like Nokia saving every alarm to database
    the moment it fires — never stored only in memory.
    """
    try:
        supabase.table("conversations").insert({
            "session_id": session_id,
            "role": role,
            "content": content
        }).execute()
        print(f"Saved to database: [{role}] {content[:50]}...")
    except Exception as e:
        print(f"Could not save message: {str(e)}")


def load_history(session_id):
    """
    Load all past messages for a session.
    
    WHY: When user comes back we load their full history
    so agent remembers everything from past conversations.
    Real life: Like WhatsApp loading your full chat history
    when you open a conversation.
    """
    try:
        result = supabase.table("conversations")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("created_at")\
            .execute()

        messages = []
        for row in result.data:
            messages.append({
                "role": row["role"],
                "content": row["content"]
            })

        print(f"Loaded {len(messages)} messages for session: {session_id}")
        return messages

    except Exception as e:
        print(f"Could not load history: {str(e)}")
        return []


def clear_history(session_id):
    """
    Delete all messages for a session.
    
    WHY: Lets user start fresh if they want.
    Real life: Like clearing your Netflix watch history.
    """
    try:
        supabase.table("conversations")\
            .delete()\
            .eq("session_id", session_id)\
            .execute()
        print(f"Cleared history for session: {session_id}")
    except Exception as e:
        print(f"Could not clear history: {str(e)}")


# Test memory.py directly
if __name__ == "__main__":

    TEST_SESSION = "test-session-001"

    print("\n--- Test 1: Save messages ---")
    save_message(TEST_SESSION, "user", "What is the weather in Calgary?")
    save_message(TEST_SESSION, "assistant", "Weather in Calgary is 11°C and partly cloudy.")

    print("\n--- Test 2: Load history ---")
    history = load_history(TEST_SESSION)
    for msg in history:
        print(f"{msg['role']}: {msg['content']}")

    print("\n--- Test 3: Clear history ---")
    clear_history(TEST_SESSION)

    print("\n--- Test 4: Confirm cleared ---")
    history = load_history(TEST_SESSION)
    print(f"Messages after clear: {len(history)}")