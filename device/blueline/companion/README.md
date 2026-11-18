# Pixel-Steuerung über Bluetooth

Kopple das Android-Handy und das Pixel in den Bluetooth-Einstellungen. Öffne am Pixel **Bluetooth-Steuerung einrichten** und wähle das gekoppelte Android-Handy aus. Installiere **Pixel-Konsole** auf dem Android-Handy, erlaube den Zugriff auf Geräte in der Nähe und wähle das Pixel aus. `blueline-bluetooth-control disable` in einem Pixel-Terminal entzieht dem Steuergerät den Zugriff.

Die App öffnet eine Shell auf dem Pixel. Die Ausgabe erscheint auf dem Android-Handy. Das Arbeitsverzeichnis und Shell-Variablen bleiben in derselben Sitzung erhalten. **Strg+C** bricht den laufenden Befehl ab, `exit` beendet die Sitzung. Für Hermes-Aufträge braucht das Pixel einen eingerichteten Modellzugang. `hermes chat --query 'Dein Auftrag'` zeigt die Antwort in der Konsole. Die Anzeige ist für Textprogramme ausgelegt.

Der Pixel-Dienst verwendet das authentifizierte RFCOMM-Profil von BlueZ. Für jede Verbindung muss das Gegenüber gekoppelt und am Pixel für die Steuerung gewählt sein. Der Dienst läuft als Sitzungsbenutzer. Die Auswahl verbleibt in der Benutzerkonfiguration auf dem Pixel.

Die Android-App benötigt SDK-Plattform 35, Build Tools 36.0.0 und JDK 17. Setze `ANDROID_SDK_ROOT` und `BLUELINE_ANDROID_JDK` auf die Installationsordner. `BLUELINE_ANDROID_SIGNING` zeigt auf das private Verzeichnis für den APK-Signaturschlüssel. `sh android/build.sh /pfad/zur/pixel-steuerung.apk` baut und verifiziert die App.

## Version 0.4

Die App hat zwei Reiter. **Agent** schickt Aufträge an Hermes auf dem Pixel und zeigt jede Antwort als eigene Karte. Die Chips oben wählen den Anbieter: **Automatisch** (Modell vom Mac per USB, sonst die eigene API), **Antigravity** (nur die eigene API) oder **Offline** (kleines Modell auf dem Pixel). Während ein Auftrag läuft, beantwortet das Eingabefeld Rückfragen von Hermes und ■ bricht ab. Schnellaktionen zeigen Status, Akku und WLAN, schalten die Taschenlampe und den Bildschirm und prüfen, welche Modellzugänge erreichbar sind. Langes Drücken auf eine Antwort kopiert sie. **Konsole** bleibt die freie Shell.

Die App verbindet sich beim Start mit dem zuletzt gewählten Pixel. Langes Drücken auf **Verbinden** wählt ein anderes. Die Shell läuft ohne Echo und Zeileneditor; Aufträge und Schnellaktionen werden zwischen zwei Markierungen (0x1E) gesetzt, damit ihre Ausgabe getrennt vom Konsolenstrom ankommt.
