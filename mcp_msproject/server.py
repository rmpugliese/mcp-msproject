"""MCP server for Microsoft Project XML files."""

from __future__ import annotations

import json
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

from . import parser

app = Server("mcp-msproject")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="read_project",
            description=(
                "Reads a Microsoft Project XML file (.xml exported from MS Project) "
                "and returns high-level project information together with all tasks, "
                "resources and assignments."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or relative path to the .xml MS Project file.",
                    }
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="get_tasks",
            description=(
                "Returns the task list of a Microsoft Project XML file. "
                "Supports optional filters: minimum and maximum percent_complete, "
                "include/exclude summary tasks and milestones, search by name substring."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the .xml MS Project file.",
                    },
                    "min_percent": {
                        "type": "integer",
                        "description": "Minimum percent complete (0-100). Default 0.",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "max_percent": {
                        "type": "integer",
                        "description": "Maximum percent complete (0-100). Default 100.",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "include_summary": {
                        "type": "boolean",
                        "description": "Include summary (parent) tasks. Default false.",
                    },
                    "include_milestones": {
                        "type": "boolean",
                        "description": "Include milestone tasks. Default true.",
                    },
                    "name_filter": {
                        "type": "string",
                        "description": "Case-insensitive substring to filter task names.",
                    },
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="get_project_summary",
            description=(
                "Returns a concise progress summary of a Microsoft Project XML file: "
                "overall percent complete, count of tasks by status (not started, "
                "in progress, completed), and project dates."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the .xml MS Project file.",
                    }
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="update_task_progress",
            description=(
                "Updates the percent_complete of one or more tasks in a Microsoft "
                "Project XML file and saves the result. "
                "Pass a list of {uid, percent_complete} objects. "
                "The file is overwritten in place unless output_path is specified."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the .xml MS Project file.",
                    },
                    "updates": {
                        "type": "array",
                        "description": "List of task updates.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "uid": {
                                    "type": "integer",
                                    "description": "Task UID (as returned by get_tasks).",
                                },
                                "percent_complete": {
                                    "type": "integer",
                                    "description": "New completion percentage (0-100).",
                                    "minimum": 0,
                                    "maximum": 100,
                                },
                            },
                            "required": ["uid", "percent_complete"],
                        },
                        "minItems": 1,
                    },
                    "output_path": {
                        "type": "string",
                        "description": (
                            "Optional path to save the updated file. "
                            "If omitted, overwrites the original."
                        ),
                    },
                },
                "required": ["file_path", "updates"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

@app.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent]:

    try:
        if name == "read_project":
            return await _read_project(arguments)
        elif name == "get_tasks":
            return await _get_tasks(arguments)
        elif name == "get_project_summary":
            return await _get_project_summary(arguments)
        elif name == "update_task_progress":
            return await _update_task_progress(arguments)
        else:
            return _error(f"Unknown tool: {name}")
    except FileNotFoundError as e:
        return _error(f"File not found: {e}")
    except Exception as e:
        return _error(f"Error: {type(e).__name__}: {e}")


async def _read_project(args: dict) -> list[types.TextContent]:
    project = parser.load(args["file_path"])
    result = {
        "project": project.to_dict(),
        "tasks": [t.to_dict() for t in project.tasks],
        "resources": [r.to_dict() for r in project.resources],
        "assignments": [a.to_dict() for a in project.assignments],
    }
    return _ok(result)


async def _get_tasks(args: dict) -> list[types.TextContent]:
    project = parser.load(args["file_path"])

    min_pct = args.get("min_percent", 0)
    max_pct = args.get("max_percent", 100)
    include_summary = args.get("include_summary", False)
    include_milestones = args.get("include_milestones", True)
    name_filter = args.get("name_filter", "").lower()

    tasks = project.tasks
    if not include_summary:
        tasks = [t for t in tasks if not t.summary]
    if not include_milestones:
        tasks = [t for t in tasks if not t.milestone]
    tasks = [t for t in tasks if min_pct <= t.percent_complete <= max_pct]
    if name_filter:
        tasks = [t for t in tasks if name_filter in t.name.lower()]

    return _ok({"tasks": [t.to_dict() for t in tasks], "count": len(tasks)})


async def _get_project_summary(args: dict) -> list[types.TextContent]:
    project = parser.load(args["file_path"])

    work_tasks = [t for t in project.tasks if not t.summary and not t.milestone]
    not_started = [t for t in work_tasks if t.percent_complete == 0]
    in_progress = [t for t in work_tasks if 0 < t.percent_complete < 100]
    completed = [t for t in work_tasks if t.percent_complete == 100]
    milestones = [t for t in project.tasks if t.milestone]
    milestones_done = [t for t in milestones if t.percent_complete == 100]

    total = len(work_tasks)
    avg = round(sum(t.percent_complete for t in work_tasks) / total, 1) if total else 0.0

    summary = {
        "project_name": project.name,
        "title": project.title,
        "author": project.author,
        "start_date": parser._format_date(project.start_date),
        "finish_date": parser._format_date(project.finish_date),
        "status_date": parser._format_date(project.status_date),
        "overall_percent_complete": avg,
        "tasks": {
            "total": total,
            "not_started": len(not_started),
            "in_progress": len(in_progress),
            "completed": len(completed),
        },
        "milestones": {
            "total": len(milestones),
            "completed": len(milestones_done),
        },
        "resources_count": len(project.resources),
    }
    return _ok(summary)


async def _update_task_progress(args: dict) -> list[types.TextContent]:
    updated = parser.update_task_progress(
        path=args["file_path"],
        updates=args["updates"],
        output_path=args.get("output_path"),
    )
    dest = args.get("output_path") or args["file_path"]
    return _ok({
        "updated_tasks": updated,
        "count": len(updated),
        "saved_to": str(Path(dest).resolve()),
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(data: dict) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


def _error(message: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps({"error": message}, ensure_ascii=False))]


def main() -> None:
    import asyncio
    from mcp.server.stdio import stdio_server

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
