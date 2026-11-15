# Pixel-Steuerung über Bluetooth

Kopple das Android-Handy und das Pixel in den Bluetooth-Einstellungen. Öffne am Pixel **Bluetooth-Steuerung einrichten** und wähle das gekoppelte Steuergerät aus. Installiere **Pixel-Steuerung** auf dem Android-Handy, erlaube den Zugriff auf Geräte in der Nähe und wähle das Pixel aus. `blueline-bluetooth-control disable` in einem Pixel-Terminal entzieht dem Steuergerät den Zugriff.

Die App kann die Taschenlampe schalten, Kamera oder Dateien öffnen und Hermes einen Textauftrag auf dem Pixel übergeben. Für Hermes-Aufträge braucht das Pixel einen eingerichteten Modellzugang. Der Agent und seine Werkzeugfreigaben erscheinen auf dem Pixel.

Der Pixel-Dienst verwendet das authentifizierte RFCOMM-Profil von BlueZ. Für jede Verbindung muss das Gegenüber gekoppelt und am Pixel für die Steuerung gewählt sein. Der Dienst läuft als Sitzungsbenutzer. Die Auswahl verbleibt in der Benutzerkonfiguration auf dem Pixel.

Die Android-App benötigt SDK-Plattform 35, Build Tools 36.0.0 und JDK 17. Setze `ANDROID_SDK_ROOT` und `BLUELINE_ANDROID_JDK` auf die Installationsordner. `BLUELINE_ANDROID_SIGNING` zeigt auf das private Verzeichnis für den APK-Signaturschlüssel. `sh android/build.sh /pfad/zur/pixel-steuerung.apk` baut und verifiziert die App.
