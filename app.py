import logging
import json
from flask import Flask, request, jsonify

# The agent, RAG and memory layers this API exists to expose. Without these
# imports /chat returned a hardcoded placeholder and /history always returned
# an empty list -- the REST surface was never connected to the agent.
from agent import run_agent
import memory
from datetime import datetime
import os
from functools import wraps
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class Config:
    DEBUG = os.getenv('FLASK_ENV', 'production') == 'development'
    MAX_REQUESTS_PER_MINUTE = 60
    REQUEST_TIMEOUT = 30

app.config.from_object(Config)

metrics = {
    'requests_total': 0,
    'requests_success': 0,
    'requests_error': 0,
    'avg_latency_ms': 0,
    'health_checks': 0
}

def track_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        metrics['requests_total'] += 1
        try:
            result = f(*args, **kwargs)
            metrics['requests_success'] += 1
            return result
        except Exception as e:
            metrics['requests_error'] += 1
            logger.error(f"Request error: {e}", exc_info=True)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            metrics['avg_latency_ms'] = duration_ms
            logger.info(f"Request completed: {f.__name__} took {duration_ms:.2f}ms")
    return decorated_function

def validate_input(required_fields):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            if not data:
                logger.warning("Request missing JSON body")
                return {"error": "Missing JSON body"}, 400
            missing = [field for field in required_fields if field not in data]
            if missing:
                logger.warning(f"Missing fields: {missing}")
                return {"error": f"Missing fields: {missing}"}, 400
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/health', methods=['GET'])
def health_check():
    metrics['health_checks'] += 1
    health_status = {
        "status": "healthy",
        "service": "smart-ai-agent",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "total_requests": metrics['requests_total'],
            "successful_requests": metrics['requests_success'],
            "failed_requests": metrics['requests_error'],
            "avg_latency_ms": metrics['avg_latency_ms']
        }
    }
    logger.info("Health check passed")
    return jsonify(health_status), 200

@app.route('/chat', methods=['POST'])
@track_request
@validate_input(['message', 'session_id'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('session_id', '').strip()
        if len(message) == 0 or len(message) > 10000:
            logger.warning(f"Invalid message length: {len(message)}")
            return {"error": "Message must be 1-10000 characters"}, 400
        if len(session_id) == 0 or len(session_id) > 255:
            logger.warning(f"Invalid session_id length: {len(session_id)}")
            return {"error": "Session ID must be 1-255 characters"}, 400
        logger.info(f"Processing chat request: session={session_id}, msg_len={len(message)}")
        # Load prior turns so the agent has conversational context. This
        # returns [] if the memory backend is unreachable, so a Supabase
        # outage degrades to a stateless answer rather than a 500.
        conversation_history = memory.load_history(session_id)

        answer, conversation_history = run_agent(message, conversation_history)

        # Persist the turn. The user already has their answer, so a storage
        # failure must never turn a successful exchange into a 500. memory.py
        # swallows its own errors today, but this guard keeps that guarantee
        # at the call site rather than depending on the callee's behaviour.
        try:
            memory.save_message(session_id, "user", message)
            memory.save_message(session_id, "assistant", answer)
        except Exception as exc:
            logger.error(f"Failed to persist turn for {session_id}: {exc}", exc_info=True)

        response = {
            "answer": answer,
            "session_id": session_id,
            "turns": len(conversation_history),
            "status": "success",
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"Chat request successful: {session_id}")
        return jsonify(response), 200
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {"error": f"Validation failed: {str(e)}"}, 400
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        return {"error": "Internal server error"}, 500

@app.route('/history', methods=['POST'])
@track_request
@validate_input(['session_id'])
def history():
    try:
        data = request.get_json()
        session_id = data.get('session_id', '').strip()
        if not session_id:
            return {"error": "session_id required"}, 400
        logger.info(f"Fetching history for session: {session_id}")
        messages = memory.load_history(session_id)
        history_data = {
            "session_id": session_id,
            "messages": messages,
            "message_count": len(messages),
            "status": "success"
        }
        return jsonify(history_data), 200
    except Exception as e:
        logger.error(f"History endpoint error: {e}", exc_info=True)
        return {"error": "Internal server error"}, 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    return jsonify(metrics), 200

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.path}")
    return {"error": "Not found", "path": request.path}, 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"500 error: {error}", exc_info=True)
    return {"error": "Internal server error"}, 500

@app.before_request
def log_request():
    logger.debug(f"Request: {request.method} {request.path}")

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

if __name__ == '__main__':
    logger.info("Starting Smart AI Agent server")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'production')}")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5001)), debug=Config.DEBUG, threaded=True)
    logger.info("Server shutdown")
