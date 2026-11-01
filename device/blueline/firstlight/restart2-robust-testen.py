#!/usr/bin/env python3
# robuster Datei-Upload ueber die Referenz-Telnet-Leitung:
# Base64(gzip) in Stuecken, jedes Stueck einzeln per SHA verifiziert,
# fehlerhafte Stuecke werden wiederholt. Danach restart2 mit Argument
# "bootloader" ausfuehren und beobachten: Fastboot (Sonde wirkt) oder
# Rueckkehr in die Referenz (Argument ignoriert).
import base64, gzip, hashlib, socket, subprocess, time, datetime, re, sys

FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"
BIN = "/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight/restart2"
LOGP = "/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight/evidence/restart2-test-2026-11-01.txt"
EXPECT_SHA = hashlib.sha256(open(BIN, "rb").read()).hexdigest()

def log(msg):
    line = datetime.datetime.now().strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    open(LOGP, "a").write(line + "\n")

def conn():
    s = socket.create_connection(("172.16.42.1", 23), timeout=8); s.settimeout(3); return s

def rd(s, secs=1.0):
    s.settimeout(secs); buf = b""
    try:
        while True:
            d = s.recv(8192)
            if not d: break
            buf += d
    except socket.timeout: pass
    return buf.decode(errors="replace")

def cmd(s, c, wait=1.5):
    s.sendall((c + "\r\n").encode()); time.sleep(wait); return rd(s)

def fb_getvar(v):
    try:
        r = subprocess.run([FB, "getvar", v], capture_output=True, text=True, timeout=6)
        return (r.stdout + r.stderr).strip().splitlines()[0] if r.returncode == 0 else "FB-ZEIT"
    except subprocess.TimeoutExpired:
        return "FB-ZEIT"

def usb_state():
    try:
        out = subprocess.run(["ioreg", "-p", "IOUSB", "-l", "-w0"], capture_output=True, text=True, timeout=8).stdout
    except subprocess.TimeoutExpired:
        return "ZEIT"
    hits = set()
    for b in out.split('+-o ')[1:]:
        if '"USB Vendor Name" = "Google"' in b:
            m = re.search(r'"idProduct"\s*=\s*(\d+)', b)
            if m: hits.add("0x%04X" % int(m.group(1)))
    return ",".join(sorted(hits)) or "kein-Geraet"

log("=== restart2-Test, robuster Upload (Stueck-fuer-Stueck-SHA) ===")
log("restart2 sha256 (Rechner): " + EXPECT_SHA)
log("vorher: %s | %s | usb=%s" % (fb_getvar("current-slot"), fb_getvar("slot-retry-count:b"), usb_state()))

payload = base64.b64encode(gzip.compress(open(BIN, "rb").read(), 9))
CH = 768
stueck = [payload[i:i+CH] for i in range(0, len(payload), CH)]
s = conn(); rd(s)
cmd(s, "rm -f /tmp/r2.b64 /tmp/restart2; : > /tmp/r2.b64", 1.0)
t0 = time.time()
for n, te in enumerate(stueck):
    ted = te.decode()
    soll = hashlib.sha256(te).hexdigest()[:16]
    ok = False
    for versuch in range(3):
        s.sendall(("printf '%s' '" + ted + "' >> /tmp/r2.b64\r\n").encode())
        time.sleep(0.35)
        rd(s, 0.15)
        r = cmd(s, "tail -c %d /tmp/r2.b64 | sha256sum | cut -c1-16" % len(te), 1.2)
        if soll in r:
            ok = True; break
        log("Stueck %d Versuch %d SHA-Fehler, wiederhole" % (n, versuch + 1))
    if not ok:
        log("ABBRUCH: Stueck %d auch nach 3 Versuchen falsch" % n); sys.exit(1)
    if n % 10 == 9:
        log("  %d/%d Stuecke ok (%.0fs)" % (n + 1, len(stueck), time.time() - t0))
log("Upload komplett in %.1fs" % (time.time() - t0))
r = cmd(s, "base64 -d /tmp/r2.b64 | gzip -d > /tmp/restart2; chmod +x /tmp/restart2; sha256sum /tmp/restart2", 4)
log("sha im Geraet: " + r.replace("\r\n", " ").strip()[-100:])
if EXPECT_SHA not in r:
    log("ABBRUCH: Ziel-SHA ungleich"); sys.exit(1)
log("starte: /tmp/restart2 bootloader")
s.sendall(b"/tmp/restart2 bootloader\r\n")
t0 = time.time()
for i in range(50):
    time.sleep(3)
    t = time.time() - t0
    g = usb_state()
    tn = "offen"
    try:
        x = socket.create_connection(("172.16.42.1", 23), timeout=1); x.close()
    except OSError:
        tn = "zu"
    log("t=%3.0fs usb=%s telnet=%s" % (t, g, tn))
    if tn == "offen" and t > 30:
        log("ERGEBNIS: zurueck in der Referenz — RESTART2 'bootloader' fuehrte normalen Neustart aus")
        break
    if g == "0x4EE0" and t > 5:
        log("ERGEBNIS: FASTBOOT nach %.0fs — RESTART2 'bootloader' wirkt (Rueckweg belegt)" % t)
        log("  %s | %s | %s" % (fb_getvar("current-slot"), fb_getvar("slot-retry-count:b"), fb_getvar("slot-unbootable:b")))
        break
else:
    log("Fenster ohne Treffer")
