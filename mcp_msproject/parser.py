"""MS Project XML parser and writer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from lxml import etree

# MS Project XML uses this namespace
NS = "http://schemas.microsoft.com/project"
NSP = f"{{{NS}}}"


def _tag(name: str) -> str:
    return f"{NSP}{name}"


def _find(element: etree._Element, name: str) -> Optional[etree._Element]:
    return element.find(_tag(name))


def _text(element: etree._Element, name: str, default: str = "") -> str:
    el = _find(element, name)
    return el.text if el is not None and el.text else default


def _int(element: etree._Element, name: str, default: int = 0) -> int:
    try:
        return int(_text(element, name, str(default)))
    except ValueError:
        return default


def _float(element: etree._Element, name: str, default: float = 0.0) -> float:
    try:
        return float(_text(element, name, str(default)))
    except ValueError:
        return default


def _parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    # MS Project XML dates: "2024-01-15T08:00:00"
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _format_date(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


@dataclass
class Task:
    uid: int
    id: int
    name: str
    percent_complete: int = 0
    percent_work_complete: int = 0
    duration: str = ""
    start: Optional[datetime] = None
    finish: Optional[datetime] = None
    milestone: bool = False
    summary: bool = False
    outline_level: int = 0
    outline_number: str = ""
    notes: str = ""
    work: str = ""
    remaining_work: str = ""
    priority: int = 500
    wbs: str = ""

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "id": self.id,
            "name": self.name,
            "percent_complete": self.percent_complete,
            "percent_work_complete": self.percent_work_complete,
            "duration": self.duration,
            "start": _format_date(self.start),
            "finish": _format_date(self.finish),
            "milestone": self.milestone,
            "summary": self.summary,
            "outline_level": self.outline_level,
            "outline_number": self.outline_number,
            "wbs": self.wbs,
            "notes": self.notes,
            "priority": self.priority,
        }


@dataclass
class Resource:
    uid: int
    id: int
    name: str
    email: str = ""
    type: int = 1  # 1=Work, 2=Material, 3=Cost

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "type": self.type,
        }


@dataclass
class Assignment:
    uid: int
    task_uid: int
    resource_uid: int
    percent_work_complete: int = 0
    units: float = 1.0

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "task_uid": self.task_uid,
            "resource_uid": self.resource_uid,
            "percent_work_complete": self.percent_work_complete,
            "units": self.units,
        }


@dataclass
class Project:
    name: str = ""
    title: str = ""
    author: str = ""
    company: str = ""
    start_date: Optional[datetime] = None
    finish_date: Optional[datetime] = None
    status_date: Optional[datetime] = None
    currency_symbol: str = "€"
    tasks: list[Task] = field(default_factory=list)
    resources: list[Resource] = field(default_factory=list)
    assignments: list[Assignment] = field(default_factory=list)
    _tree: Optional[etree._ElementTree] = field(default=None, repr=False)
    _root: Optional[etree._Element] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        total = [t for t in self.tasks if not t.summary and not t.milestone]
        completed = sum(t.percent_complete for t in total)
        avg_progress = round(completed / len(total), 1) if total else 0.0
        return {
            "name": self.name,
            "title": self.title,
            "author": self.author,
            "company": self.company,
            "start_date": _format_date(self.start_date),
            "finish_date": _format_date(self.finish_date),
            "status_date": _format_date(self.status_date),
            "currency_symbol": self.currency_symbol,
            "task_count": len(self.tasks),
            "resource_count": len(self.resources),
            "average_progress_percent": avg_progress,
        }


def load(path: str | Path) -> Project:
    """Load an MS Project XML file and return a Project object."""
    path = Path(path)
    tree = etree.parse(str(path))
    root = tree.getroot()

    project = Project(_tree=tree, _root=root)

    # Project-level fields
    project.name = path.stem
    project.title = _text(root, "Title")
    project.author = _text(root, "Author")
    project.company = _text(root, "Company")
    project.start_date = _parse_date(_text(root, "StartDate"))
    project.finish_date = _parse_date(_text(root, "FinishDate"))
    project.status_date = _parse_date(_text(root, "StatusDate"))
    project.currency_symbol = _text(root, "CurrencySymbol", "€")

    # Tasks
    tasks_el = _find(root, "Tasks")
    if tasks_el is not None:
        for task_el in tasks_el.findall(_tag("Task")):
            uid = _int(task_el, "UID")
            if uid == 0:  # skip project summary task
                continue
            task = Task(
                uid=uid,
                id=_int(task_el, "ID"),
                name=_text(task_el, "Name"),
                percent_complete=_int(task_el, "PercentComplete"),
                percent_work_complete=_int(task_el, "PercentWorkComplete"),
                duration=_text(task_el, "Duration"),
                start=_parse_date(_text(task_el, "Start")),
                finish=_parse_date(_text(task_el, "Finish")),
                milestone=_text(task_el, "Milestone") == "1",
                summary=_text(task_el, "Summary") == "1",
                outline_level=_int(task_el, "OutlineLevel"),
                outline_number=_text(task_el, "OutlineNumber"),
                notes=_text(task_el, "Notes"),
                work=_text(task_el, "Work"),
                remaining_work=_text(task_el, "RemainingWork"),
                priority=_int(task_el, "Priority", 500),
                wbs=_text(task_el, "WBS"),
            )
            project.tasks.append(task)

    # Resources
    resources_el = _find(root, "Resources")
    if resources_el is not None:
        for res_el in resources_el.findall(_tag("Resource")):
            uid = _int(res_el, "UID")
            if uid == 0:
                continue
            resource = Resource(
                uid=uid,
                id=_int(res_el, "ID"),
                name=_text(res_el, "Name"),
                email=_text(res_el, "EmailAddress"),
                type=_int(res_el, "Type", 1),
            )
            project.resources.append(resource)

    # Assignments
    assignments_el = _find(root, "Assignments")
    if assignments_el is not None:
        for asgn_el in assignments_el.findall(_tag("Assignment")):
            assignment = Assignment(
                uid=_int(asgn_el, "UID"),
                task_uid=_int(asgn_el, "TaskUID"),
                resource_uid=_int(asgn_el, "ResourceUID"),
                percent_work_complete=_int(asgn_el, "PercentWorkComplete"),
                units=_float(asgn_el, "Units", 1.0),
            )
            project.assignments.append(assignment)

    return project


def update_task_progress(
    path: str | Path,
    updates: list[dict],  # [{"uid": int, "percent_complete": int}, ...]
    output_path: str | Path | None = None,
) -> list[dict]:
    """
    Update PercentComplete (and optionally PercentWorkComplete) for given task UIDs.
    Saves back to the same file unless output_path is provided.
    Returns list of updated tasks as dicts.
    """
    path = Path(path)
    tree = etree.parse(str(path))
    root = tree.getroot()

    uid_map = {u["uid"]: u for u in updates}
    updated = []

    tasks_el = _find(root, "Tasks")
    if tasks_el is None:
        return []

    for task_el in tasks_el.findall(_tag("Task")):
        uid = _int(task_el, "UID")
        if uid not in uid_map:
            continue

        upd = uid_map[uid]
        pct = max(0, min(100, int(upd["percent_complete"])))

        # Update PercentComplete
        pc_el = _find(task_el, "PercentComplete")
        if pc_el is None:
            pc_el = etree.SubElement(task_el, _tag("PercentComplete"))
        pc_el.text = str(pct)

        # Update PercentWorkComplete if provided, else mirror PercentComplete
        pwc_val = upd.get("percent_work_complete", pct)
        pwc_el = _find(task_el, "PercentWorkComplete")
        if pwc_el is None:
            pwc_el = etree.SubElement(task_el, _tag("PercentWorkComplete"))
        pwc_el.text = str(pwc_val)

        updated.append({
            "uid": uid,
            "name": _text(task_el, "Name"),
            "percent_complete": pct,
            "percent_work_complete": pwc_val,
        })

    dest = Path(output_path) if output_path else path
    tree.write(str(dest), xml_declaration=True, encoding="UTF-8", pretty_print=True)

    return updated
