#!/usr/bin/env python3
"""Prueft den Bindblock des Trockenlauf-Ausgabe auf Reihenfolge und Form.

Warum ein eigener Pruefer: alle bisherigen Pruefer fragen Anwesenheit ab ('kommt
weicher-bind vor?'). Der Fehler, der vier Baue gekostet hat, war eine Reihenfolge
oder ein Zeilenende - ein Beweis, der rc1 vor sc1 nennt, oder ein Block, dem die
zwei done fehlen. Ein Zaehltest sieht beides nicht, weil beide Zeichenketten da
sind, wenn auch falsch herum.

Der Pruefer liest das Ausgabe des Trockenlaufs, nicht den Patch-Quelltext: der
Quelltext ist die Vermutung, das Ausgabe ist der Befund.

Drei Dinge, die die erste Fassung dieses Pruefers selbst falsch machte, und was
sie hier ersetzen:
  - Pro-Zeile-Klammern gezaehlt: ein Shell-Skript balanciert Klammern ueber
    Zeilen hinweg (( ... ) &, case ... esac). 28 Zeilen als 'fehlerhaft' gemeldet,
    alle echt. Jetzt: globale Bilanz, und innerhalb von Echo-Zeichenketten.
  - '$sc1rc' als Leser behandelt, auch in 'rc1=$sc1rc', wo es ein Label ist und
    der Wert in der naechsten Zeile gelesen wird. Jetzt: Labels ausgenommen.
  - Ein 'sh -n' haette den ersten Defekt (fehlende done) gemeldet, bevor ein
    Geraet ihn sieht. Der Syntaxtest ist deshalb Teil des Baurezepts.

Benutzung: pruefe-binde-reihenfolge.py <new.cpio>
"""
import importlib.util
import os
import sys

Q = chr(34)
# Ein Label nennt einen Wert unter einem Namen, ohne ihn zu lesen. Es ist keine
# Lesung, sondern Text - 'rc1=$sc1rc' in einer Zeile, die vor dem Setzer laeuft,
# zeigt den Wert aus der vorigen Runde, und das ist Absicht.
LABEL_AUSNAHME = ("rc1=$sc1rc", "sc1text=$sc1", "text1=$sc1")


def init_aus_cpio(pfad):
    hier = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("newc", os.path.join(hier, "newc.py"))
    assert spec is not None and spec.loader is not None, "newc.py nicht ladbar"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {e["name"]: e for e in mod.read_cpio(pfad)}["init"]["content"].decode()


def kette(zeile):
    """Nur was in der Echo-Zeichenkette steht, in doppelten Anführungszeichen."""
    st = zeile.find(Q)
    en = zeile.rfind(Q)
    return zeile[st + 1:en] if 0 <= st < en else ""


def haupt():
    init = init_aus_cpio(sys.argv[1])
    zeilen = init.splitlines()
    fehler = 0

    # 1) Globale Bilanz. Eine Zeile, die alone unbalanciert ist, ist normal; eine
    #    Datei, die es insgesamt ist, kann kein Shell lesen.
    if init.count("(") == init.count(")"):
        print("ok - globale Klammerbilanz: %d offen, %d zu" % (init.count("("), init.count(")")))
    else:
        print("not ok - globale Klammerbilanz: %d offen, %d zu"
              % (init.count("("), init.count(")")))
        fehler += 1
    zeilen = init.splitlines()

    # 2) Innerhalb der Echo-Zeichenketten: hier ist ein Paren ein Textzeichen,
    #    aber ein falsches ist auf dem Panel als Muell lesbar.
    for nr, z in enumerate(zeilen, 1):
        if not z.lstrip().startswith("echo"):
            continue
        text = kette(z).replace(chr(92) + "(", "(").replace(chr(92) + ")", ")")
        if text.count("(") != text.count(")"):
            print("not ok - Zeile %d: Echo-Kette mit %d ( gegen %d )"
                  % (nr, text.count("("), text.count(")")))
            fehler += 1

    # 3) Setzer vor Leser, mit den Labels als Ausnahme.
    for name in ("sc0rc", "sc1rc", "rc", "scvor", "sc0", "sc1"):
        setzer = [n for n, x in enumerate(zeilen, 1)
                  if (name + "=") in x and ("$?" in x or "$(" in x)]
        leser = []
        for n, x in enumerate(zeilen, 1):
            if ("$" + name) not in x or (name + "=") in x:
                continue
            if any(L in x for L in LABEL_AUSNAHME if L.startswith(name + "=")
                   or ("$" + name) in L):
                pass
            leser.append(n)
        vor = [n for n in leser if setzer and n < setzer[0]
               and not any(L in zeilen[n - 1] for L in LABEL_AUSNAHME)]
        print("%s - %s: setzt Zeile %s, liest Zeile %s%s"
              % ("ok" if not vor else "not ok", name, setzer[:4], leser[:4],
                 "" if not vor else ", vor dem Setzer: %s" % vor))
        fehler += len(vor)

    # 4) Die Fuenf-Sekunden-Ausgabe hinter ihrem sleep.
    schlaf = [n for n, x in enumerate(zeilen, 1) if x.strip() == "sleep 5"]
    spaeter = [n for n, x in enumerate(zeilen, 1) if "spaeter 5s:" in x]
    if schlaf and spaeter and min(spaeter) > min(schlaf):
        print("ok - sleep 5 Zeile %d, spaeter-Ausgabe Zeile %d" % (min(schlaf), min(spaeter)))
    else:
        print("not ok - sleep 5 %s, spaeter-Ausgabe %s" % (schlaf, spaeter))
        fehler += 1

    # 5) Der Bindblock muss in den done enden, die zu ihm gehoeren.
    ende = [n for n, x in enumerate(zeilen, 1) if x.strip() in ("done", "    done")]
    bind = next((n for n, x in enumerate(zeilen, 1) if "weicher-bind $rb:" in x), None)
    if bind and any(n > bind for n in ende):
        print("ok - nach dem Bindblock folgen %d done" % sum(1 for n in ende if n > bind))
    else:
        print("not ok - auf den Bindblock folgen keine done")
        fehler += 1

    # 6) Herzschlag: eine Zeile, die den Knopf als erreichbar ausweist.
    herz = [x for x in zeilen if "weicher-bind=debugfs-geoffnet" in x]
    if len(herz) == 1:
        print("ok - Herzschlag-Zeile: %s" % herz[0].strip()[:74])
    else:
        print("not ok - Herzschlag-Zeile %d mal" % len(herz))
        fehler += 1

    print("%d Fehler, %d Zeilen, soft_connect %d, bDeviceState %d"
          % (fehler, len(zeilen), init.count("soft_connect"), init.count("bDeviceState")))
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(haupt())
