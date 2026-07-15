import select
import signal
import sys
import time
import evdev

from kiosk_config import ConfigManager
from kiosk_mqtt import MqttController
from display_sleep_controller import SleepHandlerCore
from kiosk_keyboard import KeyboardManager
from kiosk_gesture import SwipeUpRecognizer


class KioskApp:
    def __init__(self):
        self.running = True
        self.config = ConfigManager()

        self.devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        self.fds = {dev.fd: dev for dev in self.devices}

        if not self.devices:
            print("WARNUNG: Keine evdev Eingabegeräte gefunden! Touch funktioniert evtl. nicht.")
        else:
            print(f"DEBUG: {len(self.devices)} Eingabegeräte initialisiert.")

        self.sleep_handler = SleepHandlerCore(self.config, self.devices, self.fds)
        self.keyboard = KeyboardManager(self.config)

        # GEÄNDERT: Nutzt nun .toggle anstatt .open, damit die Tastatur auch wieder schließt!
        self.gesture_recognizer = SwipeUpRecognizer(on_swipe_callback=self.keyboard.toggle)

        # GEÄNDERT: Callback zum Schließen der Tastatur an MQTT übergeben
        self.mqtt = MqttController(
            config=self.config,
            on_interaction_callback=self.sleep_handler.register_activity,
            on_keyboard_close_callback=self.keyboard.close,
            on_keyboard_open_callback=self.keyboard.open
        )

        self._setup_signals()

    def _setup_signals(self):
        def cleanup_and_exit(signum, frame):
            print("\nDEBUG: Skript wird beendet. Räume auf...")
            self.running = False
            self.sleep_handler.running = False

            self.keyboard.close()

            for dev in self.devices:
                try:
                    dev.ungrab()
                except Exception:
                    pass

            self.mqtt.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, cleanup_and_exit)
        signal.signal(signal.SIGTERM, cleanup_and_exit)

    def run(self):
        connected = False
        while not connected and self.running:
            try:
                self.mqtt.connect()
                connected = True
            except OSError as e:
                print(f"WARNUNG: Netzwerk noch nicht bereit ({e}). Versuche es in 5 Sekunden erneut...")
                time.sleep(5)

        print("DEBUG: Hauptschleife gestartet. Lausche auf Events...")

        while self.running:
            r, _, _ = select.select(self.fds.keys(), [], [], 1.0)

            if r:
                self.sleep_handler.register_activity()
                for fd in r:
                    for event in self.fds[fd].read():
                        self.gesture_recognizer.process_event(event)
            else:
                elapsed = time.time() - self.sleep_handler.last_input_time
                if self.config.is_enabled and elapsed >= self.config.timeout:
                    self.keyboard.close()
                self.sleep_handler.check_timeout()


if __name__ == "__main__":
    try:
        app = KioskApp()
        app.run()
    except Exception as e:
        print(f"CRITICAL ERROR im Main-Loop: {e}")