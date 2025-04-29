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
# Import _gather_image_blocks as well
from agent_module.architect_agent import ArchitectAgent, _gather_image_blocks
from agent_module.agent_tools.agent_tools import write_file # Keep if needed, otherwise remove

# Ensure required environment variables are set (optional but good practice)
required_vars = [
    "LANGCHAIN_TRACING_V2",
    "LANGCHAIN_ENDPOINT",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_PROJECT",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "REACT_NATIVE_PROJECT_ROOT_FOLDER",
]
for var in required_vars:
    if var not in os.environ:
        raise EnvironmentError(
            f"Required environment variable '{var}' not found. "
            "Ensure it is set in your .env file or environment."
        )


def run_architect_agent_example():
    """Runs the example usage of the ArchitectAgent iteratively."""
    print("--- Running Architect Agent Example ---")
    image_folder = project_root / "zbase_rn_project" / "ui_images"
    max_iterations = 15 # Safety break

    if not image_folder.exists() or not image_folder.is_dir():
        print(f"Error: Image folder not found at {image_folder}")
        print("Please ensure the 'zbase_rn_project/ui_images' directory exists relative to main.py")
        return

    try:
        agent = ArchitectAgent()

        # --- Iteration 1 Setup ---
        print(f"Gathering images from: {image_folder}")
        image_blocks = _gather_image_blocks(image_folder)
        initial_instruction = "Analyze the provided UI images and generate an initial development plan. Create the first set of tasks."
        current_input = [{"type": "text", "text": initial_instruction}] + image_blocks
        current_iteration = 1
        final_result = "Agent did not complete within max iterations."

        # --- Iteration Loop ---
        while current_iteration <= max_iterations:
            print(f"--- Starting Agent Iteration {current_iteration} ---")
            agent_response = agent(user_input=current_input, iteration=current_iteration)

            print(f"--- Agent Response (Iteration {current_iteration}) ---")
            print(agent_response)
            print("----------------------------------------------------")

            if "TASK COMPLETE" in agent_response:
                final_result = f"Agent completed successfully in {current_iteration} iterations."
                print(final_result)
                break # Exit the loop

            # Prepare input for the next iteration
            current_input = agent_response
            current_iteration += 1

            if current_iteration > max_iterations:
                print(f"Agent reached maximum iterations ({max_iterations}).")
                break

        print(f"--- Final Result ---")
        print(final_result)
        print("--------------------")


    except FileNotFoundError as e:
        print(f"Error during agent execution: {e}")
    except ValueError as e:
        print(f"Error during agent execution: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Optionally print traceback for debugging
        # import traceback
        # traceback.print_exc()

if __name__ == "__main__":
    print(f"Running script from project root: {project_root}")
    run_architect_agent_example()
