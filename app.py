import os
import sqlite3
from datetime import datetime

from flask import Flask, g, redirect, render_template, request, url_for

DB_PATH = os.environ.get("DB_PATH", "seife.db")

TEXT_FELDER = [
    "name", "adresse", "wegbeschreibung", "erreichbarkeit",
    "spuelmechanismus", "seife", "seife_kommentar",
    "wasserhahn", "wasserhahn_kommentar",
    "handtrocknung", "handtrocknung_kommentar",
    "muelleimer", "ausgang", "notizen", "bewertungszeitpunkt",
]
BOOL_FELDER = [
    "beschilderung_sichtbar", "gender_verstaendlich",
    "schwere_tuer", "papier_geschuetzt", "ausgang_kontaktlos",
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
    "ausgang": ["Tür", "Automatiktür", "Offen", "Offen mit Sichtschutz"],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS bewertungen (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    adresse TEXT, lat REAL, lng REAL, wegbeschreibung TEXT,
    beschilderung_sichtbar INTEGER, gender_verstaendlich INTEGER,
    erreichbarkeit TEXT, schwere_tuer INTEGER,
    sauberkeit INTEGER, papier_geschuetzt INTEGER,
    spuelmechanismus TEXT,
    seife TEXT, seife_kommentar TEXT,
    wasserhahn TEXT, wasserhahn_kommentar TEXT,
    handtrocknung TEXT, handtrocknung_kommentar TEXT,
    muelleimer TEXT,
    ausgang TEXT, ausgang_kontaktlos INTEGER,
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


@app.post("/<int:eintrag_id>/loeschen")
def loeschen(eintrag_id):
    db().execute("DELETE FROM bewertungen WHERE id = ?", (eintrag_id,))
    db().commit()
    return redirect(url_for("liste"))


if __name__ == "__main__":
    # ponytail: Flask-Builtin-Server reicht für einen Nutzer im Heimnetz
    app.run(host="0.0.0.0", port=8000)
