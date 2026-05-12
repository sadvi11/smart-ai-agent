"""
app.py — Flask REST API for Smart AI Agent with RAG

Endpoints:
  POST /chat          - Chat with the agent (RAG-enhanced)
  POST /upload        - Upload document to knowledge base
  GET  /documents     - List all documents in knowledge base
  DELETE /documents   - Remove a document from knowledge base
  GET  /history/<id>  - Get conversation history
  GET  /health        - Health check
"""

from flask import Flask, request, jsonify
from agent import run_agent
from memory import save_message, load_history
from rag import store_document, list_documents, delete_document, retrieve_context, format_context
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# WHY: Store active sessions in memory
# Each user gets their own conversation history
sessions = {}


# ── CHAT ─────────────────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint — now RAG-enhanced.

    The agent automatically searches the knowledge base
    before responding. No change needed to how you call this endpoint.

    Request body:
        {
            "message": "What does the document say about X?",
            "session_id": "optional-session-id"
        }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No data sent"}), 400

        user_message = data.get("message", "")
        session_id = data.get("session_id", str(uuid.uuid4()))

        if not user_message.strip():
            return jsonify({
                "error": "Message cannot be empty",
                "session_id": session_id
            }), 400

        if session_id not in sessions:
            sessions[session_id] = load_history(session_id)

        history = sessions[session_id]
        answer, updated_history = run_agent(user_message, history)

        save_message(session_id, "user", user_message)
        save_message(session_id, "assistant", answer)

        sessions[session_id] = updated_history

        return jsonify({
            "session_id": session_id,
            "message": user_message,
            "answer": answer,
            "status": "success"
        })

    except Exception as e:
        return jsonify({"error": str(e), "status": "failed"}), 500


# ── UPLOAD DOCUMENT ───────────────────────────────────────────────────
@app.route("/upload", methods=["POST"])
def upload():
    """
    Upload a document to the RAG knowledge base.

    The document is chunked, embedded, and stored in Supabase.
    After uploading, the agent can answer questions about this document.

    WHY this matters: This is the core RAG capability.
    Upload your CV → ask "summarise my experience"
    Upload Nokia docs → ask "what does the AMF function do"
    Upload a JD → ask "am I a good fit for this role"

    Request body:
        {
            "text": "Full document text here...",
            "source": "my-document-name"
        }

    Real life: Like Nokia's OAM system ingesting
    a new network configuration file into its knowledge base.
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No data sent"}), 400

        text = data.get("text", "").strip()
        source = data.get("source", "manual-upload")

        if not text:
            return jsonify({"error": "Text cannot be empty"}), 400

        if len(text) < 10:
            return jsonify({"error": "Text too short to be useful"}), 400

        result = store_document(content=text, source=source)

        return jsonify({
            "status": "success",
            "message": f"Document stored successfully",
            "source": source,
            "chunks_stored": result.get("stored", 0),
            "total_chunks": result.get("total_chunks", 0)
        })

    except Exception as e:
        return jsonify({"error": str(e), "status": "failed"}), 500


# ── LIST DOCUMENTS ────────────────────────────────────────────────────
@app.route("/documents", methods=["GET"])
def get_documents():
    """
    List all documents stored in the knowledge base.

    Returns document source names and chunk counts.

    Real life: Like Nokia's inventory system listing
    all network configuration files in the database.
    """
    try:
        docs = list_documents()
        return jsonify({
            "status": "success",
            "documents": docs,
            "count": len(docs)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── DELETE DOCUMENT ───────────────────────────────────────────────────
@app.route("/documents/<source>", methods=["DELETE"])
def remove_document(source):
    """
    Remove a document from the knowledge base.

    Args:
        source: Document source name (from /documents list)
    """
    try:
        result = delete_document(source)
        return jsonify({
            "status": "success",
            "message": f"Document '{source}' removed",
            "result": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── SEARCH KNOWLEDGE BASE ─────────────────────────────────────────────
@app.route("/search", methods=["POST"])
def search():
    """
    Search the knowledge base directly (without going through the agent).

    Useful for testing what context the agent will find
    before asking a full question.

    Request body:
        {
            "query": "What is the AMF function?",
            "k": 3
        }
    """
    try:
        data = request.json
        query = data.get("query", "").strip()
        k = data.get("k", 3)

        if not query:
            return jsonify({"error": "Query cannot be empty"}), 400

        chunks = retrieve_context(query, k=k)
        context = format_context(chunks)

        return jsonify({
            "status": "success",
            "query": query,
            "chunks_found": len(chunks),
            "context": context,
            "raw_chunks": chunks
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── HISTORY ───────────────────────────────────────────────────────────
@app.route("/history/<session_id>", methods=["GET"])
def get_history(session_id):
    """Get full conversation history for a session."""
    try:
        history = load_history(session_id)
        return jsonify({
            "session_id": session_id,
            "messages": history,
            "count": len(history)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── HEALTH CHECK ──────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    """
    Health check — now includes RAG status.

    Real life: Like Nokia's network health check.
    Monitoring systems ping this every minute.
    """
    try:
        docs = list_documents()
        return jsonify({
            "status": "healthy",
            "service": "smart-ai-agent",
            "version": "2.0",
            "rag": "enabled",
            "documents_in_knowledge_base": len(docs)
        })
    except Exception as e:
        return jsonify({
            "status": "healthy",
            "service": "smart-ai-agent",
            "version": "2.0",
            "rag": "error",
            "rag_error": str(e)
        })


# ── START ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Smart AI Agent API v2.0 starting...")
    print("RAG enabled — knowledge base ready")
    print("\nEndpoints:")
    print("  POST   /chat              - Chat with RAG-enhanced agent")
    print("  POST   /upload            - Upload document to knowledge base")
    print("  GET    /documents         - List knowledge base documents")
    print("  DELETE /documents/<name>  - Remove document")
    print("  POST   /search            - Search knowledge base directly")
    print("  GET    /history/<id>      - Get conversation history")
    print("  GET    /health            - Service health check")
    app.run(debug=True, host="0.0.0.0", port=5001)
