import os
import re
from pathlib import Path

from mcp.server.mcpserver import MCPServer

EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".c", ".h", ".cpp", ".hpp", ".java", ".go", ".rs", ".sh", ".md"}
MAX_RESULTS = 200

mcp = MCPServer("devtools")

@mcp.tool()
def find_todos() -> str:
    """
    List the TODO and FIXME comments of the source files in the current directory.

    :return: one `path:line: text` per line (at most 200)
    """
    found = []
    for root, dirs, files in os.walk("."):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            path = Path(root, name)
            if name.startswith(".") or path.suffix not in EXTENSIONS:
                continue
            try:
                lines = path.read_text(errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, 1):
                if re.search(r"TODO|FIXME", line):
                    found.append(f"{path}:{number}: {line.strip()[:200]}")
                    if len(found) >= MAX_RESULTS:
                        return "\n".join(found)
    return "\n".join(found) or "No TODO or FIXME found"

if __name__ == "__main__":
    mcp.run()
