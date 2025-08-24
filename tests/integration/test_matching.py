from app.models.assignment import CareAssignment


def test_open_friend_requests_list(client, login_as, sample_data):
    login_as(sample_data["sitter"])
    rv = client.get("/requests/friends/open")
    assert rv.status_code == 200
    assert b"Apply" in rv.data
    assert sample_data["pet"].name.encode() in rv.data

def test_apply_requires_sitter_role(client, login_as, sample_data, future_interval):
    login_as(sample_data["owner"])
    start_s, end_s = future_interval
    rv = client.post(
        f"/requests/{sample_data['request'].id}/apply",
        data={"start_at": start_s, "end_at": end_s, "sitter_note": "hi"},
        follow_redirects=True,
    )
    assert rv.status_code in (403, 200, 302)
    if rv.status_code != 403:
        assert (
            b"Sitter" in rv.data
            or b"role" in rv.data
            or b"permission" in rv.data
            or b"not allowed" in rv.data
        )

def test_apply_not_friends(client, login_as, sample_data, future_interval):
    login_as(sample_data["stranger"])
    start_s, end_s = future_interval
    rv = client.post(
        f"/requests/{sample_data['request'].id}/apply",
        data={"start_at": start_s, "end_at": end_s},
        follow_redirects=True,
    )
    assert rv.status_code in (200, 302, 403)
    assert b"friend" in rv.data.lower() or b"friends" in rv.data.lower()

def test_apply_success_and_overlap_block(client, login_as, sample_data, future_interval):
    login_as(sample_data["sitter"])
    start_s, end_s = future_interval
    rv = client.post(
        f"/requests/{sample_data['request'].id}/apply",
        data={"start_at": start_s, "end_at": end_s, "sitter_note": "ok"},
        follow_redirects=True,
    )
    assert rv.status_code in (200, 302)

    q = CareAssignment.query.filter_by(
        care_request_id=sample_data["request"].id,
        sitter_id=sample_data["sitter"].id,
    )
    rows = q.all()
    assert len(rows) == 1
    a = rows[0]
    assert a.status in ("pending", "active", "assigned", "awaiting_review")

    rv2 = client.post(
        f"/requests/{sample_data['request'].id}/apply",
        data={"start_at": start_s, "end_at": end_s},
        follow_redirects=True,
    )
    assert rv2.status_code in (200, 302, 400, 403, 409)
    assert q.count() == 1 