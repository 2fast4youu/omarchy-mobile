#!/bin/sh
# Zeigt die USB-wege-Zeilen eines v0t-/v0s-/v0r-init aus einem v0t-Bild.
# Aufruf: sh usbwege.sh <cpio>   (noto: zeigt nur die Zeilen, die der Host je sah)
for f in "$@"; do
  echo "### $f"
  python3 - "$f" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location(
    "newc", "/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight/newc.py")
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)
init = {e["name"]: e for e in newc.read_cpio(sys.argv[1])}["init"]["content"].decode()
such = ("nachbinden", "gebunden", "letzter Schritt", "udc nach", "gefundene udc",
        "beide Knoten", "dwc3 rolle", "controller-state", "steps=", "say()")
for n, x in enumerate(init.splitlines(), 1):
    if any(s in x for s in such):
        print("%4d| %s" % (n, x))
PY
done
