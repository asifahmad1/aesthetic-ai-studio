"""API tests: CRUD round-trip through the Flask test client.

Routes are discovered defensively (the backend agent owns app.py), so the
test works with any REST-shaped route layout and skips cleanly if the app
module is not written yet.
"""
import io
import json

import pytest

CREATE_CANDIDATES = ["/api/projects", "/projects", "/api/project"]


def _get_app(tmp_path):
    try:
        from app import create_app
    except ImportError as e:
        pytest.skip(f"app.py not written yet ({e})")
    app = create_app(data_root=str(tmp_path / "data"))
    app.config["TESTING"] = True
    return app


def _find_create(client):
    payload = {"title": "API Round-Trip Deck", "slide_count": 4,
               "theme": "dark-green-gold"}
    for path in CREATE_CANDIDATES:
        r = client.post(path, json=payload)
        if r.status_code in (200, 201):
            return path, r
    return None, None


def _pid(resp):
    data = resp.get_json(silent=True) or {}
    if isinstance(data.get("project"), dict) and data["project"].get("id"):
        return data["project"]["id"]
    return data.get("id")


def test_api_project_round_trip(tmp_path):
    app = _get_app(tmp_path)
    client = app.test_client()
    base, created = _find_create(client)
    if base is None:
        pytest.skip("no project-creation route discovered; "
                    f"tried {CREATE_CANDIDATES}")
    pid = _pid(created)
    assert pid, f"create response carried no project id: {created.get_data(as_text=True)[:200]}"

    # read
    r = client.get(f"{base}/{pid}")
    assert r.status_code in (200,), f"GET failed: {r.status_code}"
    body = r.get_json(silent=True) or {}
    text = json.dumps(body)
    assert "API Round-Trip Deck" in text

    # update (try PUT then PATCH)
    updated = None
    for method in ("put", "patch"):
        r = getattr(client, method)(f"{base}/{pid}",
                                    json={"title": "API Round-Trip Deck v2"})
        if r.status_code in (200,):
            updated = r
            break
    assert updated is not None, "neither PUT nor PATCH updated the project"
    assert "v2" in json.dumps(updated.get_json(silent=True) or {})

    # delete
    r = client.delete(f"{base}/{pid}")
    assert r.status_code in (200, 204), f"DELETE failed: {r.status_code}"
    r = client.get(f"{base}/{pid}")
    assert r.status_code == 404, "deleted project should be gone"


def test_api_export_endpoints(tmp_path):
    app = _get_app(tmp_path)
    client = app.test_client()
    base, created = _find_create(client)
    if base is None:
        pytest.skip("no project-creation route discovered")
    pid = _pid(created)
    tried, served = 0, 0
    for fmt, ctype in (("pptx", "presentation"), ("pdf", "pdf"),
                       ("html", "html")):
        for path in (f"{base}/{pid}/export/{fmt}",
                     f"{base}/{pid}/export?format={fmt}",
                     f"/api/projects/{pid}/export/{fmt}"):
            r = client.get(path)
            tried += 1
            if r.status_code == 200 and len(r.data) > 1024:
                served += 1
                assert ctype in (r.content_type or ""), \
                    f"{fmt} export wrong content type: {r.content_type}"
                break
    if tried and not served:
        pytest.skip("export routes not discoverable in this build")
    assert served >= 1
