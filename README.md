# Was ist Seife? 🧼

Not the SOAP API you wanted, but the soap API you need.

Selbstgehostete Webapp zum Bewerten der Toilettenhygiene von Restaurants & Co.
Flask + SQLite, Docker, Heimnetz. DB liegt in `./data/seife.db`.

```sh
docker compose up --build -d   # → http://localhost:8000
python test_app.py             # Tests
```

## Veröffentlichen auf github.io

„🌐 Veröffentlichen" committet alle Bewertungen als Retro-HTML-Seite per
GitHub-API nach `docs/index.html` (Vorschau: `/export`). Einmalig:

1. Repo public auf GitHub pushen, Pages: Branch `main`, Ordner `/docs`
2. Fine-grained Token nur für dieses Repo, **Contents: Read and write**
3. `.env` anlegen (gitignored): `GITHUB_TOKEN=…` und `GITHUB_REPO=<user>/was-ist-seife`

**Achtung:** Die Seite ist öffentlich — inklusive Koordinaten und Notizen.
