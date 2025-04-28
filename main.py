import sys
from pathlib import Path
import os # Import os for cleanup if needed
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# Add project root to the Python path AFTER loading env vars if needed,
# though imports below might handle this depending on structure.
# Consider if this sys.path modification is still necessary here or if
# relative imports within the modules are sufficient.
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import modules that might depend on environment variables
from agent_module.architect_agent import ArchitectAgent
from agent_module.agent_tools.agent_tools import write_code_tool

# Ensure required environment variables are set (optional but good practice)
required_vars = [
    "LANGCHAIN_TRACING_V2",
    "LANGCHAIN_ENDPOINT",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_PROJECT",
    "OPENAI_API_KEY",
    "REACT_NATIVE_PROJECT_ROOT_FOLDER",
]
for var in required_vars:
    if var not in os.environ:
        raise EnvironmentError(
            f"Required environment variable '{var}' not found. "
            "Ensure it is set in your .env file or environment."
        )


def run_architect_agent_example():
    """Runs the example usage of the ArchitectAgent."""
    print("--- Running Architect Agent Example ---")
    # Define the path to the UI images relative to the project root
    # TODO: Consider making this configurable (e.g., via command-line args or env var)
    image_folder = project_root / "zbase_rn_project" / "ui_images"

    if not image_folder.exists() or not image_folder.is_dir():
        print(f"Error: Image folder not found at {image_folder}")
        print("Please ensure the 'zbase_rn_project/ui_images' directory exists relative to main.py")
        return

    try:
        agent = ArchitectAgent()
        plan_text = agent(image_folder)
        print("--- Generated Plan ---")
        print(plan_text)
        print("----------------------")
    except FileNotFoundError as e:
        print(f"Error during agent execution: {e}")
    except ValueError as e:
        print(f"Error during agent execution: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print(f"Running script from project root: {project_root}")
    run_architect_agent_example()
    # test_write_code_tool()
