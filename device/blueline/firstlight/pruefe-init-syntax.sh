#!/bin/sh
# POSIX- und bash-Syntaxpruefung auf den Init, der WIRKLICH herausgeloest ist.
#
# Anlass, gemessen: ich meldete 'sh -n: syntax error' fuer das v0v-Bild und fuer
# meinen v0w-Entwurf - und beide Male testete ich die falsche Datei. Ein Test in
# der Eile schrieb das ganze cpio-Archiv nach /tmp/alt.sh und pruefte es als
# Shell-Skript; die gemeldete 'Fehlerzeile' war Zeile 67 von /etc/protocols.
# Ein Test, dessen eigene Grundlage ungeprueft ist, meldet Defekte, die keine
# sind, und verdeckt damit die echten.
#
# Dieser Laeufer loest den Init mit newc.read_cpio aus dem Archiv (nicht per
# Hand aus einem Rohblock), meldet seine Groesse und seine erste Zeile - damit
# die Grundlage des Tests selbst lesbar ist - und laesst dann sh -n und bash -n
# daruefer laufen.
#
# Benutzung: pruefe-init-syntax.sh <pfad-zu-neu.cpio> [pfad-zu-boot.img]
#   Erster Punkt: das cpio-Archiv, aus dem der Init kommt. Zweiter Punkt
#   (optional): ein boot.img, dessen angehaengter Init zum Vergleich dient.
set -eu
[ $# -ge 1 ] || { echo "usage: $0 <neu.cpio> [boot.img]"; exit 2; }
FL=${FL:-/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight}
export FLDIR="$FL"                 # der Python-Teil sucht newc.py, ohne zu raten
python3 - "$1" <<'PY'
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location("newc", os.environ["FLDIR"] + "/newc.py")
assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
newc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(newc)
es = {e["name"]: e for e in newc.read_cpio(sys.argv[1])}
assert "init" in es, "kein init im Archiv: %d Eintraege" % len(es)
text = es["init"]["content"].decode()
open("/tmp/pruef-init.sh", "w", encoding="utf-8").write(text)
print("Grundlage: init, %d B, %d Zeilen, erste Zeile %r"
      % (len(text), text.count(chr(10)), text.splitlines()[0][:60]))
PY
echo "--- sh -n (POSIX) ---"
sh -n /tmp/pruef-init.sh && echo "ok - POSIX-Syntaxpruefung durchgelaufen"
echo "--- bash -n ---"
bash -n /tmp/pruef-init.sh && echo "ok - bash-Syntaxpruefung durchgelaufen"
