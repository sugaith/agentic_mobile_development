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

# Add project root to the Python path to allow absolute imports
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.tools import tool
from agent_module.system_description.agent_job_descriptions import ARCHITECT_AGENT_JOB_DESCRIPTION, ARCHITECT_AGENT_DUTY
from agent_module.agent_tools import write_code_tool, powershell_tool

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
# Core agent class
# -----------------------------------------------------------------------------
class ArchitectAgent:
    """Analyze images in *folder* and return the implementation plan as a string."""

    def __init__(self, *, model_name: str = "o4-mini", temperature: float = 1.0):
        # gpt‑4o (or any o‑series) natively supports multimodal inputs.
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)
        # Bind the tools to the LLM instance
        self.llm_with_tools = self.llm.bind_tools([write_code_tool, powershell_tool])

    def __call__(self, folder: Union[str, Path]) -> str:  # noqa: D401
        """
        Analyze images in *folder*. If the LLM decides to write code or execute PowerShell commands,
        it invokes the appropriate tools. Returns a summary of operations performed.
        """
        image_blocks = _gather_image_blocks(folder)

        user_content = [
            {"type": "text", "text": ARCHITECT_AGENT_DUTY},
            *image_blocks,
        ]

        messages = [
            SystemMessage(content=ARCHITECT_AGENT_JOB_DESCRIPTION),
            HumanMessage(content=user_content),
        ]

        # Invoke the LLM with the bound tools
        response = self.llm_with_tools.invoke(messages)

        # Check if the response contains tool calls
        tool_calls = response.tool_calls
        if tool_calls:
            results = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("name")
                args = tool_call.get("args", {})
                if isinstance(args, str):
                    args = json.loads(args)

                if tool_name == write_code_tool.name:
                    try:
                        relative_file_path = args.get("file_path")
                        code_content = args.get("text")

                        if not relative_file_path or code_content is None:
                            results.append(f"Error: Skipped tool call due to missing 'file_path' or 'text': {args}")
                            continue

                        full_file_path = PROJECT_ROOT_PATH / relative_file_path
                        full_file_path.parent.mkdir(parents=True, exist_ok=True)
                        tool_result = write_code_tool.run({"file_path": str(full_file_path), "text": code_content})
                        results.append(f"Code written successfully to {relative_file_path}. Tool Result: {tool_result}")

                    except Exception as e:
                        results.append(f"Error executing write_code_tool: {e}")

                elif tool_name == powershell_tool.name:
                    try:
                        command = args.get("command")
                        if not command:
                            results.append(f"Error: Skipped PowerShell command due to missing 'command': {args}")
                            continue

                        tool_result = powershell_tool.run(command)
                        results.append(f"PowerShell command executed successfully. Result: {tool_result}")

                    except Exception as e:
                        results.append(f"Error executing PowerShell command: {e}")

                else:
                    results.append(f"Skipped unsupported tool call: {tool_name}")

            return "\n".join(results) if results else "Tool calls received but none were processed."
        else:
            return response.content if response.content else "No content generated."

# -----------------------------------------------------------------------------
# LangChain Tool wrapper
# -----------------------------------------------------------------------------
@tool("generate_ui_plan", return_direct=True)
def generate_ui_plan(*, folder: str) -> str:  # type: ignore[valid-type]
    """Generate a React Native UI implementation plan from annotated images in *folder*."""
    agent = ArchitectAgent()
    return agent(folder)
