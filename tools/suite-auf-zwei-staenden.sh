#!/bin/sh
# Misst die Suite auf zwei Repo-Staenden mit demselben Harness und denselben
# Bild-Mounts, und legt die vollen TAP-Texte nebeneinander ab.
#
# Anlass, gemessen: auf 50ed6e1 meldete der Laeufer ok=145 (skip=5, not-ok=0), auf
# dem jetzigen Stand ok=144 (skip=7, not-ok=0). Beide 'gruen'; die Differenz ist
# eine Pruefung, die zu einem skip geworden ist. Eine Zahl, die das nicht zeigt,
# ist kein Beweis - deshalb der Abschrieb, und deshalb der Vergleich.
#
# Der Harness ist derselbe file fuer beide Laeufe (er liegt im Repo, nicht im
# Stand): ein Vergleich zweier Harness-Staende waere kein Vergleich zweier Staende.
# Ein nachgebauter Harness ist uebrigens gar kein Harness: ein selbst gebauter
# shasum-Fake zerlegte sich und meldete fuer beide Staende 90/1.
#
# Benutzung: suite-auf-zwei-staenden.sh <Ordner1> <Ordner2> <Ausgangsordner>
#   Der Ausgangsordner muss existieren und beschreibbar sein.
set -u
HARNESS=/Users/gregor/hermes-workspace/omarchy-mobile/tools/ci-arm64.sh
IMAGES=/Users/gregor/hermes-workspace/images
REFBUILD=/Users/gregor/hermes-workspace/pmos-ref-build

lauf() {
  quell=$1; name=$2; aus=$3
  docker run --rm --platform linux/arm64/v8 \
    -v "$quell":/w:ro -v "$IMAGES":/images:ro -v "$REFBUILD":/pmos-ref-build:ro \
    -v "$IMAGES/factory-spiegel":/factory-spiegel:ro \
    -v "$HARNESS":/v.sh:ro -v "$aus":/out -e TAP_ABSCHRIEB="/out/$name.tap" \
    alpine:edge sh /v.sh
}

lauf "$1" "stand-1" "$3"
lauf "$2" "stand-2" "$3"
echo
echo "Vergleich der TAP-Texte, nur die Pruefnamen, die sich unterscheiden:"
if [ -f "$3/stand-1.tap" ] && [ -f "$3/stand-2.tap" ]; then
  # Kein Duplikat-Zweig: der alte endete auf 'head -0', das auf macOS
  # 'illegal line count -- 0' als zwei Fehlerzeilen in jeden Lauf meldete und
  # ohnehin nichts ausgab (gemessen im Zwei-Staende-Lauf v0u gegen v0v). Eine
  # Duplikat-Zahlung nach Pruefnamen wurde bei der Reparatur gemessen und ist
  # hier kein Signal, sondern Bauart: tests/all haengt mehrere Testdateien an
  # einander, und Namen wie 'scripts parse' (3x) oder 'an AI Signed-off-by
  # fails' (2x) wiederholen sich in BEIDEN Staenden mit denselben Zahlen. Ein
  # Pruefer, der in jedem Lauf feuert, wird ueberlesen; das Urteil bleibt der
  # comm-Vergleich unten, der Stehendes von Verschwundenem trennt.
  grep -E '^(ok|not ok) ' "$3/stand-1.tap" | sed 's/^[^ ]* [^-]*- //' | sort -u > "$3/namen-1"
  grep -E '^(ok|not ok) ' "$3/stand-2.tap" | sed 's/^[^ ]* [^-]*- //' | sort -u > "$3/namen-2"
  echo "--- nur in Stand 1 ---"; comm -23 "$3/namen-1" "$3/namen-2"
  echo "--- nur in Stand 2 ---"; comm -13 "$3/namen-1" "$3/namen-2"
else
  echo "nicht ok - TAP-Texte fehlen, Vergleich nicht moeglich"
  exit 1
fi
