from langchain_community.tools.file_management import WriteFileTool
from langchain_community.tools.shell import ShellTool

# Tool instance for writing/modifying files
write_code_tool = WriteFileTool()

# Tool instance for executing PowerShell commands
# Configure to use PowerShell specifically on Windows
powershell_tool = ShellTool(command_prefix="powershell.exe -Command ")

__all__ = ["write_code_tool", "powershell_tool"]
