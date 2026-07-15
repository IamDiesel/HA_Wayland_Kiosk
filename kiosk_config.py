import os
import json


class ConfigManager:
    """
    Verwaltet die Konfiguration und Persistenz der Anwendung.
    Lese- und Schreibzugriffe auf die JSON-Datei sind sauber gekapselt.
    """

    def __init__(self, filepath="/home/fuchsi/preferences.json"):
        self.filepath = filepath
        self.preferences = {
            "timeout": 300,
            "is_enabled": True,
            "keyboard_height": 250
        }
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    self.preferences.update(json.load(f))
                    print(f"DEBUG: Preferences geladen: {self.preferences}")
            except Exception as e:
                print(f"FEHLER beim Laden der Preferences: {e}")

    def save(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.preferences, f)
        except Exception as e:
            print(f"FEHLER beim Speichern der Preferences: {e}")

    @property
    def timeout(self):
        return self.preferences.get("timeout", 300)

    @timeout.setter
    def timeout(self, value):
        self.preferences["timeout"] = value
        self.save()

    @property
    def is_enabled(self):
        return self.preferences.get("is_enabled", True)

    @is_enabled.setter
    def is_enabled(self, value):
        self.preferences["is_enabled"] = value
        self.save()

    @property
    def keyboard_height(self):
        return self.preferences.get("keyboard_height", 250)

    @keyboard_height.setter
    def keyboard_height(self, value):
        self.preferences["keyboard_height"] = value
        self.save()