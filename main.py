import sys
from pathlib import Path

# Add project root to the Python path to allow absolute imports from anywhere
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent_module.architect_agent import ArchitectAgent
from agent_module.agent_tools.agent_tools import write_code_tool
import os # Import os for cleanup if needed

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

def test_write_code_tool():
    """Tests the write_code_tool functionality."""
    print("\n--- Testing write_code_tool ---")
    try:
        # Define the test file path relative to the project root
        test_file_path = project_root / "test_output.txt"
        test_content = "This is a test content written by write_code_tool from main.py."
        # The tool expects keyword arguments 'file_path' and 'text'
        # Note: WriteFileTool expects file_path as a string
        write_code_tool.run(tool_input={"file_path": str(test_file_path), "text": test_content})
        print(f"Successfully wrote to {test_file_path}")
        # Optional: Clean up the test file
        # try:
        #     os.remove(test_file_path)
        #     print(f"Cleaned up {test_file_path}")
        # except OSError as e:
        #     print(f"Error cleaning up test file: {e}")
    except Exception as e:
        print(f"Error testing write_code_tool: {e}")
    print("-----------------------------")

if __name__ == "__main__":
    print(f"Running script from project root: {project_root}")
    run_architect_agent_example()
    test_write_code_tool()
