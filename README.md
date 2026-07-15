---

# Home Assistant Wayland Kiosk (Raspberry Pi 5 / Bookworm)

<img width="525" height="370" alt="image" src="https://github.com/user-attachments/assets/ef043c91-d373-4f5c-ad2b-236b9b3fa056" />


Dieses Repository enthält die Konfiguration und Steuerungsskripte für ein Home Assistant Kiosk-Display. Das System ist spezifisch für den **Raspberry Pi 5 unter Raspberry Pi OS (Bookworm, Wayland)** ausgelegt. Es steuert das Display-Timeout, verarbeitet Touch-Gesten und stellt eine virtuelle On-Screen-Tastatur bereit, die über dem Browser gerendert wird.

## Software-Komponenten

Das Setup basiert auf dem Zusammenspiel folgender lokaler und netzwerkbasierter Komponenten:

* **labwc (Wayland)**: Ein leichtgewichtiger Window-Manager für Wayland, der als Laufzeitumgebung für den Kiosk-Modus dient.
* **Chromium**: Der Webbrowser läuft im nativen Wayland-Modus und stellt das Home Assistant Dashboard im Vollbild (`--kiosk`) dar.
* **wvkbd**: Eine virtuelle Wayland-Bildschirmtastatur. Sie rendert auf dem `overlay`-Layer, um sicherzustellen, dass sie nicht vom Vollbild-Browser verdeckt wird.
* **wlopm**: Ein Kommandozeilen-Tool zur Steuerung des Power-Managements (DPMS) verbundener Wayland-Displays (Bildschirm-Standby).
* **evdev**: Eine Linux-Kernel-Schnittstelle, die es dem Kiosk-Daemon erlaubt, rohe Touch- und Hardware-Events abzufangen, noch bevor sie den Window-Manager erreichen.
* **Kiosk Daemon (`main_sleep_keyboard.py`)**: Ein Python-Hintergrunddienst. Er überwacht Eingaben via `evdev` zur Erkennung von Bildschirm-Inaktivität (Display-Sleep) und wertet Multitouch-Wischgesten (z. B. 2-Finger-Swipe) aus. Zudem orchestriert er den Prozess der On-Screen-Tastatur.
* **Zugangsdaten (`kiosk_credentials.py`)**: Eine ausgelagerte Konfigurationsdatei für die MQTT- und Netzwerk-Zugangsdaten.
* **Home Assistant Frontend (JavaScript / MQTT)**: Ein lokales Skript, das in das Home Assistant Dashboard injiziert wird. Über einen URL-Parameter (`?kiosk_keyboard=true`) autorisiert es den Kiosk-Browser im `localStorage`, erfasst Klicks auf Textfelder und steuert die Tastatur bidirektional über MQTT.

---

## 1. Konfiguration der Zugangsdaten

Bevor das System in Betrieb genommen wird, müssen die netzwerkspezifischen Zugangsdaten für die MQTT-Kommunikation konfiguriert werden.

Erstelle im selben Verzeichnis wie die Python-Skripte eine Datei namens `kiosk_credentials.py` und passe die Werte an deine lokale Home Assistant / MQTT-Umgebung an:

```python
# kiosk_credentials.py

MQTT_USER = "dein_mqtt_nutzer"
MQTT_PASSWORD = "dein_mqtt_passwort"
MQTT_BROKER_IP = "192.168.X.X" # IP-Adresse des MQTT-Brokers / Home Assistant

```

---

## 2. Installation der virtuellen Tastatur (wvkbd)

Das Standardpaket von `wvkbd` in den Paketquellen von Raspberry Pi OS (Bookworm) ist veraltet. Um zu verhindern, dass Chromium im Kiosk-Modus (`FULLSCREEN`-Layer) die Tastatur verdeckt, muss die aktuelle Version aus dem Quellcode kompiliert werden. Diese Version zwingt die Tastatur systemseitig in den obersten `OVERLAY`-Layer.

Führe dazu folgende Befehle im Terminal des Raspberry Pi aus:

```bash
# 1. Abhängigkeiten installieren
sudo apt update
sudo apt install -y git build-essential pkg-config libwayland-dev libpango1.0-dev libcairo2-dev libxkbcommon-dev wayland-protocols

# 2. Quellcode herunterladen
git clone https://github.com/jjsullivan5196/wvkbd.git
cd wvkbd

# 3. Kompilieren und installieren (mit mobilem Layout)
make LAYOUT=mobintl
sudo make install LAYOUT=mobintl

```

---

## 3. Home Assistant JavaScript-Integration

Damit der Raspberry Pi erfährt, wann ein Textfeld angetippt wurde, muss das Kiosk-Skript in Home Assistant hinterlegt werden.

1. Erstelle im Home Assistant Konfigurationsverzeichnis (z. B. über das File Editor Add-on) im Ordner `/config/www/` die Datei `kiosk_keyboard.js`.
2. Füge folgenden Code ein:

```javascript
console.log("Kiosk: Tastatur-Skript geladen.");

// 1. Zertifikat in den Kiosk-Browser schreiben (wird durch die URL getriggert)
if (window.location.search.includes("kiosk_keyboard=true")) {
    localStorage.setItem("is_fuchsi_kiosk", "true");
    console.log("Kiosk: Passwort erkannt! Dieser Browser ist nun dauerhaft als Kiosk autorisiert.");
}

// 2. Klick-Erkennung aktivieren, sofern das Zertifikat im Browser vorliegt
if (localStorage.getItem("is_fuchsi_kiosk") === "true") {
    console.log("Kiosk: Autorisierter Kiosk-Browser erkannt! Aktiviere Touch-Steuerung.");

    window.addEventListener("click", function(e) {
        const path = e.composedPath ? e.composedPath() : [];
        // Sucht im DOM nach Eingabefeldern, auch innerhalb von Shadow DOMs
        const isInput = path.some(el => 
            el.tagName === "INPUT" || 
            el.tagName === "TEXTAREA" || 
            el.tagName === "HA-TEXTFIELD" ||
            el.tagName === "HA-SELECTOR-TEXT"
        );

        try {
            const ha = document.querySelector("home-assistant");
            if (ha && ha.hass) {
                if (isInput) {
                    ha.hass.callService("mqtt", "publish", {
                        topic: "kiosk/display/keyboard/open",
                        payload: "PRESS"
                    });
                } else {
                    ha.hass.callService("mqtt", "publish", {
                        topic: "kiosk/display/keyboard/close",
                        payload: "PRESS"
                    });
                }
            }
        } catch (error) {
            console.error("Kiosk: Fehler beim Senden des MQTT-Befehls:", error);
        }
    }, true);
}

```

3. Binde das Skript in Home Assistant ein: Gehe zu **Einstellungen -> Dashboards -> Ressourcen** (oben rechts über das Drei-Punkte-Menü).
4. Füge eine neue Ressource hinzu:
* **URL:** `/local/kiosk_keyboard.js?v=1`
* **Ressourcentyp:** JavaScript-Modul



---

## 4. Autostart auf dem Raspberry Pi konfigurieren

Die gesamte Orchestrierung der Prozesse findet beim Systemstart durch den Window-Manager `labwc` statt. Öffne die Konfigurationsdatei mit einem Texteditor:

```bash
nano ~/.config/labwc/autostart

```

Füge die folgenden Zeilen ein.
*Hinweis: Ersetze `/pfad/zum/kiosk_script/` durch den tatsächlichen Pfad zu deinen Python-Dateien und passe die `URL` in der letzten Zeile an deine Home Assistant Instanz an.*

```bash
# 1. Chromium zwingen, nativ unter Wayland zu laufen
export OZONE_PLATFORM=wayland

# 2. Chromium zwingen, Touch-Gesten nativ zu nutzen
export USE_WAYLAND_GRAB=1

# 3. Bildschirmschoner und Tastatur-Daemon im Hintergrund starten MIT LOGGING (-u = unbuffered)
/usr/bin/python3 -u /pfad/zum/kiosk_script/main_sleep_keyboard.py > /pfad/zum/kiosk_script/main_sleep_keyboard.log 2>&1 &

# 4. Chromium als Kiosk, mit 3 Sekunden Startverzögerung für saubere Inputs
(sleep 3 && chromium --kiosk --noerrdialogs --disable-infobars --password-store=basic "http://<IP-DEINES-HA>:<PORT>/<DEIN-DASHBOARD-PFAD>?kiosk_keyboard=true") &

```

### Parameter-Erklärung

* **`OZONE_PLATFORM=wayland`**: Deaktiviert XWayland für Chromium. Dies ist zwingend erforderlich, damit die Bildschirmtastatur auf dem korrekten Layer (`overlay`) gerendert werden kann.
* **`USE_WAYLAND_GRAB=1`**: Erlaubt es Chromium, Touch-Events direkt zu verarbeiten und verhindert, dass `labwc` Touch-Eingaben vor der Weboberfläche abfängt.
* **`-u` Flag (Python)**: Erzwingt die unbuffered Ausgabe. Log-Ereignisse des Python-Skripts werden sofort in die Datei geschrieben.
* **`> ... 2>&1 &`**: Leitet die Standardausgabe (`stdout`) und Fehler (`stderr`) in ein Logfile um und lagert den Prozess in den Hintergrund aus (`&`).
* **`sleep 3`**: Garantiert, dass der Kiosk-Daemon gestartet und die Hardware über `evdev` registriert ist, bevor Chromium geöffnet wird.
* **`?kiosk_keyboard=true`**: Dies ist das einmalige Autorisierungs-Flag für Home Assistant. Hierdurch weiß das Dashboard, dass es auf dem physischen Kiosk-Terminal läuft, und schreibt das Zertifikat in den `localStorage`.

---

## 5. Debugging

Da der Kiosk-Controller im Hintergrund läuft, werden sämtliche Events (Timeouts, MQTT-Befehle, Touch-Gesten) in die definierte Logdatei geschrieben. Für eine Echtzeit-Diagnose des Systems:

```bash
tail -f /pfad/zum/kiosk_script/main_sleep_keyboard.log

```
