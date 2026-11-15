# Pixel-Steuerung über Bluetooth

Kopple das Android-Handy und das Pixel in den Bluetooth-Einstellungen. Öffne am Pixel **Bluetooth-Steuerung einrichten** und wähle das gekoppelte Android-Handy aus. Installiere **Pixel-Konsole** auf dem Android-Handy, erlaube den Zugriff auf Geräte in der Nähe und wähle das Pixel aus. `blueline-bluetooth-control disable` in einem Pixel-Terminal entzieht dem Steuergerät den Zugriff.

Die App öffnet eine Shell auf dem Pixel. Die Ausgabe erscheint auf dem Android-Handy. Das Arbeitsverzeichnis und Shell-Variablen bleiben in derselben Sitzung erhalten. **Strg+C** bricht den laufenden Befehl ab, `exit` beendet die Sitzung. Für Hermes-Aufträge braucht das Pixel einen eingerichteten Modellzugang. `hermes chat --query 'Dein Auftrag'` zeigt die Antwort in der Konsole. Die Anzeige ist für Textprogramme ausgelegt.

Der Pixel-Dienst verwendet das authentifizierte RFCOMM-Profil von BlueZ. Für jede Verbindung muss das Gegenüber gekoppelt und am Pixel für die Steuerung gewählt sein. Der Dienst läuft als Sitzungsbenutzer. Die Auswahl verbleibt in der Benutzerkonfiguration auf dem Pixel.

Die Android-App benötigt SDK-Plattform 35, Build Tools 36.0.0 und JDK 17. Setze `ANDROID_SDK_ROOT` und `BLUELINE_ANDROID_JDK` auf die Installationsordner. `BLUELINE_ANDROID_SIGNING` zeigt auf das private Verzeichnis für den APK-Signaturschlüssel. `sh android/build.sh /pfad/zur/pixel-steuerung.apk` baut und verifiziert die App.
