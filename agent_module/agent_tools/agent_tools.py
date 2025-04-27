from langchain_community.tools.file_management import WriteFileTool

# Tool instance for writing/modifying files
write_code_tool = WriteFileTool()

# You can add more tools here as needed
# from langchain_community.tools.file_management import ReadFileTool
# read_code_tool = ReadFileTool()

__all__ = ["write_code_tool"]
