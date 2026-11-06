# mcp-msproject

MCP server for reading and updating **Microsoft Project XML files** (`.xml` exported from MS Project).

Exposes 4 tools to Claude:

| Tool | Description |
|---|---|
| `read_project` | Load full project data: tasks, resources, assignments |
| `get_tasks` | List tasks with filters (% complete, name, milestones) |
| `get_project_summary` | Progress summary (SAL): overall %, tasks by status |
| `update_task_progress` | Update completion % for one or more tasks and save |

## Requirements

- Python ≥ 3.11
- [Claude Desktop](https://claude.ai/download)
- Microsoft Project (to export/import `.xml` files)

> **No Java required.** Works with MS Project's native XML export format.

## Installation

```bash
pip install mcp-msproject
```

Or install from source:

```bash
git clone https://github.com/rmpugliese/mcp-msproject.git
cd mcp-msproject
pip install -e .
```

## Installation with SSE support

To use the HTTP/SSE transport (for clients that do not launch local processes):

```bash
pip install "mcp-msproject[sse]"
```

## Claude Desktop configuration

Edit the `claude_desktop_config.json` file for your platform:

| Platform | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

**macOS / Linux:**

```json
{
  "mcpServers": {
    "msproject": {
      "command": "python3",
      "args": ["-m", "mcp_msproject.server"]
    }
  }
}
```

**Windows:**

```json
{
  "mcpServers": {
    "msproject": {
      "command": "python",
      "args": ["-m", "mcp_msproject.server"]
    }
  }
}
```

Then restart Claude Desktop.

### SSE transport (HTTP — for other MCP clients)

Start the server in SSE mode:

```bash
python3 -m mcp_msproject.server --transport sse --host 127.0.0.1 --port 8000
```

The server exposes two endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /sse` | SSE event stream (client connects here) |
| `POST /messages/` | Client sends messages here |

Configure your MCP client to connect to `http://127.0.0.1:8000/sse`.

> **Note:** SSE transport requires the optional dependencies: `pip install "mcp-msproject[sse]"`

## MS Project workflow

### Export from MS Project

1. Open your project in Microsoft Project
2. **File → Save As**
3. In the *Save as type* dropdown select **XML Format (\*.xml)**
4. Choose a destination folder and save

### Update via Claude

Ask Claude things like:

> *"Read the project at /path/to/project.xml and show me the progress status"*

> *"Update task 7 to 60% complete in /path/to/project.xml"*

> *"Which tasks are not started yet in /path/to/project.xml?"*

### Reimport into MS Project

1. **File → Open**
2. Select the updated `.xml` file
3. MS Project will ask how to handle the import — choose **Import** (not **Append**)
4. Follow the import wizard: map fields as needed (usually defaults work fine)

> **Tip:** Keep a backup of the original `.mpp` file before reimporting.

## Example usage

Ask Claude:

> *"Read the project at /path/to/project.xml and show me the progress status"*

> *"Update task 7 (Design database) to 60% complete in /path/to/project.xml"*

## Sample project

A sample XML file (`sample_project.xml`) is included for testing.

## License

MIT
