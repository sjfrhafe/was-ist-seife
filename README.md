# Was ist Seife? 🧼

Selbstgehostete Webapp zum Bewerten der Toilettenhygiene von Restaurants & Co.
Flask + SQLite, läuft per Docker im Heimnetz.

## Starten

```sh
docker compose up --build -d
# → http://localhost:8000
```

Die Datenbank liegt in `./data/seife.db`.

## Veröffentlichen auf github.io

Der Button „🌐 Veröffentlichen" rendert alle Bewertungen als Retro-HTML-Seite
und committet sie per GitHub-API nach `docs/index.html` in dieses Repo.
Einmalige Einrichtung:

1. Repo auf GitHub anlegen (public) und dieses Repo dorthin pushen
2. GitHub → Settings → Pages → Source: Branch `main`, Ordner `/docs`
3. Fine-grained Token erzeugen (Settings → Developer settings → Tokens),
   nur für dieses Repo, Berechtigung **Contents: Read and write**
4. `.env` neben `compose.yml` anlegen (ist gitignored):

   ```
   GITHUB_TOKEN=github_pat_…
   GITHUB_REPO=<user>/was-ist-seife
   ```

5. `docker compose up -d` neu starten

Vorschau der Export-Seite ohne Veröffentlichen: `http://localhost:8000/export`

**Achtung:** Die Seite ist öffentlich — inklusive Koordinaten und Notizen.

## Tests

```sh
python test_app.py
```
