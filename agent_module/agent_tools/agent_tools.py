import os
from langchain.tools import BaseTool
from langchain_community.tools.file_management import WriteFileTool, ReadFileTool
from langchain_community.tools.shell import ShellTool

# Tool instance for writing/modifying files
write_file = WriteFileTool()

# Tool instance for reading files
read_file = ReadFileTool()

# Tool instance for executing PowerShell commands
# Configure to use PowerShell specifically on Windows
powershell_tool = ShellTool(command_prefix="powershell.exe -Command ")

class ListSrcFolderTool(BaseTool):
    name: str = "list_src_folder"
    description: str = (
        "List all files recursively in the folder defined by the REACT_NATIVE_SOURCE_FOLDER environment variable."
    )

    def _run(self, tool_input=None) -> str:
        folder = os.getenv("REACT_NATIVE_SOURCE_FOLDER")
        if not folder:
            return "Environment variable REACT_NATIVE_SOURCE_FOLDER is not set."
        from subprocess import run, PIPE
        result = run(["ls", "-R"], cwd=folder, stdout=PIPE, stderr=PIPE, text=True, shell=False)
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout

    async def _arun(self) -> str:
        # Synchronous only
        raise NotImplementedError("list_src_folder does not support async")

list_src_folder = ListSrcFolderTool()

__all__ = ["write_file", "read_file", "powershell_tool", "list_src_folder"]
