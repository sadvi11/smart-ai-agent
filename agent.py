"""
agent.py — Claude AI Agent with RAG + Tool Use

WHY RAG + Tools together:
- Tools answer real-time questions (weather, calculations)
- RAG answers questions about YOUR documents
- Together = agent with memory, knowledge, and live data

Architecture:
  User question
        ↓
  Retrieve relevant context from RAG (if any)
        ↓
  Build system prompt with context injected
        ↓
  Claude decides: use tool OR answer from context OR general knowledge
        ↓
  Final answer returned
"""

import anthropic
import os
from dotenv import load_dotenv
from tools import TOOLS, get_weather, calculate
from rag import retrieve_context, format_context

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def build_system_prompt(rag_context: str = "") -> str:
    """
    Build the system prompt, injecting RAG context when available.

    WHY inject into system prompt (not user message):
    System prompt sets the agent's knowledge base.
    Injecting here means Claude treats it as established fact,
    not as user-provided information (which it might question).

    Real life: Like Nokia's alarm system loading the network
    topology map before processing any alarm — context first.
    """
    base_prompt = (
        "You are a helpful AI assistant with access to real-time tools "
        "and a knowledge base of uploaded documents. "
        "Use tools when you need live data (weather, calculations). "
        "Use the knowledge base context when answering questions about "
        "uploaded documents. Always be concise and accurate."
    )

    if rag_context:
        return (
            f"{base_prompt}\n\n"
            f"RELEVANT KNOWLEDGE BASE CONTEXT:\n"
            f"{'='*50}\n"
            f"{rag_context}\n"
            f"{'='*50}\n"
            f"Use this context to answer questions when relevant. "
            f"If the context does not contain the answer, say so clearly."
        )

    return base_prompt


def run_agent(user_message: str, conversation_history: list = []) -> tuple:
    """
    Run the AI agent with RAG + tool use.

    Flow:
    1. Retrieve relevant context from RAG knowledge base
    2. Build system prompt with context injected
    3. Send to Claude with tools available
    4. If Claude uses a tool → execute tool → send result back
    5. Return final answer

    Args:
        user_message: User's input text
        conversation_history: List of past messages

    Returns:
        Tuple of (answer string, updated history list)
    """
    print(f"\nUser said: {user_message}")

    if not user_message.strip():
        return "Please type a message so I can help you.", conversation_history

    # ── Step 1: RAG retrieval ─────────────────────────────────────────
    # WHY: Before calling Claude, check if we have relevant documents
    # Same concept as Nokia checking its knowledge base before
    # dispatching an engineer — use existing knowledge first
    print("Searching knowledge base...")
    relevant_chunks = retrieve_context(user_message, k=3)
    rag_context = format_context(relevant_chunks)

    if rag_context:
        print(f"Found {len(relevant_chunks)} relevant chunks from knowledge base")
    else:
        print("No relevant context found — using general knowledge")

    # ── Step 2: Build system prompt with context ──────────────────────
    system_prompt = build_system_prompt(rag_context)

    # ── Step 3: Add user message to history ──────────────────────────
    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    # ── Step 4: Call Claude ───────────────────────────────────────────
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        tools=TOOLS,
        messages=conversation_history
    )

    print(f"Claude decision: {response.stop_reason}")

    # ── Step 5: Handle tool use ───────────────────────────────────────
    if response.stop_reason == "tool_use":

        tool_use_block = next(
            block for block in response.content
            if block.type == "tool_use"
        )

        tool_name = tool_use_block.name
        tool_input = tool_use_block.input

        print(f"Tool chosen: {tool_name}")
        print(f"Tool input: {tool_input}")

        if tool_name == "get_weather":
            tool_result = get_weather(tool_input["city"])
        elif tool_name == "calculate":
            tool_result = calculate(tool_input["expression"])
        else:
            tool_result = "Tool not found"

        print(f"Tool result: {tool_result}")

        conversation_history.append({
            "role": "assistant",
            "content": response.content
        })
        conversation_history.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": tool_result
            }]
        })

        # Send tool result back to Claude for final answer
        final_response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=conversation_history
        )

        final_answer = final_response.content[0].text

    else:
        # Claude answered directly (from context or general knowledge)
        final_answer = response.content[0].text

    conversation_history.append({
        "role": "assistant",
        "content": final_answer
    })

    print(f"Final answer: {final_answer}")
    return final_answer, conversation_history


# ── Test agent directly ───────────────────────────────────────────────
if __name__ == "__main__":
    history = []

    print("\n--- Test 1: RAG question ---")
    answer, history = run_agent(
        "What cloud certifications is Sadhvi pursuing?", history
    )

    print("\n--- Test 2: Tool use ---")
    answer, history = run_agent("What is the weather in Calgary?", history)

    print("\n--- Test 3: RAG + memory ---")
    answer, history = run_agent(
        "Based on her background, is she suitable for DevOps roles?", history
    )
