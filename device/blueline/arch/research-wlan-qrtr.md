# WCN3990 / QRTR-Transport auf SDM845 (Pixel 3 „blueline“)

**Stand:** 2026-11-07
**Kernelbaum:** `~/hermes-workspace/linux-sdm845` (v7.1.0-rc1, Commit `85f1df2a4`)
**Frage:** Wie kommt der `wlfw`-QMI-Client des `ath10k_snoc` auf sdm845 an den WCN3990, und braucht es dafür einen DTS-Patch (`qcom,smd-edge`, `IPCRTR`, `glink-edge`)?

---

## 0. Ergebnis in Kurzform

1. **Es fehlt kein DTS-Knoten.** Der QRTR-Transport für den WCN3990 existiert im mainline-`sdm845.dtsi` bereits – als **dynamisch vom Modem-Firmware erzeugter rpmsg-Kanal `IPCRTR` auf der GLINK-Edge des MSS** (`4080000.remoteproc`, Label `modem`, `qcom,remote-pid = <1>`). Ein statischer DT-Knoten ist dafür weder nötig noch wirksam.
2. Der `wlfw`-Dienst des WCN3990 ist auf sdm845/msm8998 **hinter dem Modem-Subsystem (MSS)** erreichbar; `wlanmdsp.mbn` liegt im Firmware-Verzeichnis neben `modem.mbn`. Ohne laufendes MSS gibt es keinen `IPCRTR`-Kanal und keine Antwort auf den `wlfw`-Lookup → genau das beobachtete „`snoc probe`, dann Stille“.
3. Das `ipq6018`-Muster (`qrtr_requests { qcom,glink-channels = "IPCRTR"; }`) ist **nicht übertragbar**: sdm845 nutzt GLINK (nicht SMD), DT-Kinder erzeugen keine Kanäle, und die GLINK-Edge-Bindung erlaubt nur `apr`/`fastrpc`/`gpr` (`additionalProperties: false`).
4. **Fazit:** Kein DTS-Patch, keine neue Treiberarbeit. Der Fix ist MSS-/Firmware-/Userspace-Bring-up (`mba.mbn`, `modem.mbn`, `wlanmdsp.mbn`, `rmtfs`, `pd-mapper`, `tqftpserv`, `qrtr-smd`).

---

## 1. Lokale Ausgangslage (verifiziert im Baum)

| Ort | Zeilen | Inhalt |
|---|---|---|
| `arch/arm64/boot/dts/qcom/sdm845.dtsi` | 5611–5632 | `wifi: wifi@18800000`, `compatible = "qcom,wcn3990-wifi"`, `status = "disabled"`, 12 CE-Interrupts (GIC_SPI 414–425), `iommus = <&apps_smmu 0x0040 0x1>` |
| dito | 852–855 | `wlan_msa_mem: wlan-msa@8df00000`, Größe `0x100000` → passt exakt zur Logzeile `qmi msa.paddr: 0x8df00000` |
| dito | 3434–3498 | `mss_pil: remoteproc@4080000`, `compatible = "qcom,sdm845-mss-pil"` |
| dito | 3491–3496 | `glink-edge { interrupts = <GIC_SPI 449 …>; label = "modem"; qcom,remote-pid = <1>; mboxes = <&apss_shared 12>; }` – **ohne Kinder** |
| dito | 925–933 | ADSP-`glink-edge`, Label `lpass`, Kind `apr` mit `qcom,glink-channels = "apr_audio_svc"` |
| dito | 1061–1070 | CDSP-`glink-edge`, Label `turing`, Kind `fastrpc` mit `fastrpcglink-apps-dsp` |
| dito | 3541–3550 | SLPI-`glink-edge`, Label `dsps`, Kind `fastrpc` |
| `sdm845-google-common.dtsi` | 644–649 | `&mss_pil { firmware-name = "qcom/sdm845/Google/blueline/mba.mbn", "…/modem.mbn"; status = "okay"; }` |
| dito | 925–934 | `&wifi` mit Versorgungsrails, `qcom,snoc-host-cap-8bit-quirk` und `status = "okay"` |
| `sdm845-google-blueline.dts` | 104–106 | `&wifi { qcom,calibration-variant = "Google_blueline"; }` |

**Wichtig:** Das WLAN-DT ist für blueline bereits vollständig (Versorgung, Quirk, Kalibrierungsvariante, MSA-Region). Es fehlt an dieser Stelle nichts. `qcom,smd` kommt in `sdm845.dtsi` **0×** vor – sdm845 nutzt ausschließlich GLINK.

Der beobachtete Logablauf ist der normale Probe-Pfad **vor** dem QMI-Handshake:

- `drivers/net/wireless/ath/ath10k/snoc.c:1578–1609` – `ath10k_setup_msa_resources()`, druckt `qmi msa.paddr: …`
- `snoc.c:1858` – `ath10k_qmi_init()`
- `snoc.c:1864` – `snoc probe`
- `drivers/net/wireless/ath/ath10k/qmi.c:1115` – `qmi_add_lookup(&qmi->qmi_hdl, WLFW_SERVICE_ID_V01, …)`

Ab hier hängt alles am QRTR-Transport. Kommt keine Antwort, bleibt es bei „snoc probe“ – genau das Symptom.

---

## 2. Wie der Transport auf SDM845 tatsächlich funktioniert

### 2.1 Der Stack

```
ath10k_qmi (AF_QIPCRTR-Socket)
        │
   qrtr-ns (In-Kernel-Nameserver, net/qrtr/ns.c)
        │
   qrtr-smd  (rpmsg-Treiber für den Kanalnamen "IPCRTR", net/qrtr/smd.c)
        │
   GLINK-SMEM  (rpmsg/qcom_glink_*, Edge "modem" = MSS, remote-pid 1)
        │
   Modem-Firmware (MSS) mit WLAN-MDSP-Image
        │
   WCN3990 (WLFW-QMI-Dienst)
```

### 2.2 Der `IPCRTR`-Kanal wird zur Laufzeit erzeugt – nicht im DT

- `net/qrtr/smd.c:92–95`: Der rpmsg-Treiber matcht ausschließlich auf den **Kanalnamen** `"IPCRTR"`; `MODULE_ALIAS("rpmsg:IPCRTR")` (Zeile 109) sorgt für das Autoladen, sobald ein rpmsg-Device dieses Namens erscheint.
- `drivers/rpmsg/qcom_glink_native.c:1636–1694` (`qcom_glink_rx_open`): Öffnet die **Gegenseite** einen Kanal, wird – falls lokal unbekannt – `create_device = true` gesetzt und ein rpmsg-Device mit genau diesem Namen registriert. Das ist der Pfad, über den `IPCRTR` auf der Modem-Edge entsteht.
- `qcom_glink_native.c:1593–1613` (`qcom_glink_match_channel`) sucht zu einem Kanalnamen lediglich den passenden **DT-Knoten** (für `rpdev->dev.of_node`). Ein DT-Kind erzeugt **keinen** Kanal.
- `qcom_glink_native.c:1247–1256`: Kanäle werden nur bei lokalem `rpmsg_create_ept` oder bei remote-initiiertem `rx_open` alloziert – nie beim Parsen der GLINK-Edge.
- `drivers/remoteproc/qcom_common.c:240–245`: Die GLINK-Edge wird als Kind `glink-edge` des Remoteproc-Knotens gefunden (deshalb liegt sie in `sdm845.dtsi` unter `mss_pil`).

### 2.3 Belege, dass der Dienst am MSS hängt

- **OnePlus 6 (sdm845), pmOS, Kernel 6.13-rc2 – dmesg-Timeline** (Gist, siehe Quellen):
  - `28.239 s` `ath10k_snoc 18800000.wifi: Adding to iommu group 10` (Probe, `wlfw`-Lookup wird registriert)
  - `29.326 s` `remoteproc remoteproc3: powering up 4080000.remoteproc` / `Booting fw image qcom/sdm845/oneplus6/mba.mbn`
  - `31.423 s` `remoteproc remoteproc3: remote processor 4080000.remoteproc is now up`
  - `32.427 s` `ath10k_snoc … qmi chip_id 0x30214 chip_family 0x4001 …`
  - `35.718 s` `wcn3990 hw1.0 target …` → Firmware-Download läuft.
  D. h. **erst mit dem MSS-Boot antwortet WLFW** – 4 s nach dem ath10k-Probe.
- **pmOS-Wiki SDM845:** „The modem is booted by the Q6V5 MSS Peripheral Image Loader, **it is required to boot the WiFi adapter**.“ Außerdem wird für WLAN `rmtfs pd-mapper tqftpserv` verlangt.
- **pmOS-Wiki MSM8998 (gleiche WCN3990-Architektur):** „The **MSS (modem) remoteproc needs to be running** with firmware extracted from the device partitions“; „Make sure your OEM `wlanmdsp.mbn` is **in the same directory** with `modem.mdt` (or `modem.mbn`)“; Pakete `pd-mapper`, `tqftpserv`, `qrtr`, `rmtfs`.
- **jhugo-README (5.5-WLAN-Anleitung):** `WLANMDSP.MBN` in dasselbe Verzeichnis wie die Modem-Firmware kopieren; `qrtr-ns`, `rmtfs`, `pd-mapper`, `tqftpserv` als Dienste.
- **Firmware-Repo sdm845-mainline/blueline:** `lib/firmware/qcom/sdm845/Google/blueline/` enthält `mba.mbn`, `modem.mbn`, `modemr.jsn`, `modemuw.jsn` **und `wlanmdsp.mbn`** – genau die Kopplung, die die pmOS-Doku beschreibt.

> Einordnung: Ob der WLFW-Dienst auf dem Modem-DSP läuft oder das Modem ihn per IPC-Router an den WCN3990 weiterreicht, ist in mainline nicht dokumentiert. Operativ ist das MSS zwingend – alle Quellen und der Log stimmen darin überein.

### 2.4 Lookup-Timing ist tolerant, aber nur gegenüber einem *späten* Modem

`net/qrtr/ns.c:498–538` (`ctrl_cmd_new_server`): Ein neu angemeldeter Dienst benachrichtigt **alle noch offenen Lookups**. `qmi_add_lookup` ist daher kein Einmal-Schuss mit Sekunden-Timeout – im OnePlus-6-Log kommt die Antwort 4 s nach dem Probe an. Ein **nie** bootendes Modem bleibt aber für immer unbeantwortet.

---

## 3. Vendor-DT (Android `android-msm-bluecross-4.9-pie-qpr1`, blueline)

Datei: `arch/arm64/boot/dts/qcom/sdm845.dtsi` im Vendor-Baum.

| Zeilen | Knoten | Inhalt |
|---|---|---|
| 569 | `wlan_fw_region@0x8df00000` | WLAN-MSA-Region, `0x100000` – identisch zu mainline `wlan_msa_mem` |
| 3081–3111 | `qcom,icnss@18800000` | `compatible = "qcom,icnss"`, `reg = <0x18800000 0x800000>, <0xa0000000 0x10000000>, <0xb0000000 0x10000>`, `reg-names = "membase","smmu_iova_base","smmu_iova_ipa"`, IRQs 414–425, `qcom,wlan-msa-memory = <0x100000>`, Versorgung `pm8998_l5/l7/l17/l25` |
| 2341–2345 | `qcom,ipc_router` | `compatible = "qcom,ipc_router"`, `qcom,node-id = <1>` |
| 2346–2355 | `qcom,ipc_router_modem_xprt` | `compatible = "qcom,ipc_router_glink_xprt"`, **`qcom,ch-name = "IPCRTR"`**, `qcom,xprt-remote = "mpss"`, `qcom,glink-xprt = "smem"`, `qcom,xprt-linkid = <1>`, `qcom,xprt-version = <1>`, `qcom,fragmented-data` |
| 2356–2365 | `…_q6_xprt` | dito, `xprt-remote = "lpass"` |
| 2366–2377 | `…_dsps_xprt` | dito, `xprt-remote = "dsps"` |
| 2378–2388 | `…_cdsp_xprt` | dito, `xprt-remote = "cdsp"` |
| 2157–2170 | `qcom,glink-mailbox-xprt-spss@1885008` | Mailbox-XPRT, Label `spss` – **nicht WLAN** |

**Kernbefund:** Auch das Vendor-DT enthält **keinen** `qcom,smd`, `smd-edge`, `glink-edge`, `qrtr-smem` oder WLAN-spezifischen `IPCRTR`-Knoten. Der IPC-Router kennt `IPCRTR`-XPRTs nur zu `mpss`, `lpass`, `dsps`, `cdsp` – **kein `wlan`/`spss`-XPRT für WLAN**. Der WLAN-QMI-Verkehr läuft also bereits downstream über einen dieser Kanten, praktisch über `mpss` (deckt sich mit `wlanmdsp.mbn` neben `modem.mbn`). Downstream heißt der Host-Treiber `icnss`, mainline `ath10k_snoc` – die Transportanforderung ist identisch.

---

## 4. Lokale Muster (grep über `arch/arm64/boot/dts/qcom/`)

```
$ grep -rn "IPCRTR" arch/arm64/boot/dts/qcom/
ipq6018.dtsi:860:  qcom,glink-channels = "IPCRTR";

$ grep -rn "smd-edge" arch/arm64/boot/dts/qcom/ | cut -d: -f1 | sort -u
msm8939.dtsi msm8953.dtsi msm8996.dtsi   (nur ältere SoCs, SMD)

$ grep -c "qcom,smd" arch/arm64/boot/dts/qcom/sdm845.dtsi
0
```

| Datei/Zeile | Muster | Bewertung für sdm845 |
|---|---|---|
| `ipq6018.dtsi:855–864` | GLINK-Edge Label `rtr` (WCSS-Remoteproc) + `qrtr_requests { qcom,glink-channels = "IPCRTR"; }` | Anderer SoC, anderer Remoteproc; Kanal wird trotzdem erst durch die Gegenseite geöffnet. Keine Vorlage. |
| `msm8953.dtsi:215–228` | `smd-edge { qcom,smd-edge = <15>; rpm_requests { qcom,smd-channels = "rpm_requests"; } }` | **SMD**, nicht GLINK – auf sdm845 falsch |
| `msm8996.dtsi:2536, 2612, 3574` | `smd-edge` (MSS/ADSP/SLPI) | dito |
| `sdm845.dtsi:3491–3496` | MSS-`glink-edge`, keine Kinder | **Hier** erscheint `IPCRTR` dynamisch |
| `sdm845.dtsi:925–933, 1061–1070, 3541–3550` | `apr_audio_svc`, `fastrpcglink-apps-dsp` | Nur statische DSP-Kanäle, kein QRTR |
| `net/qrtr/smd.c:92–95,109` | rpmsg-ID `"IPCRTR"`, `MODULE_ALIAS("rpmsg:IPCRTR")` | Bindet an jeden so benannten Kanal, egal an welcher Edge |
| `drivers/rpmsg/qcom_glink_native.c:1636–1694` | `qcom_glink_rx_open()` erzeugt rpmsg-Device für remote geöffneten Kanal | **Der** Erzeugungspfad – ohne DT |
| `Documentation/devicetree/bindings/remoteproc/qcom,glink-edge.yaml:76` | `additionalProperties: false`; nur `apr`/`fastrpc`/`gpr` erlaubt | Ein `qrtr_requests`-Kind wäre schema-invalid |

---

## 5. Warum es keinen DTS-Patch gibt (und warum das kein Treiberdefizit ist)

1. **Falscher Bus:** `qcom,smd`/`qcom,smd-edge` beschreibt den alten SMD-Shared-Memory-Stack (z. B. msm8953 RPM). sdm845 hat keinen SMD-Knoten; ein solcher würde nicht binden und nichts transportieren.
2. **DT erzeugt keine GLINK-Kanäle:** Kanäle entstehen ausschließlich durch `rx_open` (remote) oder `rpmsg_create_ept` (lokal). `qcom,glink-channels` ordnet einem Kanal nur einen `device_node` zu.
3. **Schema verbietet es:** `qcom,glink-edge.yaml` hat `additionalProperties: false` und nur `apr`, `fastrpc`, `gpr` als Kinder.
4. **Upstream funktioniert ohne:** `db845c`, `mtp`, `LG judyln/judyp`, `shift-axolotl`, `blueline` und `crosshatch` haben alle **keinen** `IPCRTR`-Knoten; es genügt `&wifi` mit Versorgung + Quirk (siehe LG-Patch und axolotl-Patch in den Quellen).
5. **Der Engpass liegt woanders:** Der Kanal erscheint erst, wenn die Modem-Firmware läuft. Kein DT-Eintrag kann Firmware starten oder den `wlfw`-Dienst herbeiführen.

**Explizit:** Ein Patch wie

```dts
/* NICHT anwenden – würde nichts bewirken */
&mss_pil {
        glink-edge {
                qrtr_requests {
                        qcom,glink-channels = "IPCRTR";
                };
        };
};
```

wäre wirkungslos (kein Kanal wird alloziert), würde `dtbs_check` verletzen und das eigentliche Problem (MSS bootet nicht) nur verdecken. Er wird hier **bewusst nicht** vorgeschlagen.

---

## 6. Was tatsächlich zu tun ist – Prüfplan

### 6.1 MSS-Status

```sh
dmesg | grep -iE 'q6v5-mss|mba|modem|remoteproc'
for r in /sys/class/remoteproc/remoteproc*; do
        echo "$r: $(cat $r/name) $(cat $r/state) $(cat $r/firmware 2>/dev/null)"
done
```

Erwartet: `4080000.remoteproc` mit `name = mss` (oder `4080000.remoteproc`), `state = running`.
Typische Fehler: `failed to load mba.mbn`, `timed out waiting for handover`, `failed to acquire pdc reset`, `remoteproc … releasing`.

### 6.2 Firmware

```sh
ls -l /lib/firmware/qcom/sdm845/Google/blueline/
```

Erwartet: `mba.mbn`, `modem.mbn`, `modemr.jsn`, `modemuw.jsn`, **`wlanmdsp.mbn`**.
`wlanmdsp.mbn` muss im **selben** Verzeichnis wie `modem.mbn` liegen (pmOS-Doku/msm8998 + jhugo).

### 6.3 QRTR-Kette

```sh
zcat /proc/config.gz | grep -E 'CONFIG_QRTR|CONFIG_RPMSG_QCOM_GLINK|CONFIG_QCOM_Q6V5_MSS'
lsmod | grep -E 'qrtr|glink|q6v5' ; modprobe qrtr-smd   # Modulname: qrtr-smd
ls /sys/bus/rpmsg/devices/ | grep -i IPCRTR
qrtr-lookup
```

Erwartet:
- `…:glink-edge.IPCRTR.-1.-1` unter `/sys/bus/rpmsg/devices/` (auf sdm845 typischerweise `4080000.remoteproc:glink-edge.IPCRTR.-1.-1`),
- `qrtr-lookup` listet Dienste; **ohne WLFW-Eintrag** ist der `wlfw`-Dienst nicht erreichbar → MSS nicht oben.

### 6.4 Userspace

```sh
rc-service rmtfs status; rc-service pd-mapper status; rc-service tqftpserv status
```

Ohne `rmtfs`/`pd-mapper`/`tqftpserv` bleibt das Modem häufig hängen bzw. der Dienst kommt nie hoch (pmOS-Angaben für sdm845 und msm8998).

### 6.5 ath10k neu proben (schneller Test)

```sh
rmmod ath10k_snoc; modprobe ath10k_snoc
dmesg -w | grep -i ath10k
```

Erwartet bei funktionierendem MSS: `qmi chip_id …` und `qmi fw_version …` (beides `ath10k_info`, `qmi.c:635–639`), danach `wcn3990 hw1.0 target …`.
Bleibt es bei `snoc probe`, ist der QRTR-Pfad tot.

### 6.6 Nur falls danach ein *anderes* Symptom auftritt

Wenn `chip_id`/`fw_version` erscheinen, der Download aber bei „MSA ready“ stehen bleibt (msm8998-Klassiker), hilft:

```dts
&wifi {
        qcom,no-msa-ready-indicator;
};
```

Belege: Freebox/msm8998-Thread (Lore) und Commit `737abcabe97b` („arm64: dts: qcom: msm8998: set qcom,no-msa-ready-indicator for wifi“, seit 6.11). In diesem Baum ist das Property bei `msm8998.dtsi:3397` und `sdm630.dtsi:2599` gesetzt, bei sdm845-Geräten **nicht** – und die funktionierenden sdm845-Logs (LG/OP6) brauchen es nicht. Es ist also **kein** Bestandteil des hier diskutierten Symptoms.

---

## 7. Fazit

- Der QRTR-Transport für den WCN3990 ist auf sdm845 **vorhanden** und braucht **keinen DTS-Knoten**: `IPCRTR` erscheint dynamisch auf der MSS-GLINK-Edge, sobald die Modem-Firmware läuft; `qrtr-smd` bindet über den rpmsg-Namen.
- Das beobachtete „`qmi msa.paddr … snoc probe`, dann Stille“ ist kein fehlender `smd-edge`, sondern ein **nicht erreichbarer `wlfw`-Dienst** – weil das MSS nicht (rechtzeitig/überhaupt) läuft oder `qrtr-smd`/`qrtr` fehlt.
- Es ist **keine neue Treiberarbeit** nötig. Zu prüfen sind ausschließlich: MSS-Remoteproc-Status, Firmware-Satz inkl. `wlanmdsp.mbn`, `rmtfs`/`pd-mapper`/`tqftpserv`, `CONFIG_QRTR_SMD`/`qrtr-smd`, und ob `qrtr-lookup` WLFW zeigt.
- Das `ipq6018`-`IPCRTR`-Muster ist ein Sonderfall (WCSS-Remoteproc) und **keine** Vorlage für sdm845.

---

## 8. Quellen

**Mainline / Doku**
- sdm845.dtsi (mainline): <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/boot/dts/qcom/sdm845.dtsi>
- ipq6018.dtsi mit `IPCRTR`-Kind: <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/boot/dts/qcom/ipq6018.dtsi#n860>
- qrtr-smd (rpmsg-ID `IPCRTR`): <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/qrtr/smd.c>
- GLINK-Kanalerzeugung: <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/rpmsg/qcom_glink_native.c>
- GLINK-Edge-Bindung: <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/devicetree/bindings/remoteproc/qcom,glink-edge.yaml>
- ath10k-Bindung (`qcom,no-msa-ready-indicator`): <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/devicetree/bindings/net/wireless/qcom,ath10k.yaml>
- msm8998-`no-msa-ready`-Commit: <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=737abcabe97bb37e38be2504acd28ad779dbaf3d>

**sdm845-WLAN-Upstreaming (2026)**
- LG-WLAN-Patch mit funktionierendem QMI-Log: <https://lkml.iu.edu/hypermail/linux/kernel/2604.0/02729.html>
- axolotl: WLAN/BT nur über `&wifi` + PMU: <https://patchew.org/linux/20260415-axolotl-wifi-v1-1-07df39cfc0a4@ixit.cz/>
- sdm845-google: Wi-Fi/BT-PMU: <https://lore.kernel.org/all/20260327-wcn3990-pwrctl-sdm845-v1-0-3f5c34e3fdd0@ixit.cz/>

**Vendor-DT (android-msm-bluecross-4.9, blueline)**
- `arch/arm64/boot/dts/qcom/sdm845.dtsi`, Branch `android-msm-bluecross-4.9-pie-qpr1`:
  <https://android.googlesource.com/kernel/msm/+/refs/heads/android-msm-bluecross-4.9-pie-qpr1/arch/arm64/boot/dts/qcom/sdm845.dtsi>

**Community-/Erfahrungsquellen**
- pmOS-Wiki SDM845 („modem … required to boot the WiFi adapter“, rmtfs/pd-mapper/tqftpserv, IPCRTR-rpmsg-Device):
  <https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_845/850_(SDM845/SDM850)>
- pmOS-Wiki MSM8998/WLAN (MSS muss laufen, `wlanmdsp.mbn` neben `modem.mbn`, Pakete, MSA-Workaround):
  <https://wiki.postmarketos.org/wiki/Qualcomm_Snapdragon_835_(MSM8998)#WLAN>
- OnePlus-6-dmesg mit Timeline MSS 31.4 s → WLFW 32.4 s: <https://gist.github.com/feisuzhu/c7665b44b5eec91963abf008f9f639b8>
- jhugo-WLAN-README (5.5, `WLANMDSP.MBN` + Dienste): <https://github.com/jhugo/linux/blob/5.5rc2_wifi/README>
- blueline-Firmware-Repo (enthält `wlanmdsp.mbn` neben `modem.mbn`): <https://gitlab.com/sdm845-mainline/firmware-google-pixel3>
- Freebox/msm8998-Thread zu fehlendem MSA_READY: <https://lore.kernel.org/ath10k/14daa98e-7fd3-4ebb-87bb-5d2c1fba679f@freebox.fr/>
