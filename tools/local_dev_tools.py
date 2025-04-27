# tools/local_dev_tools.py
# Defines the custom tools the agent can use to interact with the local environment.

import subprocess
import os
import pathlib
from typing import List, Optional

# --- File System Tools ---

def read_file(file_path: str) -> str:
    """
    Reads the content of a file relative to the base React Native project path.
    Args:
        file_path: The relative path to the file within the RN project (e.g., 'src/screens/HomeScreen.js').
    Returns:
        The content of the file as a string, or an error message if reading fails.
    """
    # Get base path from environment variable, default if not set
    base_path = os.getenv('BASE_RN_PROJECT_PATH', './base_react_native_project')
    # Construct the full path safely
    full_path = pathlib.Path(base_path).resolve() / file_path
    try:
        # Ensure the path is within the intended project directory (basic security check)
        if not str(full_path.resolve()).startswith(str(pathlib.Path(base_path).resolve())):
             return f"Error: Attempted to read file outside the project directory: {file_path}"
        # Read the file content
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"[Tool Action] Read file: {file_path}")
        return content
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

def write_file(file_path: str, content: str) -> str:
    """
    Writes content to a file relative to the base React Native project path.
    Creates parent directories if they don't exist. Overwrites existing files.
    Args:
        file_path: The relative path to the file within the RN project (e.g., 'src/screens/NewScreen.js').
        content: The string content to write to the file.
    Returns:
        A success message or an error message if writing fails.
    """
    base_path = os.getenv('BASE_RN_PROJECT_PATH', './base_react_native_project')
    full_path = pathlib.Path(base_path).resolve() / file_path
    try:
        # Ensure the path is within the intended project directory (basic security check)
        if not str(full_path.resolve()).startswith(str(pathlib.Path(base_path).resolve())):
             return f"Error: Attempted to write file outside the project directory: {file_path}"
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        # Write the file content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[Tool Action] Wrote file: {file_path}")
        return f"Successfully wrote content to {file_path}"
    except Exception as e:
        return f"Error writing file {file_path}: {str(e)}"

def list_files(directory_path: str = ".") -> List[str]:
    """
    Lists files and directories within a specified path relative to the base React Native project path.
    Args:
        directory_path: The relative directory path within the RN project (default is root '.'). E.g., 'src/components'.
    Returns:
        A list of file/directory names, or a list containing a single error message string.
    """
    base_path = os.getenv('BASE_RN_PROJECT_PATH', './base_react_native_project')
    full_path = pathlib.Path(base_path).resolve() / directory_path
    try:
         # Ensure the path is within the intended project directory (basic security check)
        if not str(full_path.resolve()).startswith(str(pathlib.Path(base_path).resolve())):
             return [f"Error: Attempted to list directory outside the project directory: {directory_path}"]
        # List directory contents
        entries = os.listdir(full_path)
        print(f"[Tool Action] Listed directory: {directory_path}")
        return entries
    except FileNotFoundError:
         return [f"Error: Directory not found at {directory_path}"]
    except Exception as e:
        # Return error as string within a list for consistency, though LLM might handle string better
        return [f"Error listing directory {directory_path}: {str(e)}"]

# --- Build & Test Tools ---

def run_tests() -> str:
    """
    Runs the test suite (e.g., 'npm test' or 'yarn test') in the base React Native project directory
    and returns the full console output (stdout and stderr).
    Returns:
        The combined stdout and stderr output from the test command as a single string.
    """
    base_path = os.getenv('BASE_RN_PROJECT_PATH', './base_react_native_project')
    # --- IMPORTANT: Configure your actual test command here ---
    command = "npm test" # Or "yarn test" or specific jest command
    print(f"[Tool Action] Running tests: '{command}' in '{base_path}'")
    try:
        # Execute the command, capture output, wait for completion (with timeout)
        result = subprocess.run(
            command,
            cwd=base_path,        # Run command in the RN project directory
            capture_output=True,  # Capture stdout and stderr
            text=True,            # Decode output as text
            shell=True,           # Easier for npm/yarn, but be mindful of security if command varies
            check=False,          # Don't raise error on non-zero exit code, just return output
            timeout=180           # Timeout in seconds (e.g., 3 minutes)
        )
        # Combine output for the agent
        output = (
            f"--- Test Execution Results ---\n"
            f"Exit Code: {result.returncode}\n"
            f"--- STDOUT ---\n{result.stdout}\n"
            f"--- STDERR ---\n{result.stderr}\n"
            f"------------------------------"
        )
        print(f"[Tool Action] Test run finished with exit code: {result.returncode}")
        return output
    except subprocess.TimeoutExpired:
        print("[Tool Error] Test command timed out.")
        return "Error: Test command timed out after 180 seconds."
    except Exception as e:
        print(f"[Tool Error] Exception running tests: {e}")
        return f"Error running tests: {str(e)}"

def run_on_emulator(platform: str = "android", timeout_sec: int = 90) -> str:
    """
    Attempts to build and launch the React Native app on a specified emulator platform ('android' or 'ios')
    and captures console output (stdout/stderr) for a limited time.
    NOTE: This is a simplified implementation for capturing build/initial run logs.
          It doesn't guarantee capturing all runtime errors if the process runs long.
    Args:
        platform: The target platform ('android' or 'ios'). Default: 'android'.
        timeout_sec: How long to attempt capturing output after starting the command. Default: 90 seconds.
    Returns:
        The combined stdout and stderr from the run command process as a single string.
    """
    base_path = os.getenv('BASE_RN_PROJECT_PATH', './base_react_native_project')
    # Determine the command based on platform
    if platform.lower() == "android":
        command = "npx react-native run-android"
    elif platform.lower() == "ios":
        command = "npx react-native run-ios" # May require specific simulator flags
    else:
        return f"Error: Unsupported platform '{platform}'. Use 'android' or 'ios'."

    print(f"[Tool Action] Running on emulator: '{command}' in '{base_path}' (timeout: {timeout_sec}s)")
    try:
        # Start the process. This command often keeps running (Metro bundler, etc.)
        process = subprocess.Popen(
            command,
            cwd=base_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True # Easier for npx command
        )

        # Attempt to capture output for the timeout duration
        stdout_data = ""
        stderr_data = ""
        try:
            # communicate() waits for process termination OR timeout
            stdout_data, stderr_data = process.communicate(timeout=timeout_sec)
            print(f"[Tool Action] Emulator run command finished with exit code: {process.returncode}")
        except subprocess.TimeoutExpired:
            # If timeout expires, the process is likely still running (e.g., Metro bundler)
            print(f"[Tool Action] Emulator run command timed out after {timeout_sec}s. Terminating process.")
            process.kill() # Terminate the process
            # Try to get any remaining output
            stdout_data, stderr_data = process.communicate()
            print("[Tool Action] Captured available output after timeout.")

        # Combine captured output
        output = (
            f"--- Emulator Run Output ({platform}) ---\n"
            # Note: Exit code might be None or from termination signal after timeout
            f"Exit Code: {process.returncode}\n"
            f"--- STDOUT ---\n{stdout_data}\n"
            f"--- STDERR ---\n{stderr_data}\n"
            f"------------------------------------"
        )
        return output

    except Exception as e:
        print(f"[Tool Error] Exception running on emulator ({platform}): {e}")
        return f"Error running on emulator ({platform}): {str(e)}"

# It's good practice to define __all__ if you want to control imports with '*'
# but ADK can often find tools without it if imported directly.
__all__ = ["read_file", "write_file", "list_files", "run_tests", "run_on_emulator"]
