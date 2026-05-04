import anthropic
import os
from dotenv import load_dotenv
from tools import TOOLS, get_weather, calculate

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def run_agent(user_message, conversation_history=[]):

    print(f"\nUser said: {user_message}")

    if not user_message.strip():
        return "Please type a message so I can help you.", conversation_history

    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system="You are a helpful assistant. Use tools when needed to get real data. Always be concise and accurate.",
        tools=TOOLS,
        messages=conversation_history
    )

    print(f"Claude decision: {response.stop_reason}")

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

        final_response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a helpful assistant. Use tools when needed to get real data. Always be concise and accurate.",
            tools=TOOLS,
            messages=conversation_history
        )

        final_answer = final_response.content[0].text

    else:
        final_answer = response.content[0].text

    conversation_history.append({
        "role": "assistant",
        "content": final_answer
    })

    print(f"Final answer: {final_answer}")
    return final_answer, conversation_history


if __name__ == "__main__":
    history = []

    print("\n--- Test 1: Weather ---")
    answer, history = run_agent("What is the weather in Calgary?", history)

    print("\n--- Test 2: Memory ---")
    answer, history = run_agent("Is that good weather to go outside?", history)

    print("\n--- Test 3: Calculate ---")
    answer, history = run_agent("If I earn $45 per hour for 40 hours what is my weekly pay?", history)