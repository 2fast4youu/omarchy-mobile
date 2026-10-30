#!/usr/bin/env python3
"""Trägt den FLASH-BEREIT-Block für v0w oben in BRINGUP-M1.md ein.

Warum ein Skript und kein direkter Edit: ein Hineinschreiben von Hand hat in
dieser Datei schon viermal eine Maßzahl aus der Erinnerung gegeben. Dieses
Skript mißt jede Zahl selbst — Bildgröße, sha256, Init-Größe, Zeilenzahl — und
schneidet die Paneltexte wörtlich aus dem Archiv, statt sie abzutippen.

Die Plätze im Text sind BENANNT ('<<{BILD_SHA}>>'), nicht nummeriert. Grund,
gemessen an diesem Skript selbst: in der nummerierten Fassung zählte ein
literales Prozentzeichen in einem Kommentar als Feld mit, die Zahlung "25 Felder
gegen 25 Argumente" war erfüllt und die Zuordnung trotzdem um zwei Stellen
verschoben. Ein Zähler, der Text mitzählt, ist kein Zähler.
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import os
import re
import struct
import sys

WS = "/Users/gregor/hermes-workspace"
FL = WS + "/omarchy-mobile/device/blueline/firstlight"
BILD = WS + "/images/fl-v0w/firstlight.img"
ARCHIV = WS + "/images/fl-v0w/new.cpio"
PROTOKOLL = WS + "/omarchy-mobile/device/blueline/BRINGUP-M1.md"
RÜCKWEG1 = WS + "/pmos-ref-build/ref/boot.img"
RÜCKWEG2 = WS + "/android-mainline/factory/sp1a/boot.img"
VORGÄNGER = WS + "/images/fl-v0v/firstlight.img"
EINZELQUOTE = chr(39)


def sha(pfad: str) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as offener:
        for block in iter(lambda: offener.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def init_aus_bild(bild: str) -> str:
    d = open(bild, "rb").read()
    ks = struct.unpack_from("<I", d, 8)[0]
    rd = 4096 + ((ks + 4095) // 4096) * 4096
    ziel = "/tmp/protokoll-eintrag.cpio"
    with open(ziel, "wb") as offener:
        offener.write(gzip.decompress(d[rd:rd + struct.unpack_from("<I", d, 16)[0]]))
    spec = importlib.util.spec_from_file_location("newc", FL + "/newc.py")
    assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
    newc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(newc)
    return {e["name"]: e for e in newc.read_cpio(ziel)}["init"]["content"].decode()


def zeile(init: str, teil: str) -> int:
    """Zeilennummer der ersten Zeile, die 'teil' enthält (1-basiert)."""
    for nr, zeilentext in enumerate(init.splitlines(), 1):
        if teil in zeilentext:
            return nr
    raise AssertionError("keine Zeile enthält %r" % teil)


def inhalt(init: str, teil: str) -> str:
    """Der Wortlaut der ersten Zeile, die 'teil' enthält, ohne Einrückung."""
    return next(z.strip() for z in init.splitlines() if teil in z)


bild_sha, archiv_sha = sha(BILD), sha(ARCHIV)
vorg_b, vorg_sha = os.path.getsize(VORGÄNGER), sha(VORGÄNGER)
rw1_sha, rw2_sha = sha(RÜCKWEG1), sha(RÜCKWEG2)
init = init_aus_bild(BILD)
zeilen = init.splitlines()
suchblock = [z.strip() for z in zeilen if any(k in z for k in (
    "SCDATEIEN=$(", "SCLISTE=$(", "SZAHL=$(", "SC=$(printf", '[ -n "$SC" ] ||',
    "test -w ", "if [ $SCRCA"))]

BLOCK = """## FLASH-BEREIT v0w — der Knopf wird gesucht, nicht angenommen (2026-10-30, 20:4x; Flash-Freigabe von Gregor liegt vor, Working Directive: weiterarbeiten und melden wenn etwas gebraucht wird)

WARUM v0w: v0v drückte `/sys/kernel/debug/usb/` + UDC-Name + `/soft_connect`, **ohne diesen Pfad je beobachtet zu haben**. Am entpackten Kernel-Binary (44 498 944 B) sind die drei `soft_connect`-Fundstellen Namen in der Kallsyms-Tafel (`dwc3_gadget_soft_connect`, `dwc3_gadget_soft_disconnect`, `soft_connect_store`); `CONFIG_IKCONFIG=n` liefert keine eingebettete Config, ob der Knoten zur Laufzeit angelegt wird, ist aus dem Bild nicht beweisbar (firstlight/evidence/debugfs-zweig-kernelbinary-2026-10-30.txt). Ein Bild, das einen unbestätigten Knoten drückt, meldet "kein Knopf" genauso wie "Knopf ohne Wirkung". v0w sucht den Knoten im hängenden Zählkanal, meldet die gefundene Zahl und die Pfade im Herzschlag, und drückt nur, wenn die Datei beschreibbar ist.

SCHRITT 0, vor jedem Anruf: das Gerät braucht einen Tastendruck (Power + Leiser ~10 s) und danach `fastboot devices` mit einem Eintrag. Ohne diesen Beweis ist jeder Flash-Anruf ein Blindflug, und der Runner bricht ohne Eintrag ab.

Anruf (ein Write auf boot_a, danach 300 s jede Enumeration zählen):
```sh
cd /Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight
./run-flash-observe.sh /Users/gregor/hermes-workspace/images/fl-v0w/firstlight.img <<{BILD_SHA}>> 300
```
v0w: <<{BILD_B}>> B, sha256 `<<{BILD_SHA2}>>`, herausgelöste Init <<{INIT_B}>> B / <<{INIT_ZEILEN}>> Zeilen, Archiv sha256 `<<{ARCHIV_SHA}>>`. Vorgänger v0v: <<{VORG_B}>> B, sha256 `<<{VORG_SHA}>>`, Init 21 417 B / 449 Zeilen. Die Bildgröße ist auf den Byte identisch — die Größe ist kein Kennzeichen, der Hash vor dem Write ist es.

Rueckweg STUFE 1 (stellt den Zustand von heute früh exakt wieder her): `<<{RW1_PFAD}>>`, sha256 `<<{RW1_SHA}>>`, <<{RW1_B}>> B. Rueckweg STUFE 2 (Android-Bootimage; ein boot.img-Flash fasst userdata NICHT an): `<<{RW2_PFAD}>>`, sha256 `<<{RW2_SHA}>>`, <<{RW2_B}>> B. Vor jedem Partitions-Write stehen Größen- und sha256-Prüfung der Rückweg-Datei, unabhängig davon, dass eine Freigabe vorliegt.

Gerät ist jetzt (gemessen 2026-10-30 20:37): **läuft v0t, an keinem Bus** — `fastboot devices` ohne Eintrag, kein Fastboot-Gerät am USB-Baum, `ping -c 2 172.16.42.1` antwortet nicht; `boot_a` hält den v0t-Hash, und das Panel zeigt Titel und Herzschlag mit `state=not attatched` und leerem `gebunden=`-Feld (Gregors Ablesung). Für diesen Flash ist der Tastendruck nötig.

DIE SUCHE, wie sie im fertigen Bild steht — aus dem Archiv geschnitten, nicht abgetippt —, Zeilen <<{SUCHE_VON}>> bis <<{SUCHE_BIS}>>:
<<{SUCHE_BLOCK}>>

DER HERZSCHLAG meldet in jedem Block die Suche selbst, Zeile <<{HERZ_ZEILE}>>:
`<<{HERZ_TEXT}>>`

DIE NACHBIND-RUNDE, Zeile <<{BEWEIS_ZEILE}>>:
`<<{BEWEIS_TEXT}>>`

DIE FÜNF-SEKUNDEN-ZEILE, Zeile <<{SPAETER_ZEILE}>>:
`<<{SPAETER_TEXT}>>`

ERWARTUNG v0w (vor dem Flash festgelegt; jede Zeichenkette ist im ausgelieferten Bild nachgesehen). Die Fälle, die dieses Bild **ohne jeden Bus** trennt:
- `gefunden=0` mit leerem `suche=` = der Knoten existiert in diesem Kernel nicht; v0vs `pfad=` war eine Annahme, und der Fall ist damit abgeschlossen, nicht offen.
- `gefunden=1` mit gefülltem `suche=` und `scrca=0`, aber `state=` bleibt `not attached` = der Knoten ist da, beschreibbar, gedrückt — und der Host sieht trotzdem nichts: VBUS, CC, Kabel oder Port. Software kann hier nichts mehr richten.
- `rc0=` oder `rc1=` ungleich null mit `invalid argument` = der Controller trägt den gadget-Zweig in diesem Moment nicht. `read-only file system` = debugfs hängt nicht. `No such file or directory` bei `scrca=0` = die Datei verschwand zwischen Test und Write.
- `scrca=9` mit `text0=kein Knopf` = die Beschreibbar-Prüfung hat den Write verhindert; die Beweiszeile nennt dann trotzdem `pfad=` und `suche=`, weil die Suche der Messwert ist, nicht der Druck.
- `debugfs=` im Herzschlag leer = debugfs hängt nicht; dann ist die ganze Suche Dunkelheit, kein Befund.
- `state=` geht auf `default` oder `configured` = der Host hat den Reset geschickt; am Bus wäre dann Vendor 0x18D1 Produkt 0xD002 zu sehen — dieselbe Produktzahl wie v0s, v0t, v0u und v0v, eine Enumeration ist also nur über den Panel-Titel einem Bild zuzuordnen.
- Titel ohne Herzschlag = PID 1 stirbt zwischen den beiden Zeilen; gar kein Text = der Boot starb vor init.

BELEGE VOR DEM Flash, alle gelaufen: Trockenlauf `patch-v0w.py` (7 Umbauten, je 1 Fundstelle, Bilanz 146 offene gegen 146 zu Paren), `pruefe-binde-reihenfolge.py` auf dem gepatchten Archiv (0 Fehler), `verify-v0q.py` 28 Beweismale / 0 Fehler am fertigen Bild, `verify-v0w.py` **41 Beweismale / 0 Fehler** am fertigen Bild — darunter sechs Reihenfolge-Prüfungen: Suche in Zeile <<{SUCHE_VON2}>> vor der Annahme in Zeile <<{BEDINGT_ZEILE}>>, Beschreibbar-Test vor beiden Writes, kein unbedingter Pfad. `pruefe-init-syntax.sh` über die wirklich herausgelöste Init: sh -n und bash -n durchgelaufen. Die Suite war zum Zeitpunkt dieses Eintrags noch nicht durchgelaufen; ihr Ergebnis wird nachgetragen.

ZWEI NEUE REGELN AUS DIESEM BAU, beide gemessen, nicht gemeint:
1. **Ein Syntax-Test hat Vorrang vor jedem Text-Test.** Drei Herzschlag-Kandidaten wurden gegeneinander gemessen: nur der mit zwei Double-Quotes besteht `bash -n` allein. Der Kandidat in der Form des Vorgängers — drei Double-Quotes in einer Zeile — überlebt nur, weil die Folgezeile sein Literal schließt; am v0v-Bild ist genau das Zeile 74, und die nächste Zeile gehört mit in ihr Literal. Ein Text-Test war grün, während der Text syntaktisch zerstückelt war.
2. **Wer einen Beweis umbenennt, meldet ihn als fehlend.** Der Reihenfolge-Prüfer suchte das v0v-Feld und meldete die v0w-Zeile als fehlend, obwohl dieselbe Aussage dastand. Merkmalssätze wachsen mit; Beweise werden nicht umgetauft (dasselbe Muster: `write rc=` wurde zu `binde rc=` und durchtrennte die Beweiskette über drei Bilder).
"""

# Ein Suchbegriff, der ein Zeichen auslaesst, findet die Zeile nicht, die da
# steht: "SCDATEIEN$(" sucht an der falschen Stelle, im Bild steht
# "SCDATEIEN=$(find". Die Zahl 0 war eine Aussage ueber meinen Begriff, nicht
# ueber das Bild. Wer eine fehlende Zeile meldet, misst erst den Begriff.
SETZEN = {
    "BILD_SHA": bild_sha, "BILD_B": os.path.getsize(BILD),
    "BILD_SHA2": bild_sha, "INIT_B": len(init), "INIT_ZEILEN": len(zeilen),
    "ARCHIV_SHA": archiv_sha, "VORG_B": vorg_b, "VORG_SHA": vorg_sha,
    "RW1_PFAD": RÜCKWEG1, "RW1_SHA": rw1_sha, "RW1_B": os.path.getsize(RÜCKWEG1),
    "RW2_PFAD": RÜCKWEG2, "RW2_SHA": rw2_sha, "RW2_B": os.path.getsize(RÜCKWEG2),
    "SUCHE_VON": zeile(init, "SCDATEIEN=$("), "SUCHE_BIS": zeile(init, "if [ $SCRCA"),
    "SUCHE_BLOCK": "\n".join("    " + s for s in suchblock),
    "HERZ_ZEILE": zeile(init, "debugfs=$("), "HERZ_TEXT": inhalt(init, "debugfs=$("),
    "BEWEIS_ZEILE": zeile(init, "weicher-bind $rb:"),
    "BEWEIS_TEXT": inhalt(init, "weicher-bind $rb:"),
    "SPAETER_ZEILE": zeile(init, "spaeter 5s:"), "SPAETER_TEXT": inhalt(init, "spaeter 5s:"),
    "SUCHE_VON2": zeile(init, "SCDATEIEN=$("), "BEDINGT_ZEILE": zeile(init, '[ -n "$SC" ] ||'),
}
for name, wert in sorted(SETZEN.items()):
    platz = "<<{%s}>>" % name
    assert BLOCK.count(platz) == 1, "%s: Platzhalter %d mal, erwartet 1" % (
        name, BLOCK.count(platz))
    BLOCK = BLOCK.replace(platz, str(wert), 1)
uebrig = re.findall(r"<<[A-Z0-9_]+>>", BLOCK)
assert not uebrig, "Platzhalter übrig geblieben: %s" % uebrig
# Der Anruf soll genau einmal dastehen. Der Pfad allein steht zweimal (einmal
# im vorangestellten cd, einmal im Anruf), also zaehlt die Pruefung den Anruf
# mit seinem Hash - das ist die Zeile, die ein Mensch eintippt. Sie steht HINTER
# dem Einsetzen, der Platzhalter ist da schon der Hash: eine Pruefung auf den
# Platzhalter prüft einen Text, den es an dieser Stelle nicht mehr gibt.
assert BLOCK.count("images/fl-v0w/firstlight.img " + bild_sha + " 300") == 1, \
    "der Anruf soll genau einmal stehen"


if __name__ == "__main__":
    roh = open(PROTOKOLL, encoding="utf-8").read()
    assert bild_sha not in roh, "der v0w-Hash steht schon im Protokoll — nicht zweimal eintragen"
    marke = "\n## FLASH-BEREIT v0v"
    assert roh.count(marke) == 1, "der Vorgänger-Block ist nicht eindeutig (%d mal)" % roh.count(marke)
    neu = roh.replace(marke, "\n" + BLOCK + marke, 1)
    assert len(neu) - len(roh) == len(BLOCK) + 1, "die Länge rechnet nicht auf"
    open(PROTOKOLL, "w", encoding="utf-8").write(neu)
    print("eingetragen: v0w-Block vor dem v0v-Block")
    print("  Protokoll %d -> %d B" % (len(roh), len(neu)))
    print("  Bild %d B, sha256 %s" % (os.path.getsize(BILD), bild_sha))
    print("  Init %d B / %d Zeilen, Archiv sha256 %s" % (len(init), len(zeilen), archiv_sha))
    print("  Panel-Titel: %s" % inhalt(init, "first-light v0w").split(EINZELQUOTE)[1])
    print("  Suche Zeile %d bis %d, Bedingung Zeile %d, Drücken Zeile %d"
          % (SETZEN["SUCHE_VON"], SETZEN["SUCHE_BIS"], SETZEN["BEDINGT_ZEILE"],
             zeile(init, "if [ $SCRCA -eq 0 ]; then sc0")))
