"""Legt BINDEFIX_ALT neben die entsprechende Bildstelle, Zeichen fuer Zeichen.

Grund: drei von fuenf Ankern passen, der Bindblock nicht, und die
Allzweck-Suche fand die Abweichung nicht, weil ihr Zeilenvergleich bei
Mehrzeilen-Ankern auf die falsche Bildzeile faellt.
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

anker = pm.BINDEFIX_ALT
# Bildstelle: die siebzehn Zeichen um den Ankeranfang herum, ueber sechs Zeilen.
anfang = '[ -n "$u" ] || continue'
i = init.index(anfang) - 12
bildstelle = init[i:i + len(anker) + 80]

print("Anker %d Zeichen, Bildstelle %d Zeichen" % (len(anker), len(bildstelle)))
for k in range(min(len(anker), len(bildstelle))):
    if anker[k] != bildstelle[k]:
        print("ERSTE ABWEICHUNG bei Zeichen %d (Zeile %d des Ankers)"
              % (k, anker[:k].count("\n") + 1))
        print("  Anker: %r" % anker[max(0, k - 46):k + 26])
        print("  Bild : %r" % bildstelle[max(0, k - 46):k + 26])
        print("  Anker-Zeichen: U+%04X   Bild-Zeichen: U+%04X" % (ord(anker[k]), ord(bildstelle[k])))
        break
else:
    print("Anker ist ein Praefix der Bildstelle, keine Abweichung in %d Zeichen" % min(len(anker), len(bildstelle)))
print()
print("Anker-Zeilen:", anker.count("\n"))
for nr, x in enumerate(anker.split("\n"), 1):
    print("  A%02d %r" % (nr, x[:120]))
