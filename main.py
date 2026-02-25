from llm import call_llm
from models import (
    InputSchema, Message, Tool, ToolCall, ToolProperty,
    ToolResultMessage, UserMessage,
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


def execute_tool(tool_call: ToolCall) -> str:
    if tool_call.name == "get_weather":
        city = tool_call.input.get("city", "unknown")
        return f"The weather in {city} is 72°F and sunny."
    return "Tool not found."


def test_plain():
    print("=== Plain text ===")
    messages = [UserMessage("What is the capital of France?")]
    response = call_llm(messages, system=SYSTEM)
    print(response.text)


def test_tool_use():
    print("\n=== Tool use ===")
    messages = [UserMessage("What is the weather in Tokyo?")]

    response = call_llm(messages, system=SYSTEM, tools=[get_weather])
    print(f"stop_reason: {response.stop_reason}")

    if response.has_tool_calls:
        for tool_call in response.tool_calls:
            print(f"Tool called: {tool_call.name}({tool_call.input})")
            result = execute_tool(tool_call)
            print(f"Tool result: {result}")

            messages.append(Message(role="assistant", content=[
                {"type": "tool_use", "id": tool_call.id, "name": tool_call.name, "input": tool_call.input}
            ]))
            messages.append(ToolResultMessage(tool_call.id, result))

        final = call_llm(messages, system=SYSTEM, tools=[get_weather])
        print(f"Final answer: {final.text}")


if __name__ == "__main__":
    test_plain()
    test_tool_use()
