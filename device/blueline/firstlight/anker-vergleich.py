"""Vergleicht patch-v0u.py's Anker Zeichen fuer Zeichen mit dem v0t-Bild.

Grund: ein Anker meldet 'genau 0 mal' und die Ursache sass bisher jedes Mal in
einem Randzeichen (fehlendes Anfuhrungszeichen, wegge-Crstripeter Leerstrich).
Gerade-weil-Sehen schlaegt Raten: diese Datei zeigt die erste Abweichung.
"""
import importlib.util
import sys

spec = importlib.util.spec_from_file_location(
    "newc", "/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight/newc.py")
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)

init = {e["name"]: e for e in newc.read_cpio(
    "/Users/gregor/hermes-workspace/images/fl-v0t/new.cpio")}["init"]["content"].decode()

sys.argv = ["x", "/dev/null", "/dev/null"]
pspec = importlib.util.spec_from_file_location(
    "pm", "/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight/patch-v0u.py")
pm = importlib.util.module_from_spec(pspec)
try:
    pspec.loader.exec_module(pm)
except SystemExit:
    pass

for name in ("TITEL_ALT", "STAAT_ALT", "DOPPEL_ALT", "TYP_ALT", "BINDEFIX_ALT"):
    anker = getattr(pm, name)
    n = init.count(anker)
    print("%-12s im Bild %d mal, %d Zeichen" % (name, n, len(anker)))
    if n:
        continue
    # Erste Abweichung gegen die gleichbeginnende Bildzeile suchen.
    anfang = anker.split("\n")[0].lstrip()
    zeile = next((z for z in init.splitlines() if z.lstrip().startswith(anfang[:40])), None)
    if zeile is None:
        print("    keine Bildzeile findet Anfang %r" % anfang[:40])
        continue
    zeile = zeile.lstrip() if zeile.startswith("          ") is False else zeile
    kleiner = min(len(anker), len(zeile.strip()) + 8)
    for k in range(kleiner):
        a = anker[k] if k < len(anker) else "<ende>"
        b = zeile[k] if k < len(zeile) else "<ende>"
        if a != b:
            print("    erste Abweichung bei Zeichen %d" % k)
            print("      Anker: %r" % anker[max(0, k - 30):k + 12])
            print("      Bild : %r" % zeile[max(0, k - 30):k + 12])
            break
    else:
        print("    Bildzeile kuerzer als Anker: Bild %d, Anker %d Zeichen" % (len(zeile), len(anker)))
        print("      Anker-Ende: %r" % anker[-40:])
        print("      Bild-Ende : %r" % zeile[-40:])
