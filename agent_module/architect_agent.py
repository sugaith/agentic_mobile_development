# input_agent.py
"""
Input Agent – analyzes annotated UI images with **OpenAI o‑series vision
support** and outputs a structured React Native implementation plan.

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
from typing import List, Union
import sys # Add sys import

# Add project root to the Python path to allow absolute imports
project_root = Path(__file__).resolve().parents[1] # Go up two levels (agent_module -> agentic_mobile_development)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
from langchain.tools import tool  # LangChain tool wrapper
# Use absolute import from project root
from agent_module.system_description.agent_job_descriptions import ARCHITECT_AGENT_JOB_DESCRIPTION, ARCHITECT_AGENT_DUTY
# Import the tool using an absolute path from the project root perspective
from agent_module.agent_tools.agent_tools import write_code_tool


# Load environment variables from .env file
load_dotenv()

# Ensure required environment variables are set (optional but good practice)
required_vars = [
    "LANGCHAIN_TRACING_V2",
    "LANGCHAIN_ENDPOINT",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_PROJECT",
    "OPENAI_API_KEY",
]
for var in required_vars:
    if var not in os.environ:
        raise EnvironmentError(
            f"Required environment variable '{var}' not found. "
            "Ensure it is set in your .env file or environment."
        )

__all__ = ["ArchitectAgent", "generate_ui_plan"]

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

    def __init__(self, *, model_name: str = "gpt-4o", temperature: float = 0.0):
        # gpt‑4o (or any o‑series) natively supports multimodal inputs.
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)

    # ------------------------------------------------------------------
    def __call__(self, folder: Union[str, Path]) -> str:  # noqa: D401
        """Return the structured plan for images inside *folder*."""
        image_blocks = _gather_image_blocks(folder)

        user_content = [
            {"type": "text", "text": ARCHITECT_AGENT_DUTY},
            *image_blocks,
        ]

        messages = [
            SystemMessage(content=ARCHITECT_AGENT_JOB_DESCRIPTION),
            HumanMessage(content=user_content),
        ]

        response = self.llm.invoke(messages)
        return response.content  # type: ignore[return-value]


# -----------------------------------------------------------------------------
# LangChain Tool wrapper
# -----------------------------------------------------------------------------
@tool("generate_ui_plan", return_direct=True)
def generate_ui_plan(*, folder: str) -> str:  # type: ignore[valid-type]
    """Generate a React Native UI implementation plan from annotated images in *folder*."""
    agent = ArchitectAgent()
    return agent(folder)
