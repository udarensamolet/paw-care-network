from flask import url_for

def test_home_access(client):
    rv = client.get("/")
    assert rv.status_code == 200
    assert b"Find trusted sitters" in rv.data

def test_dashboard_requires_login(client):
    rv = client.get("/dashboard", follow_redirects=False)
    assert rv.status_code in (301, 302)

def test_dashboard_counts(client, login_as, sample_data):
    login_as(sample_data["owner"])
    rv = client.get("/dashboard")
    assert rv.status_code == 200
    assert b"My Pets" in rv.data
    assert b"Care Requests" in rv.data
    assert b"Friends" in rv.data