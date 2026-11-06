"""Quick smoke test for the parser (no pytest required)."""

import json
from pathlib import Path
from mcp_msproject import parser

SAMPLE = Path(__file__).parent / "sample_project.xml"


def test_load():
    project = parser.load(SAMPLE)
    assert project.title == "Progetto Alpha"
    assert len(project.tasks) > 0
    print("✓ load() OK —", len(project.tasks), "tasks,", len(project.resources), "resources")


def test_summary():
    project = parser.load(SAMPLE)
    d = project.to_dict()
    print("✓ summary:", json.dumps(d, indent=2, ensure_ascii=False))


def test_filter():
    project = parser.load(SAMPLE)
    work = [t for t in project.tasks if not t.summary and not t.milestone]
    not_started = [t for t in work if t.percent_complete == 0]
    print(f"✓ filter: {len(not_started)} task non avviati")
    for t in not_started:
        print(f"   - [{t.uid}] {t.name}")


def test_update(tmp_path=None):
    import shutil, tempfile
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        tmp = Path(f.name)
    shutil.copy(SAMPLE, tmp)

    updated = parser.update_task_progress(
        path=tmp,
        updates=[
            {"uid": 9, "percent_complete": 25},
            {"uid": 10, "percent_complete": 10},
        ],
    )
    print("✓ update:", updated)

    # verify
    project = parser.load(tmp)
    for t in project.tasks:
        if t.uid in (9, 10):
            print(f"   [{t.uid}] {t.name}: {t.percent_complete}%")
    tmp.unlink()


if __name__ == "__main__":
    test_load()
    test_summary()
    test_filter()
    test_update()
    print("\nTutti i test passati.")
