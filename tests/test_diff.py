from opendata_watch.catalog import site_root, to_dataset
from opendata_watch.diff import compare, merge, snapshot

SITE = "https://catalog.example.jp"


def package(name="d1", modified="2026-01-01T00:00:00", resources=None, title="調達情報"):
    return {
        "name": name,
        "title": f" {title} ",
        "metadata_modified": modified,
        "organization": {"title": "練馬区"},
        "resources": resources
        if resources is not None
        else [{"id": "r1", "name": "契約一覧", "url": "https://x/r1.csv", "format": "csv",
               "last_modified": "2026-01-01T00:00:00"}],
    }


def ds(**kw):
    return to_dataset(package(**kw), SITE)


def test_to_dataset_normalizes_fields():
    d = ds()
    assert d.title == "調達情報"
    assert d.organization == "練馬区"
    assert d.page_url == "https://catalog.example.jp/dataset/d1"
    assert d.resources[0].format == "CSV"


def test_site_root():
    assert site_root("https://catalog.example.jp/api/3/action") == SITE


def test_new_dataset_is_reported_with_all_files():
    changes = compare({}, [ds()])
    assert [c.kind for c in changes] == ["new"]
    assert [r.id for r in changes[0].new_resources] == ["r1"]


def test_unchanged_dataset_is_silent():
    prev = snapshot([ds()])
    assert compare(prev, [ds()]) == []


def test_metadata_only_edit_is_ignored():
    prev = snapshot([ds()])
    assert compare(prev, [ds(modified="2026-02-01T00:00:00")]) == []


def test_added_file_is_reported():
    prev = snapshot([ds()])
    new_files = package()["resources"] + [
        {"id": "r2", "name": "2月分", "url": "https://x/r2.csv", "format": "CSV",
         "last_modified": "2026-02-01T00:00:00"}
    ]
    changes = compare(prev, [ds(modified="2026-02-01T00:00:00", resources=new_files)])
    assert changes[0].kind == "updated"
    assert [r.id for r in changes[0].new_resources] == ["r2"]
    assert changes[0].updated_resources == []


def test_replaced_file_is_reported():
    prev = snapshot([ds()])
    replaced = [dict(package()["resources"][0], last_modified="2026-03-01T00:00:00")]
    changes = compare(prev, [ds(modified="2026-03-01T00:00:00", resources=replaced)])
    assert [r.id for r in changes[0].updated_resources] == ["r1"]


def test_merge_keeps_datasets_that_left_the_search_window():
    prev = snapshot([ds(name="old")])
    merged = merge(prev, [ds(name="d1")])
    assert set(merged) == {"old", "d1"}
    # ...so "old" coming back later is not treated as new
    assert compare(merged, [ds(name="old")]) == []
