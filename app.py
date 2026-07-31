import base64
import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime

from flask import Flask, g, redirect, render_template, request, url_for

DB_PATH = os.environ.get("DB_PATH", "seife.db")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # z. B. "fred/was-ist-seife"
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
EXPORT_PFAD = os.environ.get("EXPORT_PFAD", "docs/index.html")

TEXT_FELDER = [
    "name", "adresse", "wegbeschreibung", "erreichbarkeit",
    "spuelmechanismus", "seife", "seife_kommentar",
    "wasserhahn", "wasserhahn_kommentar",
    "handtrocknung", "handtrocknung_kommentar",
    "muelleimer", "ausgang", "notizen", "bewertungszeitpunkt",
    "toilettenrollenhalter",
]
BOOL_FELDER = [
    "beschilderung_sichtbar", "gender_verstaendlich", "schwere_tuer",
]
ZAHL_FELDER = ["sauberkeit", "sterne"]
KOORD_FELDER = ["lat", "lng"]
FELDER = TEXT_FELDER + BOOL_FELDER + ZAHL_FELDER + KOORD_FELDER

OPTIONEN = {
    "erreichbarkeit": ["Ebenerdig", "Stufe", "Treppe"],
    "seife": ["Pumpspender", "Sensor", "Hebel", "Stückseife", "Keine"],
    "wasserhahn": ["Hebel", "Automatik", "Drehknopf", "Druckknopf"],
    "handtrocknung": ["Offener Föhn", "Geschlossener Föhn", "Papiertuch",
                      "Festes Handtuch", "Trommelhandtuch", "Nichts"],
    "muelleimer": ["Keiner", "Mit Berührung", "Berührungslos"],
    "toilettenrollenhalter": ["Offen", "Geschlossen", "Beides"],
    "ausgang": ["Tür", "Tür (mit Fuß öffenbar)", "Tür (mit Papiertuch öffenbar)",
                "Automatiktür", "Offen", "Offen mit Sichtschutz"],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS bewertungen (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    adresse TEXT, lat REAL, lng REAL, wegbeschreibung TEXT,
    beschilderung_sichtbar INTEGER, gender_verstaendlich INTEGER,
    erreichbarkeit TEXT, schwere_tuer INTEGER,
    sauberkeit INTEGER, toilettenrollenhalter TEXT,
    spuelmechanismus TEXT,
    seife TEXT, seife_kommentar TEXT,
    wasserhahn TEXT, wasserhahn_kommentar TEXT,
    handtrocknung TEXT, handtrocknung_kommentar TEXT,
    muelleimer TEXT,
    ausgang TEXT,
    sterne INTEGER, notizen TEXT,
    bewertungszeitpunkt TEXT,
    erstellt_am TEXT DEFAULT (datetime('now', 'localtime')),
    geaendert_am TEXT DEFAULT (datetime('now', 'localtime'))
)
"""

app = Flask(__name__)
app.jinja_env.globals["optionen"] = OPTIONEN

with sqlite3.connect(DB_PATH) as conn:
    conn.execute(SCHEMA)
    try:
        conn.execute("ALTER TABLE bewertungen ADD COLUMN bewertungszeitpunkt TEXT")
    except sqlite3.OperationalError:
        pass  # Spalte existiert schon
    try:
        conn.execute("ALTER TABLE bewertungen ADD COLUMN toilettenrollenhalter TEXT")
        conn.execute("UPDATE bewertungen SET toilettenrollenhalter = 'Geschlossen' "
                     "WHERE papier_geschuetzt = 1")
    except sqlite3.OperationalError:
        pass  # schon migriert
    for alte_spalte in ["papier_geschuetzt", "ausgang_kontaktlos"]:
        try:
            conn.execute(f"ALTER TABLE bewertungen DROP COLUMN {alte_spalte}")
        except sqlite3.OperationalError:
            pass  # schon weg (oder frische DB)


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def db_schliessen(_exc):
    verbindung = g.pop("db", None)
    if verbindung is not None:
        verbindung.close()


def formular_werte():
    werte = {}
    for feld in TEXT_FELDER:
        werte[feld] = request.form.get(feld, "").strip() or None
    for feld in BOOL_FELDER:
        werte[feld] = 1 if request.form.get(feld) else 0
    for feld in ZAHL_FELDER:
        wert = request.form.get(feld)
        werte[feld] = int(wert) if wert else None
    for feld in KOORD_FELDER:
        try:
            werte[feld] = float(request.form.get(feld, "").strip().replace(",", "."))
        except ValueError:
            werte[feld] = None
    return werte


@app.route("/")
def liste():
    eintraege = db().execute(
        "SELECT id, name, adresse, sterne, "
        "COALESCE(bewertungszeitpunkt, erstellt_am) AS zeitpunkt FROM bewertungen "
        "ORDER BY zeitpunkt DESC"
    ).fetchall()
    return render_template("liste.html", eintraege=eintraege)


@app.route("/neu", methods=["GET", "POST"])
def neu():
    if request.method == "POST":
        werte = formular_werte()
        if not werte["name"]:
            return render_template("formular.html", eintrag=werte,
                                   fehler="Name fehlt"), 400
        spalten = ", ".join(FELDER)
        platzhalter = ", ".join("?" * len(FELDER))
        cursor = db().execute(
            f"INSERT INTO bewertungen ({spalten}) VALUES ({platzhalter})",
            [werte[f] for f in FELDER])
        db().commit()
        return redirect(url_for("detail", eintrag_id=cursor.lastrowid))
    jetzt = datetime.now().strftime("%Y-%m-%dT%H:%M")
    return render_template("formular.html", eintrag={"bewertungszeitpunkt": jetzt})


@app.route("/<int:eintrag_id>")
def detail(eintrag_id):
    eintrag = db().execute(
        "SELECT * FROM bewertungen WHERE id = ?", (eintrag_id,)).fetchone()
    if eintrag is None:
        return "Nicht gefunden", 404
    return render_template("detail.html", eintrag=eintrag)


@app.route("/<int:eintrag_id>/bearbeiten", methods=["GET", "POST"])
def bearbeiten(eintrag_id):
    eintrag = db().execute(
        "SELECT * FROM bewertungen WHERE id = ?", (eintrag_id,)).fetchone()
    if eintrag is None:
        return "Nicht gefunden", 404
    if request.method == "POST":
        werte = formular_werte()
        if not werte["name"]:
            return render_template("formular.html", eintrag=werte,
                                   fehler="Name fehlt"), 400
        zuweisungen = ", ".join(f"{f} = ?" for f in FELDER)
        db().execute(
            f"UPDATE bewertungen SET {zuweisungen}, "
            "geaendert_am = datetime('now', 'localtime') WHERE id = ?",
            [werte[f] for f in FELDER] + [eintrag_id])
        db().commit()
        return redirect(url_for("detail", eintrag_id=eintrag_id))
    return render_template("formular.html", eintrag=dict(eintrag))


def export_html():
    eintraege = db().execute(
        "SELECT * FROM bewertungen "
        "ORDER BY COALESCE(bewertungszeitpunkt, erstellt_am) DESC"
    ).fetchall()
    return render_template("export.html", eintraege=eintraege,
                           stand=datetime.now().strftime("%d.%m.%Y %H:%M"))


def github_veroeffentlichen(html):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise RuntimeError("GITHUB_TOKEN und GITHUB_REPO müssen gesetzt sein (siehe README)")
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{EXPORT_PFAD}"
    kopf = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "was-ist-seife",
    }
    sha = None
    try:
        anfrage = urllib.request.Request(f"{url}?ref={GITHUB_BRANCH}", headers=kopf)
        with urllib.request.urlopen(anfrage) as antwort:
            sha = json.load(antwort)["sha"]
    except urllib.error.HTTPError as fehler:
        if fehler.code != 404:  # 404 = Datei existiert noch nicht, erster Export
            raise
    daten = {
        "message": "Export: Bewertungen aktualisiert",
        "content": base64.b64encode(html.encode()).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        daten["sha"] = sha
    anfrage = urllib.request.Request(url, data=json.dumps(daten).encode(),
                                     headers=kopf, method="PUT")
    with urllib.request.urlopen(anfrage):
        pass


@app.get("/export")
def export():
    return export_html()


@app.post("/veroeffentlichen")
def veroeffentlichen():
    try:
        github_veroeffentlichen(export_html())
    except (RuntimeError, urllib.error.URLError) as fehler:
        return render_template("veroeffentlicht.html", fehler=str(fehler)), 500
    besitzer, repo = GITHUB_REPO.split("/", 1)
    pages_url = f"https://{besitzer}.github.io/{repo}/"
    return render_template("veroeffentlicht.html", fehler=None, pages_url=pages_url)


@app.post("/<int:eintrag_id>/loeschen")
def loeschen(eintrag_id):
    db().execute("DELETE FROM bewertungen WHERE id = ?", (eintrag_id,))
    db().commit()
    return redirect(url_for("liste"))


if __name__ == "__main__":
    # ponytail: Flask-Builtin-Server reicht für einen Nutzer im Heimnetz
    app.run(host="0.0.0.0", port=8000)
