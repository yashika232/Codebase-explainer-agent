import os
from typing import AsyncIterator, Callable, Optional
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import Message, AssistantMessage, TextBlock

DEFAULT_MODEL = "claude-3-5-haiku-20241022"

# A robust default system prompt for the Repo Explainer Agent.
# We will optimize this system prompt using our prompt optimizer harness.
DEFAULT_SYSTEM_PROMPT = """You are a highly capable Repo Explainer Agent.
Your task is to analyze the local codebase and answer questions about its architecture, flow, components, and logic.

You have access to read-only tools: Read, Grep, Glob.
Use them to locate files, search for terms, and read code to answer questions accurately and completely.
Be concise and structured in your explanations. Highlight key files and functions with their paths.
"""

async def run_explainer(
    repo_path: str,
    question: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    model: str = DEFAULT_MODEL,
    max_turns: int = 15,
) -> AsyncIterator[Message]:
    """
    Runs the Repo Explainer agent for a specific question on the given repo_path.
    Yields the stream of messages from the agent loop.
    """
    # Verify API Key
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        
    options = ClaudeAgentOptions(
        cwd=repo_path,
        system_prompt=system_prompt,
        model=model,
        allowed_tools=["Read", "Grep", "Glob"],       # Limit tools for security
        disallowed_tools=["Write", "Edit", "Bash"],    # Strictly block modifying tools
        permission_mode="acceptEdits",
        max_turns=max_turns,
    )
    
    # We use query() since explaining is a stateless one-shot task
    async for message in query(prompt=question, options=options):
        yield message

async def explain_repo_text(
    repo_path: str,
    question: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    model: str = DEFAULT_MODEL,
    max_turns: int = 15,
    on_message_cb: Optional[Callable[[Message], None]] = None,
) -> str:
    """
    Executes the agent and returns the aggregated text response.
    Optional callback on_message_cb(message) is called for every streamed message.
    """
    response_chunks = []
    async for msg in run_explainer(repo_path, question, system_prompt, model, max_turns):
        if on_message_cb:
            on_message_cb(msg)
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    response_chunks.append(block.text)
    return "".join(response_chunks)
