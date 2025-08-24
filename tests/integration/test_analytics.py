def test_analytics_page_renders(client, login_as, sample_data):
    login_as(sample_data["owner"])
    rv = client.get("/analytics")
    assert rv.status_code == 200
    assert b"Plotly.newPlot" in rv.data
    assert b"Requests by status" in rv.data