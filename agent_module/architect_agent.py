# input_agent.py
"""
Input Agent – analyzes annotated UI images with **OpenAI o‑series vision
support** and outputs a structured React Native implementation plan.

Key changes:
* **No `transformers`, no OCR.** Images are fed directly to the vision model.
* Exposes a callable `InputAgent` **and** a LangChain `Tool` named
  `generate_ui_plan` for orchestration.
* Optional CLI preserved for ad‑hoc testing.

Example (as a Tool) ::

    from input_agent import generate_ui_plan

    plan_markdown = generate_ui_plan.run({"folder": "./design_shots"})
    print(plan_markdown)

Environment::
    Requires OPENAI_API_KEY.

Dependencies::
    pip install langchain langchain-openai pillow
"""
from __future__ import annotations

import base64
import os
import mimetypes
from pathlib import Path
from typing import List, Union, Dict, Any
import sys
import json
import time # Import time for potential delays or retries if needed
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
import operator
from typing import TypedDict, Annotated, List, Union, Literal # Import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver # For potential state persistence

from agent_module.system_description.agent_job_descriptions import ARCHITECT_AGENT_JOB_DESCRIPTION, ARCHITECT_AGENT_DUTY
from agent_module.agent_tools import write_file, read_file, list_src_folder

__all__ = ["ArchitectAgent", "generate_ui_plan"]

# Get the project root from environment variable
REACT_NATIVE_PROJECT_ROOT_FOLDER = os.getenv("REACT_NATIVE_PROJECT_ROOT_FOLDER")
if not REACT_NATIVE_PROJECT_ROOT_FOLDER:
    raise ValueError("Environment variable REACT_NATIVE_PROJECT_ROOT_FOLDER is not set.")
PROJECT_ROOT_PATH = Path(REACT_NATIVE_PROJECT_ROOT_FOLDER)
if not PROJECT_ROOT_PATH.is_dir():
     raise FileNotFoundError(f"REACT_NATIVE_PROJECT_ROOT_FOLDER path does not exist or is not a directory: {PROJECT_ROOT_PATH}")

# -----------------------------------------------------------------------------
# Helpers – image handling
# -----------------------------------------------------------------------------

_SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

def _encode_image(path: Path) -> dict:
    """Return an `image_url` content block with a `data:` URI for the given file."""
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        raise ValueError(f"Unsupported image type: {path.suffix}")

    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    data_uri = f"data:{mime_type};base64,{b64}"
    return {"type": "image_url", "image_url": {"url": data_uri}}

def _gather_image_blocks(folder: Union[str, Path]) -> List[dict]:
    """Collect base64‑encoded image blocks from *folder*."""
    folder_path = Path(folder)
    if not folder_path.exists() or not folder_path.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    images = sorted(p for p in folder_path.iterdir() if p.suffix.lower() in _SUPPORTED_EXTS)
    if not images:
        raise ValueError(f"No image files found in {folder_path}")

    return [_encode_image(p) for p in images]

# -----------------------------------------------------------------------------
# LangGraph State Definition
# -----------------------------------------------------------------------------
class ArchitectAgentState(TypedDict):
    """Represents the state of our graph."""
    messages: Annotated[List[BaseMessage], operator.add]
    # Add other state variables if needed, e.g., iteration count
    # iteration: int

# -----------------------------------------------------------------------------
# LangGraph Nodes
# -----------------------------------------------------------------------------

# Node 1: The core agent logic (calling LLM with tools)
def call_architect_llm(state: ArchitectAgentState):
    """Calls the LLM with the current message history."""
    print("--- Calling Architect LLM ---")
    # Assuming llm_with_tools is accessible (we'll set this up in the class/runner)
    # Need to instantiate the LLM and tools here or pass them in.
    # For simplicity, let's assume they are accessible via a global or passed context later.
    # We will refine this when integrating into the class structure.
    response = llm_with_tools.invoke(state["messages"])
    # We return a dictionary mapping state keys to values to update
    return {"messages": [response]}

# Node 2: Executes tools
def execute_tools(state: ArchitectAgentState):
    """Executes tools called by the LLM."""
    print("--- Executing Tools ---")
    messages = state["messages"]
    last_message = messages[-1]

    tool_calls = last_message.tool_calls
    if not tool_calls:
        print("No tool calls requested.")
        return {"messages": []} # No update if no tools called

    tool_results = []
    print(f"Tool calls requested: {[tc['name'] for tc in tool_calls]}")
    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})
        tool_call_id = tool_call.get("id")

        # Ensure args is a dictionary
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse args string for tool {tool_name}: {args}")
                args = {}

        tool_to_run = None
        if tool_name == write_file.name:
            tool_to_run = write_file
        elif tool_name == read_file.name:
            tool_to_run = read_file
        elif tool_name == list_src_folder.name:
            tool_to_run = list_src_folder

        result_content = f"Error: Tool '{tool_name}' not found or not runnable."
        if tool_to_run:
            try:
                # Adjust arguments for write_file specifically
                if tool_name == write_file.name:
                    relative_file_path = args.get("file_path")
                    code_content = args.get("text")
                    if not relative_file_path or code_content is None:
                        result_content = f"Error: Skipped tool call due to missing 'file_path' or 'text': {args}"
                    else:
                        if os.path.isabs(relative_file_path):
                            full_file_path = Path(relative_file_path)
                        else:
                            full_file_path = PROJECT_ROOT_PATH / relative_file_path
                        try:
                            full_file_path.parent.mkdir(parents=True, exist_ok=True)
                            print(f"Attempting to write to: {full_file_path}")
                            tool_result = tool_to_run.run({"file_path": str(full_file_path), "text": code_content})
                            result_content = f"Tool '{tool_name}' executed. Result: {tool_result}"
                        except Exception as e:
                            result_content = f"Error creating directories or writing file for {relative_file_path}: {e}"
                elif tool_name == list_src_folder.name:
                    tool_result = tool_to_run.run({}) # Pass empty dict if no args expected
                    result_content = f"Tool '{tool_name}' executed. Result: {tool_result}"
                elif tool_name == read_file.name:
                    file_path_to_read = args.get("file_path")
                    if not file_path_to_read:
                        result_content = f"Error: Skipped read_file call due to missing 'file_path': {args}"
                    else:
                        if os.path.isabs(file_path_to_read):
                            full_read_path = Path(file_path_to_read)
                        else:
                            full_read_path = PROJECT_ROOT_PATH / file_path_to_read
                        print(f"Attempting to read from: {full_read_path}")
                        if full_read_path.is_file():
                            tool_result = tool_to_run.run({"file_path": str(full_read_path)})
                            result_content = f"Tool '{tool_name}' executed. Result: {tool_result}"
                        else:
                            result_content = f"Error: File not found for reading: {full_read_path}"
                else:
                    tool_result = tool_to_run.run(args)
                    result_content = f"Tool '{tool_name}' executed. Result: {tool_result}"
            except Exception as e:
                print(f"Error executing tool {tool_name}: {e}")
                result_content = f"Error executing tool {tool_name}: {e}"
        else:
            print(f"Warning: Tool '{tool_name}' not found.")

        print(f"Tool Result ({tool_name}): {result_content}")
        tool_results.append(ToolMessage(content=str(result_content), tool_call_id=tool_call_id))

    return {"messages": tool_results}

# -----------------------------------------------------------------------------
# LangGraph Conditional Edges
# -----------------------------------------------------------------------------

def should_continue(state: ArchitectAgentState) -> Literal["execute_tools", "end_loop", "continue"]:
    """Determines whether to continue the loop or end."""
    print("--- Checking Condition ---")
    last_message = state["messages"][-1]
    # If the LLM made tool calls, then execute tools
    if last_message.tool_calls:
        print("Condition: Tool calls detected, routing to execute_tools.")
        return "execute_tools"
    # Otherwise, check for completion signal
    if isinstance(last_message, AIMessage) and "TASK COMPLETE" in last_message.content:
        print("Condition: TASK COMPLETE detected, routing to end.")
        return "end_loop"
    # Otherwise, route back to the agent node
    print("Condition: No tool calls, TASK COMPLETE not found. Routing back to agent.")
    return "continue"

# -----------------------------------------------------------------------------
# Build the Graph
# -----------------------------------------------------------------------------

# Define the workflow
workflow = StateGraph(ArchitectAgentState)

# Add the nodes
workflow.add_node("agent", call_architect_llm)
workflow.add_node("tools", execute_tools)

# Set the entrypoint
workflow.set_entry_point("agent")

# Add edges
workflow.add_conditional_edges(
    "agent",
    # This function decides which node to call next based on the last message
    should_continue,
    {
        # If `should_continue` returns "execute_tools", call the tools node.
        "execute_tools": "tools",
        # If `should_continue` returns "end_loop", finish the graph.
        "end_loop": END,
        # If `should_continue` returns "continue", loop back to the agent.
        "continue": "agent",
    },
)

# Add edge from tools node back to agent node
workflow.add_edge("tools", "agent")

# Compile the graph (optionally add memory for persistence)
# memory = MemorySaver() # Example if you need persistence
app = workflow.compile() # checkpointer=memory

# Global LLM instance (or manage within a class)
# This needs proper setup - ideally passed during graph execution or part of a class
llm_with_tools = None

# -----------------------------------------------------------------------------
# Modified Agent Class / Runner Function
# -----------------------------------------------------------------------------
class ArchitectAgent:
    """Uses LangGraph to analyze images iteratively."""

    def __init__(self, *, model_name: str = "gemini-2.5-pro-preview-03-25", temperature: float = 0.3):
        global llm_with_tools # Use global for simplicity in this refactor
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
        self.tools = [write_file, read_file, list_src_folder]
        llm_with_tools = self.llm.bind_tools(self.tools, tool_choice="any")
        self.graph = app # The compiled LangGraph application

    def __call__(self, folder: Union[str, Path]) -> str:
        """Runs the LangGraph-based analysis."""
        print(f"Starting Architect Agent analysis for folder: {folder}")
        image_blocks = _gather_image_blocks(folder)

        initial_prompt_text = f"{ARCHITECT_AGENT_JOB_DESCRIPTION}\n\n{ARCHITECT_AGENT_DUTY}"
        user_content = [{"type": "text", "text": initial_prompt_text}, *image_blocks]

        initial_state = {"messages": [HumanMessage(content=user_content)]}

        # Define config for potential persistence or recursion limits
        # config = {"recursion_limit": 50, "configurable": {"thread_id": "user_123"}} # Example config
        config = {"recursion_limit": 6} # Simple recursion limit

        final_state = None
        final_summary = "Architect agent started (LangGraph)..."
        try:
            # Stream events for detailed logging (optional)
            # for event in self.graph.stream(initial_state, config=config):
            #     print(event)
            #     print("---")
            # final_state = event

            # Or invoke directly for the final state
            final_state = self.graph.invoke(initial_state, config=config)

            print("--- Architect Agent (LangGraph) Execution Complete ---")
            # Extract final messages or summary
            if final_state and "messages" in final_state:
                final_summary += "\nFinal Messages:\n" + "\n".join([str(m) for m in final_state["messages"]])
            else:
                final_summary += "\nExecution finished, but final state is unexpected."

        except Exception as e:
            print(f"Error during LangGraph execution: {e}")
            final_summary += f"\nError during LangGraph execution: {e}"

        return final_summary

# -----------------------------------------------------------------------------
# LangChain Tool wrapper
# -----------------------------------------------------------------------------
@tool("generate_ui_plan", return_direct=True)
def generate_ui_plan(*, folder: str) -> str:  # type: ignore[valid-type]
    """Generate a React Native UI implementation plan from annotated images in *folder* using LangGraph."""
    agent = ArchitectAgent()
    return agent(folder)
