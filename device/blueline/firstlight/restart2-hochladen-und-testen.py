#!/usr/bin/env python3
# Laedt das statische restart2-Binary in die laufende Referenz-Initramfs
# (Base64 ueber Telnet), prueft SHA, und fuehrt es mit Argument "bootloader"
# aus. Erwartung bei RESTART2-Unterstiuetzung: Geraet landet direkt im
# Fastboot-Modus (Product 4ee0). Bei Missachtung: normaler Neustart zurueck
# in die Referenz (Telnet wieder offen).
import base64, hashlib, socket, subprocess, time, datetime, re, sys

FB = "/Users/gregor/Library/Android/sdk/platform-tools/fastboot"
BIN = "/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight/restart2"
EXPECT_SHA = hashlib.sha256(open(BIN, "rb").read()).hexdigest()
LOG = "/Users/gregor/hermes-workspace/omarchy-mobile/device/blueline/firstlight/evidence/restart2-test-2026-11-01.txt"

def log(msg):
    line = datetime.datetime.now().strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")

def conn():
    s = socket.create_connection(("172.16.42.1", 23), timeout=8)
    s.settimeout(3)
    return s

def read_some(s, secs=1.0):
    s.settimeout(secs); buf = b""
    try:
        while True:
            d = s.recv(8192)
            if not d: break
            buf += d
    except socket.timeout: pass
    return buf.decode(errors="replace")

def cmd(s, c, wait=1.5):
    s.sendall((c + "\r\n").encode()); time.sleep(wait)
    return read_some(s)

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

log("=== restart2-Test (Hochladen + Ausfuehren in laufender Referenz) ===")
log("restart2 sha256 (Rechner): " + EXPECT_SHA)
log("vorher: %s | %s | usb=%s" % (fb_getvar("current-slot"), fb_getvar("slot-retry-count:b"), usb_state()))

raw = open(BIN, "rb").read()
import gzip, hashlib as _h
b64 = base64.b64encode(gzip.compress(raw, 9)).decode()
B64_SHA = _h.sha256(b64.encode()).hexdigest()
s = conn(); read_some(s)
cmd(s, "stty -echo 2>/dev/null; true", 0.5)
cmd(s, "rm -f /tmp/r2.b64.gz /tmp/restart2; cat > /tmp/r2.b64.gz <<'EOM'", 0.5)
time.sleep(3); read_some(s, 0.5)   # Sekendaer-Prompt abwarten, PTY-Puffer leer
CH = 1024
t0 = time.time()
for n, i in enumerate(range(0, len(b64), CH)):
    s.sendall((b64[i:i+CH] + "\r\n").encode())
    time.sleep(0.2)
    if n % 16 == 15: read_some(s, 0.05)
s.sendall(b"EOM\n"); time.sleep(2)
read_some(s, 1)
log("Base64(gzip) gesendet (%d Zeichen in %.1fs)" % (len(b64), time.time()-t0))
r = cmd(s, "sha256sum /tmp/r2.b64.gz", 3)
if B64_SHA not in r:
    log("b64-Datei fehlerhaft: " + r.replace("\r\n", " ").strip()[-120:])
    log("ABBRUCH: Base64-Upload beschadigt"); sys.exit(1)
log("b64-Datei SHA im Geraet gleich")
r = cmd(s, "base64 -d /tmp/r2.b64.gz | gzip -d > /tmp/restart2; chmod +x /tmp/restart2; sha256sum /tmp/restart2", 4)
log("sha im Geraet: " + r.replace("\r\n", " ").strip()[-120:])
if EXPECT_SHA not in r:
    log("ABBRUCH: SHA ungleich — Upload beschadigt"); sys.exit(1)
r = cmd(s, "uname -r; cat /proc/sys/kernel/panic")
log("panic-Timeout: " + r.replace("\r\n", " ").strip()[-80:])
log("starte: /tmp/restart2 bootloader")
s.sendall(b"sync; /tmp/restart2 bootloader\r\n")
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
        log("ERGEBNIS: zurueck in der Referenz — restart2 fuehrte normalen Neustart aus (bootloader-Arg ignoriert)")
        break
    if g == "0x4EE0" and t > 5:
        log("ERGEBNIS: FASTBOOT nach %.0fs — restart2 mit 'bootloader' wirkt" % t)
        log("  %s | %s | %s" % (fb_getvar("current-slot"), fb_getvar("slot-retry-count:b"), fb_getvar("slot-unbootable:b")))
        break
else:
    log("Fenster ohne Treffer")
