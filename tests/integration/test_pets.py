from app.models.pet import Pet


def test_pets_list_shows_pet(client, login_as, sample_data):
    login_as(sample_data["owner"])
    rv = client.get("/pets")
    assert rv.status_code == 200
    assert sample_data["pet"].name.encode() in rv.data

def test_delete_pet_flow(client, login_as, sample_data):
    login_as(sample_data["owner"])
    pet_id = sample_data["pet"].id
    rv = client.post(f"/pets/{pet_id}/delete", follow_redirects=True)
    assert rv.status_code == 200
    assert not Pet.query.get(pet_id)