from agent import call_llm
from models import (
    Tool, InputSchema, ToolProperty,
    Message, UserMessage, ToolResultMessage,
    AgentResponse, ToolCall,
)

SYSTEM = "You are a helpful assistant."

get_weather = Tool(
    name="get_weather",
    description="Get the current weather for a given city.",
    input_schema=InputSchema(
        properties={
            "city": ToolProperty(type="string", description="The city to get weather for."),
        },
        required=["city"],
    ),
)

# Fake tool execution
def execute_tool(tool_call: ToolCall) -> str:
    if tool_call.name == "get_weather":
        city = tool_call.input.get("city", "unknown")
        return f"The weather in {city} is 72°F and sunny."
    return "Tool not found."


def test_plain():
    print("=== Plain text ===")
    messages = [UserMessage("What is the capital of France?")]
    response = AgentResponse.from_message(call_llm(messages, system=SYSTEM))
    print(response.text)


def test_tool_use():
    print("\n=== Tool use ===")
    messages = [UserMessage("What is the weather in Tokyo?")]

    # First call — LLM should request the tool
    response = AgentResponse.from_message(
        call_llm(messages, system=SYSTEM, tools=[get_weather])
    )
    print(f"stop_reason: {response.stop_reason}")

    if response.has_tool_calls:
        for tool_call in response.tool_calls:
            print(f"Tool called: {tool_call.name}({tool_call.input})")
            result = execute_tool(tool_call)
            print(f"Tool result: {result}")

            # Append assistant turn (with tool use blocks) and tool result
            messages.append(Message(role="assistant", content=[
                {"type": "tool_use", "id": tool_call.id, "name": tool_call.name, "input": tool_call.input}
            ]))
            messages.append(ToolResultMessage(tool_call.id, result))

        # Second call — LLM produces final answer
        final = AgentResponse.from_message(
            call_llm(messages, system=SYSTEM, tools=[get_weather])
        )
        print(f"Final answer: {final.text}")


if __name__ == "__main__":
    test_plain()
    test_tool_use()
