import subprocess
import time

class KeyboardManager:
    """
    Steuert das Starten und Beenden der virtuellen Bildschirmtastatur (wvkbd).
    Beendet hängende oder versteckte Prozesse aggressiv vor einem Neustart.
    """
    def __init__(self, config):
        self.config = config
        self.process_name = "wvkbd-mobintl"

    def _is_running(self) -> bool:
        """Prüft über subprocess, ob der Prozess aktuell existiert."""
        try:
            result = subprocess.run(
                ["pgrep", "-x", self.process_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def close(self):
        """Beendet die Tastatur sauber."""
        if self._is_running():
            print("DEBUG: Schließe laufende Tastatur-Instanz...")
            subprocess.run(["pkill", "-x", self.process_name])
            time.sleep(0.2)

    def open(self):
        """Startet die Tastatur. Erzwingt einen Neustart, falls sie unsichtbar hängt."""
        if self._is_running():
            print("DEBUG: Tastatur läuft bereits unsichtbar. Erzwinge Neustart...")
            self.close()

        height = self.config.keyboard_height
        print(f"DEBUG: Starte Tastatur mit Höhe {height}px...")
        try:
            # KORREKTUR: Das falsche -l overlay Argument wurde entfernt!
            subprocess.Popen([self.process_name, "-L", str(height)])
        except FileNotFoundError:
            print(f"FEHLER: Ausführbare Datei {self.process_name} nicht gefunden!")

    def toggle(self):
        """Schließt die Tastatur, wenn offen. Öffnet sie, wenn geschlossen."""
        if self._is_running():
            self.close()
        else:
            self.open()