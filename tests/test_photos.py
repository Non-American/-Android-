import io

from PIL import Image

from tests.conftest import TAGS_A, TAGS_B


def img(fmt="PNG", size=(40, 30), exif=None):
    b = io.BytesIO()
    kw = {"exif": exif} if exif is not None else {}
    Image.new("RGB", size, (200, 50, 50)).save(b, fmt, **kw)
    return b.getvalue()


def upload(client, u, data, name="a.png"):
    return client.post("/api/photos", files={"file": (name, data, "application/octet-stream")}, headers=u.h)


def test_upload_reencodes_and_strips_metadata(client, make_user):
    u = make_user()
    exif = Image.Exif()
    exif[0x010F] = "TestCam"
    exif[0x8825] = {1: "N", 2: (55.0, 45.0, 0.0)}  # GPS
    r = upload(client, u, img("JPEG", exif=exif), "a.jpg")
    assert r.status_code == 200, r.text
    url = r.json()[0]["url"]
    served = client.get(url)
    assert served.status_code == 200
    out = Image.open(io.BytesIO(served.content))
    assert out.format == "JPEG" and len(out.getexif()) == 0


def test_large_image_is_downscaled(client, make_user):
    u = make_user()
    url = upload(client, u, img(size=(3000, 2000))).json()[0]["url"]
    assert max(Image.open(io.BytesIO(client.get(url).content)).size) == 1600


def test_rejects_non_images_and_limit(client, make_user):
    u = make_user()
    assert upload(client, u, b"definitely not an image").status_code == 415
    assert upload(client, u, img("GIF")).status_code == 415
    for _ in range(6):
        assert upload(client, u, img()).status_code == 200
    assert upload(client, u, img()).status_code == 409


def test_reorder_delete_and_feed_shows_photos(client, make_user):
    a, b = make_user("A", TAGS_A), make_user("B", TAGS_B)
    upload(client, b, img())
    photos = upload(client, b, img()).json()
    second = photos[1]["id"]
    photos = client.post(f"/api/photos/{second}/main", headers=b.h).json()
    assert photos[0]["id"] == second
    assert client.get("/api/feed", headers=a.h).json()[0]["photos"] == [p["url"] for p in photos]
    assert client.delete(f"/api/photos/{second}", headers=a.h).status_code == 404  # чужое фото
    left = client.delete(f"/api/photos/{second}", headers=b.h).json()
    assert [p["id"] for p in left] == [photos[1]["id"]]
    assert client.get(photos[0]["url"]).status_code == 404
