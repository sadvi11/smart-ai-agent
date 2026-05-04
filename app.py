from flask import Flask, request, jsonify
from agent import run_agent
from memory import save_message, load_history
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# WHY: Store active sessions in memory
# Each user gets their own conversation history
sessions = {}


@app.route("/chat", methods=["POST"])
def chat():
    """
    Main endpoint. Accepts a message and returns agent response.

    Real life: Like Netflix's recommendation API endpoint.
    App sends user data → API returns recommendations.
    Here: User sends message → API returns agent answer.
    """
    try:
        data = request.json

        if not data:
            return jsonify({
                "error": "No data sent"
            }), 400

        user_message = data.get("message", "")
        session_id = data.get("session_id", str(uuid.uuid4()))

        if not user_message.strip():
            return jsonify({
                "error": "Message cannot be empty",
                "session_id": session_id
            }), 400

        # Load past history from Supabase
        if session_id not in sessions:
            sessions[session_id] = load_history(session_id)

        history = sessions[session_id]

        # Run the agent
        answer, updated_history = run_agent(user_message, history)

        # Save to Supabase
        save_message(session_id, "user", user_message)
        save_message(session_id, "assistant", answer)

        # Update session
        sessions[session_id] = updated_history

        return jsonify({
            "session_id": session_id,
            "message": user_message,
            "answer": answer,
            "status": "success"
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "failed"
        }), 500


@app.route("/history/<session_id>", methods=["GET"])
def get_history(session_id):
    """
    Get full conversation history for a session.

    Real life: Like WhatsApp loading your chat history
    when you open a conversation.
    """
    try:
        history = load_history(session_id)
        return jsonify({
            "session_id": session_id,
            "messages": history,
            "count": len(history)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint.

    Real life: Like Nokia's network health check.
    Monitoring systems ping this every minute.
    If it returns healthy — all systems running.
    """
    return jsonify({
        "status": "healthy",
        "service": "smart-ai-agent",
        "version": "1.0"
    })


if __name__ == "__main__":
    print("Smart AI Agent API starting...")
    print("Endpoints:")
    print("  POST /chat      - Send message to agent")
    print("  GET  /history   - Get conversation history")
    print("  GET  /health    - Check service health")
    app.run(debug=True, host="0.0.0.0", port=5001)