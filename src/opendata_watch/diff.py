"""Compare the current catalog snapshot with the previous one and describe the changes."""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import Dataset, Resource

# Snapshot format kept in state.json: {dataset_id: {"title", "modified", "resources": {id: last_modified}}}
Snapshot = dict[str, dict]


@dataclass
class Change:
    kind: str  # "new" | "updated"
    dataset: Dataset
    new_resources: list[Resource] = field(default_factory=list)
    updated_resources: list[Resource] = field(default_factory=list)


def snapshot(datasets: list[Dataset]) -> Snapshot:
    return {
        d.id: {
            "title": d.title,
            "modified": d.modified,
            "resources": {r.id: r.last_modified for r in d.resources},
        }
        for d in datasets
    }


def compare(previous: Snapshot, datasets: list[Dataset]) -> list[Change]:
    """List datasets that are new, or whose files were added or replaced, since ``previous``.

    A metadata edit that touches no file (e.g. a typo fix in the description) is not reported:
    people subscribe to this to learn about new data, not catalog housekeeping.
    """
    changes: list[Change] = []
    for d in datasets:
        before = previous.get(d.id)
        if before is None:
            changes.append(Change("new", d, new_resources=list(d.resources)))
            continue
        if before["modified"] == d.modified:
            continue
        old = before.get("resources", {})
        added = [r for r in d.resources if r.id not in old]
        replaced = [r for r in d.resources if r.id in old and old[r.id] != r.last_modified]
        if added or replaced:
            changes.append(Change("updated", d, added, replaced))
    return changes


def merge(previous: Snapshot, datasets: list[Dataset]) -> Snapshot:
    """New state = old state with the datasets seen this run overwritten.

    Datasets that fell out of the search window are kept, so they are not reported as
    "new" again if they reappear later.
    """
    merged = dict(previous)
    merged.update(snapshot(datasets))
    return merged
