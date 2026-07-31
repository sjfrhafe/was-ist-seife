import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.pop("GITHUB_TOKEN", None)  # nie gegen die echte API testen
os.environ.pop("GITHUB_REPO", None)

from app import app  # noqa: E402


def test_crud():
    client = app.test_client()

    assert "Noch keine Bewertungen" in client.get("/").get_data(as_text=True)

    antwort = client.post("/neu", data={
        "name": "Testcafé", "adresse": "Teststr. 1", "lat": "51,23", "lng": "6.79",
        "sauberkeit": "4", "sterne": "5", "seife": "Sensor",
        "beschilderung_sichtbar": "1", "bewertungszeitpunkt": "2026-07-31T12:30",
    }, follow_redirects=True)
    seite = antwort.get_data(as_text=True)
    assert "Testcafé" in seite and "★★★★★" in seite and "51.23" in seite
    assert "2026-07-31 12:30" in seite

    assert client.post("/neu", data={"name": ""}).status_code == 400

    seite = client.get("/export").get_data(as_text=True)
    assert "Testcafé" in seite and "<marquee" in seite

    antwort = client.post("/veroeffentlichen")
    assert antwort.status_code == 500
    assert "GITHUB_TOKEN" in antwort.get_data(as_text=True)

    antwort = client.post("/1/bearbeiten", data={"name": "Testbar", "sterne": "2"},
                          follow_redirects=True)
    seite = antwort.get_data(as_text=True)
    assert "Testbar" in seite and "★★☆☆☆" in seite

    client.post("/1/loeschen")
    assert client.get("/1").status_code == 404


if __name__ == "__main__":
    test_crud()
    print("OK")
