import anthropic

client = anthropic.Anthropic()

# Define tools
tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA",
                }
            },
            "required": ["location"],
        },
    },
    {
        "name": "get_time",
        "description": "Get the current time in a given timezone",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "The timezone, e.g. America/New_York",
                }
            },
            "required": ["timezone"],
        },
    },
]

# Initial request
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    tools=tools,
    messages=[
        {
            "role": "user",
            "content": "What's the weather in SF and NYC, and what time is it there?",
        }
    ],
)

# Claude's response with parallel tool calls
tool_use_blocks = [c for c in response.content if c.type == "tool_use"]
print("Claude wants to use tools:", response.stop_reason == "tool_use")
print("Number of tool calls:", len(tool_use_blocks))


def mock_tool(name: str, inputs: dict) -> str:
    if name == "get_weather":
        loc = inputs.get("location", "unknown")
        return f"{loc}: 68°F, partly cloudy"
    if name == "get_time":
        tz = inputs.get("timezone", "unknown")
        return f"Current time in {tz}: 2:30 PM"
    return "Unknown tool"


# Build the conversation with tool results using actual IDs from the response
messages = [
    {
        "role": "user",
        "content": "What's the weather in SF and NYC, and what time is it there?",
    },
    {
        "role": "assistant",
        "content": response.content,
    },
    {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": mock_tool(block.name, block.input),
            }
            for block in tool_use_blocks
        ],
    },
]

# Get final response
final_response = client.messages.create(
    model="claude-opus-4-6", max_tokens=1024, tools=tools, messages=messages
)

print(final_response.content[0].text)
